from __future__ import annotations

import time

from fastapi import FastAPI
from pydantic import BaseModel
from starlette.responses import JSONResponse

from config import get_settings
from faq_index import FAQIndex
from semantic_router import SemanticRouter, route_mode
from support_service import SupportService
from semantic_cache import LLMSemanticCache

settings = get_settings()
app = FastAPI()
cache = LLMSemanticCache(settings)
faq_index = FAQIndex(settings)
router = SemanticRouter(settings)
support_service = SupportService(settings)

ROUTER_STARTER_FALLBACK_REASON = (
    "Semantic router is not implemented yet; defaulted to FAQ RAG so Tasks 1 and 2 "
    "can focus on semantic caching."
)
CACHE_SKIP_UNKNOWN_ROUTE_REASON = "No semantic route matched, so the fallback response was not cached."


def known_embedding_dimensions(model_name: str) -> int | None:
    known_dimensions = {
        "redis/langcache-embed-v3-small": 384,
        "redis/langcache-embed-v3-experimental": 768,
        "langcache-embed-v3-small": 384,
        "langcache-embed-v3-experimental": 768,
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536,
    }
    return known_dimensions.get(model_name)


def resolve_faq_embedding_dimensions() -> int:
    if settings.embedding_dimensions:
        return settings.embedding_dimensions

    known = known_embedding_dimensions(settings.embedding_model)
    if known is not None:
        return known

    return len(support_service.embed_faq("faq startup probe"))


def safe_faq_stats() -> dict:
    try:
        return faq_index.get_stats()
    except Exception as error:
        return {
            "name": settings.faq_index_name,
            "prefix": settings.faq_prefix,
            "distanceThreshold": settings.faq_distance_threshold,
            "numEntries": 0,
            "status": "error",
            "error": str(error),
        }


def safe_router_stats() -> dict:
    try:
        return router.get_stats()
    except Exception as error:
        return {
            "name": settings.router_index_name,
            "prefix": settings.router_prefix,
            "distanceThreshold": settings.router_distance_threshold,
            "numEntries": 0,
            "status": "error",
            "error": str(error),
        }


def live_policy() -> dict:
    return {
        "cacheDistanceThreshold": settings.cache_distance_threshold,
        "cacheTtlSeconds": settings.cache_ttl_seconds,
        "routerDistanceThreshold": settings.router_distance_threshold,
        "cacheEmbeddingModel": settings.cache_embedding_model,
        "embeddingModel": settings.embedding_model,
        "cacheIndexName": settings.cache_index_name,
        "cachePrefix": settings.cache_prefix,
    }


def execute_route(question: str, embedding: list[float], route_match) -> tuple[object, list]:
    route = route_match["route"]
    mode = route_mode(route)
    if mode == "faq_rag":
        faq_matches = faq_index.search(question, embedding)
        return support_service.answer(question, faq_matches, route=route), faq_matches
    if mode == "support_escalation":
        return support_service.support_escalation_response(question, route=route), []
    if mode == "blocked":
        return support_service.blocked_response(question, route=route), []
    if mode == "unknown":
        if route is None and router.router is None:
            faq_matches = faq_index.search(question, embedding)
            support_result = support_service.answer(question, faq_matches, route=route)
            support_result.tool_fallback_reason = ROUTER_STARTER_FALLBACK_REASON
            route_match["toolName"] = "fallback_faq"
            route_match["mode"] = "faq_rag"
            route_match["modelName"] = support_result.model
            return support_result, faq_matches
        return support_service.unknown_route_response(question, route=route), []

    faq_matches = faq_index.search(question, embedding)
    return support_service.answer(question, faq_matches, route=route), faq_matches


def route_name(route) -> str:
    if route is None:
        return "unknown"
    return route.name


def response_tool_name(route_match: dict) -> str:
    return route_match.get("toolName") or route_name(route_match["route"])


def response_route_mode(route_match: dict) -> str:
    return route_match.get("mode") or route_mode(route_match["route"])


def response_model_name(route_match: dict) -> str | None:
    if route_match.get("modelName"):
        return route_match["modelName"]

    route = route_match["route"]
    if route is None:
        return None
    return route.metadata.get("model", {}).get("name")


def apply_starter_router_fallback(route_match: dict) -> None:
    if route_match["route"] is None and router.router is None:
        route_match["toolName"] = "fallback_faq"
        route_match["mode"] = "faq_rag"


def should_cache_response(route_match: dict) -> bool:
    return response_route_mode(route_match) != "unknown"


class SupportRequest(BaseModel):
    question: str


@app.on_event("startup")
def startup() -> None:
    faq_index.ensure_seeded(resolve_faq_embedding_dimensions())


