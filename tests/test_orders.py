from app.orders import get_order


def test_valid_order():
    order = get_order("ORD-1001")

    assert order is not None
    assert order["order_id"] == "ORD-1001"
    assert "customer" not in order
    assert "email" not in order
    assert "shipping_address" not in order
    assert "internal" not in order


def test_order_id_is_case_insensitive():
    order = get_order("ord-1001")

    assert order is not None
    assert order["order_id"] == "ORD-1001"


def test_invalid_order_returns_none():
    assert get_order("ORD-9999") is None


def test_empty_order_id_returns_none():
    assert get_order("") is None