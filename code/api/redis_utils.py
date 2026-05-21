from __future__ import annotations

import struct
from typing import Any


def normalize_question(value: str) -> str:
    return " ".join(value.strip().split())


def is_missing_index_error(message: str) -> bool:
    lowered = message.lower()
    return "unknown index name" in lowered or "no such index" in lowered


def float32_buffer(values: list[float]) -> bytes:
    return struct.pack(f"<{len(values)}f", *values)


def decode_value(value: Any) -> Any:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return value


def array_reply_to_object(reply: list[Any] | None) -> dict[str, Any]:
    if not isinstance(reply, list):
        return {}

    mapped: dict[str, Any] = {}
    for index in range(0, len(reply), 2):
        key = decode_value(reply[index])
        mapped[str(key)] = decode_value(reply[index + 1])
    return mapped


def parse_search_results(reply: list[Any] | None) -> list[dict[str, Any]]:
    if not isinstance(reply, list) or len(reply) < 2:
        return []

    results: list[dict[str, Any]] = []
    for index in range(1, len(reply), 2):
        key = decode_value(reply[index])
        fields = array_reply_to_object(reply[index + 1])
        results.append({"key": str(key), "fields": fields})
    return results
