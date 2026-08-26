from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ConversationMemory:
    """Stores safe context for the current conversation."""

    last_order_id: Optional[str] = None
    messages: list[dict] = field(default_factory=list)

    def add_message(self, role: str, content: str) -> None:
        """Store a conversation message."""
        self.messages.append(
            {
                "role": role,
                "content": content,
            }
        )

    def set_order_id(self, order_id: str) -> None:
        """Remember the most recently referenced order ID."""
        if order_id:
            self.last_order_id = order_id.strip().upper()

    def get_order_id(self) -> Optional[str]:
        """Return the remembered order ID."""
        return self.last_order_id

    def clear(self) -> None:
        """Clear the current conversation memory."""
        self.last_order_id = None
        self.messages.clear()