from app.memory import ConversationMemory


def test_memory_stores_order_id():
    memory = ConversationMemory()

    memory.set_order_id("ord-1007")

    assert memory.get_order_id() == "ORD-1007"


def test_memory_stores_messages():
    memory = ConversationMemory()

    memory.add_message(
        "user",
        "Where is my order?",
    )

    assert len(memory.messages) == 1
    assert memory.messages[0]["role"] == "user"
    assert memory.messages[0]["content"] == "Where is my order?"


def test_memory_clear():
    memory = ConversationMemory()

    memory.set_order_id("ORD-1007")
    memory.add_message(
        "user",
        "Hello",
    )

    memory.clear()

    assert memory.get_order_id() is None
    assert memory.messages == []