@app.get("/api/health")
def health() -> JSONResponse:
    try:
        stats = cache.get_stats()
        return JSONResponse(
            {
                "ok": True,
                "models": {
                    "research": settings.openai_model,
                    "embeddings": settings.embedding_model,
                },
                "policy": live_policy(),
                "cache": stats,
                "router": safe_router_stats(),
                "faqs": safe_faq_stats(),
            }
        )
    except Exception as error:
        return JSONResponse(
            status_code=503,
            content={
                "ok": False,
                "error": str(error),
                "models": {
                    "research": settings.openai_model,
                    "embeddings": settings.embedding_model,
                },
                "policy": live_policy(),
                "cache": {
                    "name": settings.cache_index_name,
                    "prefix": settings.cache_prefix,
                    "ttlSeconds": settings.cache_ttl_seconds,
                    "distanceThreshold": settings.cache_distance_threshold,
                    "numEntries": 0,
                    "status": "unreachable",
                },
                "router": safe_router_stats(),
                "faqs": safe_faq_stats(),
            },
        )


@app.get("/api/cache/stats")
def cache_stats() -> dict:
    return cache.get_stats()


@app.post("/api/cache/clear")
def clear_cache() -> JSONResponse:
    try:
        cache.clear()
        return JSONResponse({"ok": True, "cache": cache.get_stats()})
    except Exception as error:
        return JSONResponse(status_code=503, content={"ok": False, "error": str(error)})


@app.post("/api/research")
def research(payload: SupportRequest) -> JSONResponse:
    question = payload.question.strip()
    if not question:
        return JSONResponse(status_code=400, content={"error": "Question is required."})

    try:
        started_at = time.perf_counter()
        cache_result = cache.check(question)
        route_match = router.match(question)
        apply_starter_router_fallback(route_match)

        if cache_result.hit:
            tool_name = response_tool_name(route_match)
            mode = response_route_mode(route_match)
            return JSONResponse(
                {
                    "ok": True,
                    "question": question,
                    "answer": cache_result.response,
                    "sources": cache_result.sources or [],
                    "cache": {
                        "hit": True,
                        "distance": cache_result.distance,
                        "similarity": cache_result.similarity,
                        "matchedQuestion": cache_result.cached_prompt,
                        "threshold": settings.cache_distance_threshold,
                    },
                    "routing": {
                        "toolName": tool_name,
                        "mode": mode,
                        "modelName": response_model_name(route_match),
                        "distance": route_match["distance"],
                        "similarity": route_match["similarity"],
                    },
                    "metadata": {
                        "servedBy": "redis-semantic-cache",
                        "latencyMs": round((time.perf_counter() - started_at) * 1000),
                        "model": cache_result.model,
                        "cachedAt": cache_result.created_at,
                        "originalLatencyMs": cache_result.latency_ms,
                    },
                }
            )

        support_started_at = time.perf_counter()
        faq_embedding = support_service.embed_faq(question)
        support_result, faq_matches = execute_route(question, faq_embedding, route_match)
        tool_name = response_tool_name(route_match)
        mode = response_route_mode(route_match)
        agent_latency_ms = (time.perf_counter() - support_started_at) * 1000
        cached_at = None
        cache_skipped_reason = None
        if should_cache_response(route_match):
            stored = cache.store(
                question=question,
                response=support_result.answer,
                sources=support_result.sources,
                model=support_result.model,
                latency_ms=agent_latency_ms,
            )
            cached_at = stored["createdAt"]
        else:
            cache_skipped_reason = CACHE_SKIP_UNKNOWN_ROUTE_REASON

        return JSONResponse(
            {
                "ok": True,
                "question": question,
                "answer": support_result.answer,
                "sources": support_result.sources,
                "cache": {
                    "hit": False,
                    "distance": cache_result.distance,
                    "similarity": cache_result.similarity,
                    "matchedQuestion": cache_result.cached_prompt,
                    "threshold": settings.cache_distance_threshold,
                },
                "routing": {
                    "toolName": tool_name,
                    "mode": mode,
                    "modelName": response_model_name(route_match),
                    "distance": route_match["distance"],
                    "similarity": route_match["similarity"],
                },
                "metadata": {
                    "servedBy": f"{tool_name}:{mode}",
                    "latencyMs": round((time.perf_counter() - started_at) * 1000),
                    "model": support_result.model,
                    "cachedAt": cached_at,
                    "cacheSkippedReason": cache_skipped_reason,
                    "responseId": support_result.response_id,
                    "toolFallbackReason": support_result.tool_fallback_reason,
                },
            }
        )
    except Exception as error:
        return JSONResponse(status_code=500, content={"error": str(error)})


@app.post("/api/faqs/reindex")
def reindex_faqs() -> JSONResponse:
    try:
        result = faq_index.reindex(resolve_faq_embedding_dimensions())
        return JSONResponse({"ok": True, "faqs": result})
    except Exception as error:
        return JSONResponse(status_code=500, content={"ok": False, "error": str(error)})


@app.post("/api/router/reindex")
def reindex_router() -> JSONResponse:
    try:
        result = router.reindex()
        return JSONResponse({"ok": True, "router": result})
    except Exception as error:
        return JSONResponse(status_code=500, content={"ok": False, "error": str(error)})
