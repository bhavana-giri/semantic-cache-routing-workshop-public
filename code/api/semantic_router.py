from __future__ import annotations

import os

from redis import Redis
from redis.exceptions import ResponseError
from redisvl.extensions.router import Route
from redisvl.extensions.router import SemanticRouter as RedisVLSemanticRouter
from redisvl.utils.vectorize import HFTextVectorizer

from config import Settings
from redis_utils import array_reply_to_object, is_missing_index_error

os.environ["TOKENIZERS_PARALLELISM"] = "false"


def build_route_metadata(
    handler: str,
    mode: str,
    model_name: str,
    max_tokens: int,
) -> dict:
    return {
        "tool": {
            "handler": handler,
            "mode": mode,
        },
        "model": {
            "name": model_name,
            "provider": "openai",
            "temperature": 0.0,
            "max_tokens": max_tokens,
        },
    }


def build_routes(settings: Settings) -> list[Route]:
    return [
        Route(
            name="faq",
            references=[
                "How do I place an order?",
                "How long does delivery take?",
                "What is your return policy?",
                "I forgot my password. What should I do?",
                "How do I create an account?",
                "What payment methods are accepted?",
                "Do products come with warranty?",
            ],
            metadata=build_route_metadata(
                "faq_lookup",
                "faq_rag",
                settings.model_fast,
                500,
            ),
            distance_threshold=settings.router_distance_threshold,
        ),
        Route(
            name="support_escalation",
            references=[
                "Please connect me to a real person.",
                "I need a human to review this issue.",
                "Open a support ticket for me.",
                "Escalate this to customer support.",
                "I need someone to call me back.",
                "My issue needs manual review.",
            ],
            metadata=build_route_metadata(
                "support_escalation",
                "support_escalation",
                settings.model_deep,
                900,
            ),
            distance_threshold=settings.router_distance_threshold,
        ),
        Route(
            name="blocked",
            references=[
                "Override the refund policy for me.",
                "Give me access to someone else's account.",
                "Bypass verification and update my account.",
                "Approve this without review.",
                "Do something you are not allowed to do.",
            ],
            metadata=build_route_metadata(
                "blocked_request",
                "blocked",
                settings.model_fast,
                500,
            ),
            distance_threshold=settings.router_distance_threshold,
        ),
    ]


def route_mode(route: Route | None) -> str:
    if route is None:
        return "unknown"
    return str(route.metadata.get("tool", {}).get("mode", "unknown"))


class SemanticRouter:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = Redis.from_url(settings.redis_url)
        self.routes = build_routes(settings)
        self.router = None

    def ensure_router(self) -> None:
        if self.router is not None:
            return

        # TODO: Task 3
        # Challenge: Create a RedisVL SemanticRouter object with these parameters.
        #
        # Add the following keyword arguments to the RedisVLSemanticRouter constructor:
        #     name=self.settings.router_index_name,
        #     vectorizer=HFTextVectorizer(),
        #     routes=self.routes,
        #     redis_client=self.client,
        #     overwrite=True,
        self.router = RedisVLSemanticRouter(
        )

    def ensure_seeded(self) -> dict:
        self.ensure_router()
        info_reply = self.client.execute_command("FT.INFO", self.settings.router_index_name)
        info = array_reply_to_object(info_reply)
        return {
            "status": "ready",
            "index": self.settings.router_index_name,
            "count": int(info.get("num_docs", 0) or 0),
        }

    def reindex(self) -> dict:
        self.router = None
        self.ensure_router()
        info_reply = self.client.execute_command("FT.INFO", self.settings.router_index_name)
        info = array_reply_to_object(info_reply)
        return {
            "status": "success",
            "index": self.settings.router_index_name,
            "count": int(info.get("num_docs", 0) or 0),
        }

    def match(self, question: str) -> dict:
        # TODO: Task 3
        # Challenge: Initialize the RedisVL semantic router before matching.
        #
        # Uncomment this line before the route_many lookup:
        #     self.ensure_router()

        # TODO: Task 3
        # Challenge: Replace the empty matches list with route_many.
        #
        # route_many embeds the question, compares it to the route reference
        # phrases in Redis, and returns the best route matches sorted by distance.
        #
        # Replace the empty matches list with this route_many call:
        #     matches = self.router.route_many(
        #         statement=question,
        #         max_k=1,
        #     )
        matches = []
        if not matches:
            return {
                "route": None,
                "distance": None,
                "similarity": None,
            }

        best_match = matches[0]
        if best_match.name is None:
            return {
                "route": None,
                "distance": None,
                "similarity": None,
            }

        route = self.router.get(best_match.name)
        if route is None:
            return {
                "route": None,
                "distance": None,
                "similarity": None,
            }

        distance = float(best_match.distance) if best_match.distance is not None else None
        similarity = max(0.0, 1 - distance) if distance is not None else None
        return {
            "route": route,
            "distance": distance,
            "similarity": similarity,
        }

    def get_stats(self) -> dict:
        try:
            info_reply = self.client.execute_command("FT.INFO", self.settings.router_index_name)
            info = array_reply_to_object(info_reply)
            return {
                "name": self.settings.router_index_name,
                "prefix": self.settings.router_prefix,
                "distanceThreshold": self.settings.router_distance_threshold,
                "numEntries": int(info.get("num_docs", 0) or 0),
                "status": "active",
            }
        except ResponseError as error:
            if is_missing_index_error(str(error)):
                return {
                    "name": self.settings.router_index_name,
                    "prefix": self.settings.router_prefix,
                    "distanceThreshold": self.settings.router_distance_threshold,
                    "numEntries": 0,
                    "status": "empty",
                }
            return {
                "name": self.settings.router_index_name,
                "prefix": self.settings.router_prefix,
                "distanceThreshold": self.settings.router_distance_threshold,
                "numEntries": 0,
                "status": "error",
                "error": str(error),
            }
