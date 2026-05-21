from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from redis import Redis
from redis.exceptions import ResponseError
from redisvl.extensions.cache.llm import SemanticCache
from redisvl.utils.vectorize import HFTextVectorizer

from config import Settings
from redis_utils import is_missing_index_error


@dataclass
class CacheResult:
    hit: bool
    query: str
    normalized_question: str
    cached_prompt: str | None = None
    response: str | None = None
    created_at: str | None = None
    sources: list[dict[str, str]] | None = None
    distance: float | None = None
    similarity: float | None = None
    model: str | None = None
    latency_ms: int = 0


class LLMSemanticCache:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = Redis.from_url(settings.redis_url)
        self.cache: SemanticCache | None = None

    def ensure_cache(self) -> None:
        if self.cache is not None:
            return

        # TODO: Task 1
        # Challenge: Create a RedisVL SemanticCache object with these parameters.
        #
        # Add the following keyword arguments to the SemanticCache constructor:
        #     name=self.settings.cache_index_name,
        #     redis_client=self.client,
        #     vectorizer=HFTextVectorizer(model=self.settings.cache_embedding_model),
        #     distance_threshold=self.settings.cache_distance_threshold,
        #     ttl=self.settings.cache_ttl_seconds,
        #     overwrite=True,
        self.cache = SemanticCache(
        )

    def check(self, question: str) -> CacheResult:
        self.ensure_cache()
        assert self.cache is not None

        # TODO: Task 1
        # Challenge: Check the cache for one semantically similar prompt.
        #
        # Add the following keyword arguments to self.cache.check(...):
        #     prompt=question,
        #     num_results=1,
        matches = self.cache.check()
        if not matches:
            return CacheResult(
                hit=False,
                query=question,
                normalized_question=question,
                sources=[],
            )

        match = matches[0]
        metadata = match.get("metadata") or {}
        sources = metadata.get("sources") or []
        distance = match.get("vector_distance")
        distance = float(distance) if distance is not None else None

        return CacheResult(
            hit=True,
            query=question,
            normalized_question=question,
            cached_prompt=match.get("prompt"),
            response=match.get("response"),
            created_at=metadata.get("created_at"),
            sources=sources,
            distance=distance,
            similarity=max(0.0, 1 - distance) if distance is not None else None,
            model=metadata.get("model"),
            latency_ms=int(metadata.get("latency_ms", 0) or 0),
        )

    def store(
        self,
        *,
        question: str,
        response: str,
        sources: list[dict[str, str]],
        model: str,
        latency_ms: float,
    ) -> dict[str, str]:
        self.ensure_cache()
        assert self.cache is not None

        created_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        metadata = {
            "sources": sources,
            "model": model,
            "latency_ms": round(latency_ms),
            "created_at": created_at,
        }

        # TODO: Task 1
        # Challenge: Store the generated support answer in the semantic cache.
        #
        # Add the following keyword arguments to self.cache.store(...):
        #     prompt=question,
        #     response=response,
        #     metadata=metadata,
        #     ttl=self.settings.cache_ttl_seconds,
        self.cache.store()
        return {"createdAt": created_at}

    def clear(self) -> None:
        self.ensure_cache()
        assert self.cache is not None
        self.cache.clear()

    def get_stats(self) -> dict[str, Any]:
        try:
            self.ensure_cache()
            assert self.cache is not None
            info = self.cache.index.info()
            return {
                "name": self.settings.cache_index_name,
                "prefix": self.settings.cache_prefix,
                "ttlSeconds": self.settings.cache_ttl_seconds,
                "distanceThreshold": self.settings.cache_distance_threshold,
                "numEntries": int(info.get("num_docs", 0) or 0),
                "status": "active",
            }
        except ResponseError as error:
            message = str(error)
            if is_missing_index_error(message):
                return {
                    "name": self.settings.cache_index_name,
                    "prefix": self.settings.cache_prefix,
                    "ttlSeconds": self.settings.cache_ttl_seconds,
                    "distanceThreshold": self.settings.cache_distance_threshold,
                    "numEntries": 0,
                    "status": "empty",
                }
            return {
                "name": self.settings.cache_index_name,
                "prefix": self.settings.cache_prefix,
                "ttlSeconds": self.settings.cache_ttl_seconds,
                "distanceThreshold": self.settings.cache_distance_threshold,
                "numEntries": 0,
                "status": "error",
                "error": message,
            }
        except Exception as error:
            return {
                "name": self.settings.cache_index_name,
                "prefix": self.settings.cache_prefix,
                "ttlSeconds": self.settings.cache_ttl_seconds,
                "distanceThreshold": self.settings.cache_distance_threshold,
                "numEntries": 0,
                "status": "error",
                "error": str(error),
            }
