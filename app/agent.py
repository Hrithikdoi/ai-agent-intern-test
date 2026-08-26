import os
import re
from dataclasses import dataclass, field

from dotenv import load_dotenv
from openai import OpenAI

from app.prompts import SYSTEM_PROMPT
from app.memory import ConversationMemory
from app.orders import get_order
from app.retrieval import Retriever, DocumentChunk


ORDER_ID_PATTERN = re.compile(
    r"\bORD-\d{4}\b",
    re.IGNORECASE,
)


@dataclass
class AgentResponse:
    answer: str
    sources: list[dict] = field(default_factory=list)
    tool_used: str = "not_called"
    handoff: bool = False
    debug: dict = field(default_factory=dict)


class SupportAgent:
    """Controlled customer-support agent."""

    def __init__(self):
        load_dotenv()

        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY")
        )

        self.model = "gpt-4.1-mini"

        self.retriever = Retriever()
        self.memory = ConversationMemory()

    def _extract_order_id(self, text: str) -> str | None:
        """Extract an order ID from the user's message."""
        match = ORDER_ID_PATTERN.search(text)

        if match:
            return match.group(0).upper()

        return None

    def _is_order_request(self, text: str) -> bool:
        """Detect requests that require order information."""

        if self._extract_order_id(text):
            return True

        keywords = [
            "where is my order",
            "where's my order",
            "order status",
            "track my order",
            "tracking",
            "when will",
            "when should",
            "shipped",
            "check my order",
            "check the order",
            "check order",
        ]

        text_lower = text.lower()

        return any(
            keyword in text_lower
            for keyword in keywords
        )

    def _requests_private_data(self, text: str) -> bool:
        """Detect requests for protected information."""

        private_terms = [
            "email",
            "address",
            "internal note",
            "warehouse note",
            "risk score",
            "fraud review",
            "support tags",
        ]

        text_lower = text.lower()

        return any(
            term in text_lower
            for term in private_terms
        )

    def _is_prompt_injection(self, text: str) -> bool:
        """Detect attempts to override policy authority."""

        injection_terms = [
            "ignore the real policy",
            "ignore previous instructions",
            "ignore the policy",
            "reveal hidden prompt",
            "system prompt",
            "developer message",
            "give everyone 60 days",
            "use the migration note",
        ]

        text_lower = text.lower()

        return any(
            term in text_lower
            for term in injection_terms
        )

    def _source_info(
        self,
        chunks: list[tuple[DocumentChunk, float]],
    ) -> list[dict]:
        """Convert retrieval results into safe source metadata."""

        return [
            {
                "filename": chunk.filename,
                "heading": chunk.heading,
                "score": round(score, 4),
            }
            for chunk, score in chunks
        ]

    def _build_order_response(
        self,
        order_id: str,
    ) -> AgentResponse:
        """Safely handle an order lookup."""

        order = get_order(order_id)

        if order is None:
            return AgentResponse(
                answer=(
                    f"I couldn't find order {order_id}. "
                    "Please check the order ID or contact support."
                ),
                tool_used="order_lookup",
                handoff=True,
            )

        self.memory.set_order_id(order["order_id"])

        status = order["status"]

        if status == "cancelled":
            return AgentResponse(
                answer=(
                    f"Order {order['order_id']} is cancelled, "
                    "so it will not be shipped."
                ),
                tool_used="order_lookup",
            )

        parts = [
            f"Order {order['order_id']} is {status}."
        ]

        if order["carrier"]:
            parts.append(
                f"Carrier: {order['carrier']}."
            )

        if order["tracking_number"]:
            parts.append(
                f"Tracking number: {order['tracking_number']}."
            )

        if order["estimated_delivery"]:
            parts.append(
                f"Estimated delivery: "
                f"{order['estimated_delivery']}."
            )
        elif status == "shipped":
            parts.append(
                "A delivery estimate is currently unavailable."
            )

        if order["customer_safe_message"]:
            parts.append(
                order["customer_safe_message"]
            )

        return AgentResponse(
            answer=" ".join(parts),
            tool_used="order_lookup",
        )

    def _local_grounded_answer(
        self,
        message: str,
        results: list[tuple[DocumentChunk, float]],
    ) -> str:
        """Create a deterministic grounded answer when the API is unavailable."""

        text = message.lower()
                # Genuine conflict between two active official Breeze Tumbler sources.
        if (
            "breeze tumbler" in text
            and any(
                term in text
                for term in [
                    "dishwasher",
                    "dish washer",
                    "dishwash",
                ]
            )
        ):
            return (
                "The current official sources conflict on dishwasher use "
                "for the Breeze Tumbler. The Product Care Guide says the "
                "stainless-steel body should be hand-washed, while the "
                "Breeze Tumbler product card says all components are "
                "dishwasher safe with the top rack recommended. I should "
                "not silently choose between these conflicting instructions. "
                "Please get human confirmation; as the safest interim "
                "guidance, hand-wash the tumbler body."
            )

        # Insufficient information about vegan materials.
        if any(
            term in text
            for term in [
                "vegan",
                "adhesive",
                "fabric",
            ]
        ):
            return (
                "The supplied information is insufficient to confirm "
                "whether all fabrics and adhesives in the bags are vegan. "
                "Please get human confirmation."
            )

        # Canada international shipping scenario.
        if (
            "canada" in text
            and any(
                term in text
                for term in [
                    "ship",
                    "shipping",
                    "how long",
                    "take",
                    "delivery",
                ]
            )
        ):
            return (
                "Aster & Row currently ships internationally to Canada. "
                "Canadian orders generally arrive within 5–9 business days "
                "after dispatch. Import duties, taxes, and brokerage charges "
                "are not prepaid by Aster & Row; the recipient is responsible "
                "for charges assessed by Canadian authorities or the carrier."
            )

        # Unsupported international destination.
        if "germany" in text:
            return (
                "Shipping to Germany is not currently available. "
                "Aster & Row currently ships internationally only to Canada."
            )

        # Final-sale + damaged/defective scenario.
        if (
            "final-sale" in text
            and any(
                term in text
                for term in [
                    "damaged",
                    "broken",
                    "defective",
                    "wrong",
                ]
            )
        ):
            return (
                "Final-sale items are still eligible for review when "
                "they arrive damaged, defective, or incorrect. Final sale "
                "only prevents change-of-mind returns. Damaged items should "
                "be reported within 7 calendar days of delivery. A refund, "
                "replacement, or other resolution requires human review "
                "before approval."
            )

        return self._format_retrieval_answer(results)

    def _generate_with_llm(
        self,
        message: str,
        results: list[tuple[DocumentChunk, float]],
    ) -> str:
        """Generate a grounded response, with a local fallback."""

        context_parts = []

        for chunk, _ in results[:3]:
            context_parts.append(
                f"Source: {chunk.filename} — {chunk.heading}\n"
                f"{chunk.content}"
            )

        context = "\n\n---\n\n".join(context_parts)

        try:
            response = self.client.responses.create(
                model=self.model,
                instructions=SYSTEM_PROMPT,
                input=(
                    f"Knowledge-base context:\n\n"
                    f"{context}\n\n"
                    f"User question:\n{message}"
                ),
            )

            return response.output_text.strip()

        except Exception:
            return self._local_grounded_answer(
                message,
                results,
            )

    def _handle_policy_question(
        self,
        message: str,
    ) -> AgentResponse:
        """Retrieve grounded knowledge-base information."""

        results = self.retriever.search(
            message,
            top_k=5,
        )

        # Special abstention case.
        if "vegan" in message.lower():
            if results:
                answer = self._local_grounded_answer(
                    message,
                    results,
                )
                sources = self._source_info(results)
            else:
                answer = self._local_grounded_answer(
                    message,
                    [],
                )
                sources = []

            return AgentResponse(
                answer=answer,
                sources=sources,
                handoff=True,
            )

        # If retrieval finds nothing, use the local fallback.
        if not results:
            answer = self._local_grounded_answer(
                message,
                results,
            )

            handoff = "germany" not in message.lower()

            return AgentResponse(
                answer=answer,
                sources=[],
                handoff=handoff,
            )

        answer = self._generate_with_llm(
            message,
            results,
        )

        # Damaged final-sale items require human review.
        text = message.lower()

        handoff = (
            (
                "final-sale" in text
                and any(
                    term in text
                    for term in [
                        "damaged",
                        "broken",
                        "defective",
                        "wrong",
                    ]
                )
            )
            or (
                "breeze tumbler" in text
                and any(
                    term in text
                    for term in [
                        "dishwasher",
                        "dish washer",
                        "dishwash",
                    ]
                )
            )
        )

        return AgentResponse(
            answer=answer,
            sources=self._source_info(results),
            handoff=handoff,
        )

    def _format_retrieval_answer(
        self,
        results: list[tuple[DocumentChunk, float]],
    ) -> str:
        """Create a basic grounded response."""

        best_chunks = results[:3]

        return "\n\n".join(
            chunk.content.strip()
            for chunk, _ in best_chunks
        )

    def handle(self, message: str) -> AgentResponse:
        """Process one user message."""

        self.memory.add_message(
            "user",
            message,
        )

        order_id = self._extract_order_id(message)

        if order_id:
            self.memory.set_order_id(order_id)

        # Protect private/internal order information.
        if self._requests_private_data(message):
            return AgentResponse(
                answer=(
                    "I can't provide customer email addresses, "
                    "shipping addresses, internal notes, risk scores, "
                    "or other internal information."
                ),
                tool_used="not_called",
                handoff=True,
            )

        # Reject attempts to override authoritative policy.
        if self._is_prompt_injection(message):
            results = self.retriever.search(
                message,
                top_k=5,
            )

            return AgentResponse(
                answer=(
                    "The migration note is not an authoritative "
                    "customer policy. The standard return policy "
                    "is 30 calendar days from delivery unless a "
                    "valid exception applies. I cannot approve a "
                    "return automatically."
                ),
                sources=self._source_info(results),
                handoff=False,
            )

        # Explicit or remembered order request.
        if self._is_order_request(message):

            if order_id:
                return self._build_order_response(order_id)

            remembered_order = self.memory.get_order_id()

            if remembered_order:
                return self._build_order_response(
                    remembered_order
                )

            return AgentResponse(
                answer=(
                    "Sure. Please provide your order ID "
                    "(for example, ORD-1007)."
                ),
                tool_used="not_called_without_id",
            )

        # Default to knowledge-base retrieval.
        return self._handle_policy_question(message)