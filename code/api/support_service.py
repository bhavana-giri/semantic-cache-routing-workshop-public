from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from config import Settings
from faq_index import FAQMatch


@dataclass
class SupportResponse:
    answer: str
    sources: list[dict[str, str]]
    model: str
    response_id: str | None
    tool_fallback_reason: str | None = None


class SupportService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.faq_embeddings = OpenAIEmbeddings(
            model=settings.embedding_model,
            api_key=settings.openai_api_key,
        )
        self.llm_cache: dict[tuple[str, float, int | None], ChatOpenAI] = {}
        self.output_parser = StrOutputParser()
        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    (
                        "You are an e-commerce customer support assistant for a semantic caching workshop. "
                        "Answer only from the retrieved FAQ context. "
                        "You have been routed to the tool: {route_name}. "
                        "If a retrieved FAQ directly answers the question, use it plainly and confidently. "
                        "If the retrieved FAQs are incomplete, say exactly what is missing instead of inventing policy details. "
                        "Respond with three markdown sections titled Customer reply, FAQ evidence, and Next steps. "
                        "Keep the tone concise, warm, and action-oriented."
                    ),
                ),
                (
                    "human",
                    (
                        "Customer question:\n{question}\n\n"
                        "Retrieved FAQ context:\n{context}\n\n"
                        "Use the retrieved FAQ context to answer the customer."
                    ),
                ),
            ]
        )
        self.prompt_input = {
            "question": RunnablePassthrough() | RunnableLambda(lambda data: data["question"]),
            "context": RunnableLambda(lambda data: self._format_faq_context(data["faq_matches"])),
            "route_name": RunnableLambda(lambda data: data["route_name"]),
        }

    def embed_faq(self, text: str) -> list[float]:
        return self.faq_embeddings.embed_query(text)

    def answer(
        self,
        question: str,
        faq_matches: list[FAQMatch],
        route: Any | None = None,
    ) -> SupportResponse:
        sources = [match.to_source() for match in faq_matches]
        chain_input = {
            "question": question,
            "faq_matches": faq_matches,
            "route_name": getattr(route, "name", "General support tool"),
        }
        model_config = getattr(route, "metadata", {}).get("model", {})
        selected_model = str(model_config.get("name", self.settings.model_balanced))
        temperature = float(model_config.get("temperature", 0.0))
        max_tokens = model_config.get("max_tokens")

        try:
            prompt_value = (self.prompt_input | self.prompt).invoke(chain_input)
            llm = self._get_llm(
                model_name=selected_model,
                temperature=temperature,
                max_tokens=int(max_tokens) if max_tokens is not None else None,
            )
            ai_message = llm.invoke(prompt_value)
            answer = self.output_parser.invoke(ai_message)

            return SupportResponse(
                answer=(answer or "No answer returned.").strip(),
                sources=sources,
                model=selected_model,
                response_id=getattr(ai_message, "id", None),
            )
        except Exception as error:
            return SupportResponse(
                answer=self._build_fallback_answer(question, faq_matches),
                sources=sources,
                model=selected_model,
                response_id=None,
                tool_fallback_reason=str(error),
            )

    def support_escalation_response(self, question: str, route: Any | None = None) -> SupportResponse:
        model_name = self._selected_model_name(route)
        return SupportResponse(
            answer="\n".join(
                [
                    "## Customer reply",
                    "This request needs a real support person because it appears to require account-specific review or manual intervention.",
                    "",
                    "## FAQ evidence",
                    "- This route is reserved for human escalation rather than FAQ lookup.",
                    "",
                    "## Next steps",
                    f"- Create or escalate a support case for: {question}",
                    "- Capture any order number, account email, and screenshots so a human agent can act quickly.",
                ]
            ),
            sources=[],
            model=model_name,
            response_id=None,
        )

    def blocked_response(self, question: str, route: Any | None = None) -> SupportResponse:
        model_name = self._selected_model_name(route)
        return SupportResponse(
            answer="\n".join(
                [
                    "## Customer reply",
                    "I cannot complete that request automatically because it appears to require a restricted or protected workflow.",
                    "",
                    "## FAQ evidence",
                    "- This route is marked as blocked and is intentionally not fulfilled by the automated assistant.",
                    "",
                    "## Next steps",
                    f"- Review the request manually: {question}",
                    "- If the request is legitimate, direct the customer to the approved support or verification process.",
                ]
            ),
            sources=[],
            model=model_name,
            response_id=None,
        )

    def unknown_route_response(self, question: str, route: Any | None = None) -> SupportResponse:
        model_name = self._selected_model_name(route)
        return SupportResponse(
            answer="\n".join(
                [
                    "## Customer reply",
                    "I could not confidently classify this request into a known support route, so I am not forcing it into the FAQ flow.",
                    "",
                    "## FAQ evidence",
                    "- No route crossed the semantic routing confidence threshold.",
                    "",
                    "## Next steps",
                    f"- Review the intent manually: {question}",
                    "- If this should be supported, add stronger route examples or create a new route for it.",
                ]
            ),
            sources=[],
            model=model_name,
            response_id=None,
        )

    def _get_llm(
        self,
        *,
        model_name: str,
        temperature: float,
        max_tokens: int | None,
    ) -> ChatOpenAI:
        key = (model_name, temperature, max_tokens)
        cached = self.llm_cache.get(key)
        if cached is not None:
            return cached

        llm = ChatOpenAI(
            model=model_name,
            api_key=self.settings.openai_api_key,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        self.llm_cache[key] = llm
        return llm

    def _selected_model_name(self, route: Any | None) -> str:
        model_config = getattr(route, "metadata", {}).get("model", {})
        return str(model_config.get("name", self.settings.model_balanced))

    def _format_faq_context(self, faq_matches: list[FAQMatch]) -> str:
        if not faq_matches:
            return "No FAQ entries passed the similarity threshold."

        blocks: list[str] = []
        for index, match in enumerate(faq_matches, start=1):
            similarity = (
                f"{match.similarity:.2f}" if match.similarity is not None else "unknown"
            )
            blocks.append(
                "\n".join(
                    [
                        f"FAQ {index}",
                        f"Category: {match.category}",
                        f"Question: {match.question}",
                        f"Answer: {match.answer}",
                        f"Similarity: {similarity}",
                    ]
                )
            )
        return "\n\n".join(blocks)

    def _build_fallback_answer(self, question: str, faq_matches: list[FAQMatch]) -> str:
        if not faq_matches:
            return "\n".join(
                [
                    "## Customer reply",
                    "I do not have a matching support FAQ for that question, so I cannot safely give a store-specific answer.",
                    "",
                    "## FAQ evidence",
                    "- No indexed FAQ crossed the similarity threshold.",
                    "",
                    "## Next steps",
                    "- Ask for the order details or policy context needed to answer accurately.",
                    "- Escalate to a human support workflow if the question needs account-specific actions.",
                ]
            )

        evidence_lines = [f"- {match.question}: {match.answer}" for match in faq_matches[:2]]

        return "\n".join(
            [
                "## Customer reply",
                f"Based on the indexed support FAQs, here is the safest answer we can give for: {question}",
                "",
                "## FAQ evidence",
                *evidence_lines,
                "",
                "## Next steps",
                "- Confirm any order-specific details before promising a final outcome.",
                "- Escalate to a human agent if live order, inventory, or refund status is required.",
            ]
        )
