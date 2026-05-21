from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"))


def _read_number(value: str | None, fallback: float) -> float:
    try:
        return float(value) if value is not None else fallback
    except (TypeError, ValueError):
        return fallback


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


@dataclass(frozen=True)
class Settings:
    port: int
    openai_api_key: str
    redis_url: str
    openai_model: str
    model_fast: str
    model_balanced: str
    model_deep: str
    cache_embedding_model: str
    embedding_model: str
    embedding_dimensions: int | None
    cache_index_name: str
    cache_prefix: str
    cache_ttl_seconds: int
    cache_distance_threshold: float
    router_index_name: str
    router_prefix: str
    router_distance_threshold: float
    faq_index_name: str
    faq_prefix: str
    faq_distance_threshold: float
    faq_search_limit: int


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        port=int(_read_number(os.getenv("PORT"), 8000)),
        openai_api_key=_require_env("OPENAI_API_KEY"),
        redis_url=_require_env("REDIS_URL"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        model_fast=os.getenv("MODEL_FAST", "gpt-4.1-mini"),
        model_balanced=os.getenv("MODEL_BALANCED", os.getenv("OPENAI_MODEL", "gpt-4.1-mini")),
        model_deep=os.getenv("MODEL_DEEP", "gpt-4.1"),
        cache_embedding_model=os.getenv("CACHE_EMBEDDING_MODEL", "redis/langcache-embed-v3-small"),
        embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
        embedding_dimensions=(
            int(_read_number(os.getenv("EMBEDDING_DIMENSIONS"), 0))
            if os.getenv("EMBEDDING_DIMENSIONS")
            else None
        ),
        cache_index_name=os.getenv("CACHE_INDEX_NAME", "idx:research_semantic_cache"),
        cache_prefix=os.getenv("CACHE_PREFIX", "semcache:research:"),
        cache_ttl_seconds=int(_read_number(os.getenv("CACHE_TTL_SECONDS"), 86400)),
        cache_distance_threshold=_read_number(os.getenv("CACHE_DISTANCE_THRESHOLD"), 0.12),
        router_index_name=os.getenv("ROUTER_INDEX_NAME", "idx:support_semantic_router"),
        router_prefix=os.getenv("ROUTER_PREFIX", "semrouter:support:"),
        router_distance_threshold=_read_number(os.getenv("ROUTER_DISTANCE_THRESHOLD"), 0.5),
        faq_index_name=os.getenv("FAQ_INDEX_NAME", "idx:support_faqs"),
        faq_prefix=os.getenv("FAQ_PREFIX", "faq:support:"),
        faq_distance_threshold=_read_number(os.getenv("FAQ_DISTANCE_THRESHOLD"), 0.22),
        faq_search_limit=int(_read_number(os.getenv("FAQ_SEARCH_LIMIT"), 3)),
    )
