from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openai import OpenAI
from redis import Redis
from redis.exceptions import ResponseError

from config import Settings
from redis_utils import (
    array_reply_to_object,
    float32_buffer,
    is_missing_index_error,
    normalize_question,
    parse_search_results,
)


@dataclass
class FAQMatch:
    id: str
    question: str
    answer: str
    category: str
    similarity: float | None = None
    distance: float | None = None

    def to_source(self) -> dict[str, str]:
        return {
            "id": self.id,
            "title": f"{self.category.replace('_', ' ').title()}: {self.question}",
            "content": self.answer,
        }


class FAQIndex:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = Redis.from_url(settings.redis_url)
        self.openai = OpenAI(api_key=settings.openai_api_key)
        self.faqs_path = Path(__file__).with_name("support_faqs.json")
        self.metadata_key = f"faqmeta:{settings.faq_index_name}"
        self.index_ready = False
        self.vector_dimensions: int | None = None

    def ensure_index(self, vector_dimensions: int) -> None:
        if self.index_ready and self.vector_dimensions == vector_dimensions:
            return

        try:
            self.client.execute_command("FT.INFO", self.settings.faq_index_name)
            self.index_ready = True
            self.vector_dimensions = vector_dimensions
            return
        except ResponseError as error:
            if not is_missing_index_error(str(error)):
                raise

        self.client.execute_command(
            "FT.CREATE",
            self.settings.faq_index_name,
            "ON",
            "HASH",
            "PREFIX",
            "1",
            self.settings.faq_prefix,
            "SCHEMA",
            "id",
            "TAG",
            "question",
            "TEXT",
            "answer",
            "TEXT",
            "category",
            "TAG",
            "embedding",
            "VECTOR",
            "HNSW",
            "6",
            "TYPE",
            "FLOAT32",
            "DIM",
            str(vector_dimensions),
            "DISTANCE_METRIC",
            "COSINE",
        )

        self.index_ready = True
        self.vector_dimensions = vector_dimensions

    def ensure_seeded(self, vector_dimensions: int) -> dict[str, Any]:
        self.ensure_index(vector_dimensions)
        payload = self._load_faq_payload()
        expected_count = len(payload["faqs"])
        expected_signature = payload["signature"]

        try:
            info_reply = self.client.execute_command("FT.INFO", self.settings.faq_index_name)
            info = array_reply_to_object(info_reply)
            num_docs = int(info.get("num_docs", 0) or 0)
            indexed_signature = self._read_index_signature()
            if num_docs == expected_count and indexed_signature == expected_signature:
                return {
                    "status": "ready",
                    "index": self.settings.faq_index_name,
                    "count": num_docs,
                    "signature": indexed_signature,
                }
        except ResponseError:
            pass

        return self.reindex(vector_dimensions)

    def reindex(self, vector_dimensions: int) -> dict[str, Any]:
        self.ensure_index(vector_dimensions)
        payload = self._load_faq_payload()
        faqs = payload["faqs"]
        embeddings = self._embed_many([faq["question"] for faq in faqs])

        existing_keys = list(self.client.scan_iter(match=f"{self.settings.faq_prefix}*"))
        if existing_keys:
            self.client.delete(*existing_keys)

        pipeline = self.client.pipeline()
        for faq, embedding in zip(faqs, embeddings):
            pipeline.hset(
                f"{self.settings.faq_prefix}{faq['id']}",
                mapping={
                    "id": faq["id"],
                    "question": faq["question"],
                    "answer": faq["answer"],
                    "category": faq["category"],
                    "embedding": float32_buffer(embedding),
                },
            )

        pipeline.hset(
            self.metadata_key,
            mapping={
                "dataset": payload["dataset"],
                "version": payload["version"],
                "signature": payload["signature"],
                "count": str(len(faqs)),
            },
        )
        pipeline.execute()

        return {
            "status": "success",
            "index": self.settings.faq_index_name,
            "count": len(faqs),
            "signature": payload["signature"],
        }

    def search(
        self,
        question: str,
        embedding: list[float],
        limit: int | None = None,
        categories: list[str] | tuple[str, ...] | None = None,
    ) -> list[FAQMatch]:
        self.ensure_index(len(embedding))

        num_results = limit or self.settings.faq_search_limit
        base_query = "*"
        if categories:
            escaped = "|".join(self._escape_tag_value(category) for category in categories)
            base_query = f"@category:{{{escaped}}}"
        reply = self.client.execute_command(
            "FT.SEARCH",
            self.settings.faq_index_name,
            f"{base_query}=>[KNN {num_results} @embedding $vector AS vector_distance]",
            "PARAMS",
            "2",
            "vector",
            float32_buffer(embedding),
            "RETURN",
            "5",
            "id",
            "question",
            "answer",
            "category",
            "vector_distance",
            "SORTBY",
            "vector_distance",
            "DIALECT",
            "2",
        )

        matches: list[FAQMatch] = []
        for item in parse_search_results(reply):
            fields = item["fields"]
            distance_raw = fields.get("vector_distance")

            try:
                distance = float(distance_raw) if distance_raw is not None else None
            except (TypeError, ValueError):
                distance = None

            matches.append(
                FAQMatch(
                    id=fields.get("id") or item["key"].split(":")[-1],
                    question=fields.get("question", ""),
                    answer=fields.get("answer", ""),
                    category=fields.get("category", "general"),
                    distance=distance,
                    similarity=max(0.0, 1 - distance),
                )
            )

        if not matches:
            return []

        normalized_query = normalize_question(question).casefold()
        exact_matches = [
            match
            for match in matches
            if normalize_question(match.question).casefold() == normalized_query
        ]
        if exact_matches:
            return exact_matches

        return [
            match
            for match in matches
            if match.distance is not None and match.distance <= self.settings.faq_distance_threshold
        ]

    def _escape_tag_value(self, value: str) -> str:
        escaped = []
        for char in value:
            if char.isalnum() or char in ("_", "-"):
                escaped.append(char)
            else:
                escaped.append(f"\\{char}")
        return "".join(escaped)

    def get_stats(self) -> dict[str, Any]:
        try:
            info_reply = self.client.execute_command("FT.INFO", self.settings.faq_index_name)
            info = array_reply_to_object(info_reply)
            return {
                "name": self.settings.faq_index_name,
                "prefix": self.settings.faq_prefix,
                "distanceThreshold": self.settings.faq_distance_threshold,
                "numEntries": int(info.get("num_docs", 0) or 0),
                "status": "active",
            }
        except Exception as error:
            if isinstance(error, ResponseError) and is_missing_index_error(str(error)):
                return {
                    "name": self.settings.faq_index_name,
                    "prefix": self.settings.faq_prefix,
                    "distanceThreshold": self.settings.faq_distance_threshold,
                    "numEntries": 0,
                    "status": "empty",
                }
            return {
                "name": self.settings.faq_index_name,
                "prefix": self.settings.faq_prefix,
                "distanceThreshold": self.settings.faq_distance_threshold,
                "numEntries": 0,
                "status": "error",
                "error": str(error),
            }

    def _embed_many(self, texts: list[str]) -> list[list[float]]:
        response = self.openai.embeddings.create(
            model=self.settings.embedding_model,
            input=texts,
        )
        return [item.embedding for item in response.data]

    def _load_faq_payload(self) -> dict[str, Any]:
        with self.faqs_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)

        if isinstance(payload, dict):
            faqs = payload.get("faqs", [])
            if isinstance(faqs, list):
                signature = hashlib.sha256(
                    json.dumps(faqs, sort_keys=True, ensure_ascii=True).encode("utf-8")
                ).hexdigest()
                return {
                    "dataset": str(payload.get("dataset", "support_faqs")),
                    "version": str(payload.get("version", "unknown")),
                    "faqs": faqs,
                    "signature": signature,
                }

        if isinstance(payload, list):
            signature = hashlib.sha256(
                json.dumps(payload, sort_keys=True, ensure_ascii=True).encode("utf-8")
            ).hexdigest()
            return {
                "dataset": "support_faqs",
                "version": "unknown",
                "faqs": payload,
                "signature": signature,
            }

        raise ValueError(f"Unsupported FAQ payload format in {self.faqs_path}")

    def _read_index_signature(self) -> str | None:
        value = self.client.hget(self.metadata_key, "signature")
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return value
