import json
from pathlib import Path
from typing import Optional


ORDERS_FILE = Path(__file__).resolve().parent.parent / "data" / "orders.json"


def load_orders() -> list[dict]:
    """Load orders from the provided dataset."""
    with ORDERS_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    return data["orders"]


def get_order(order_id: str) -> Optional[dict]:
    """
    Return a sanitized customer-safe view of an order.

    Never exposes:
    - customer email
    - shipping address
    - internal risk score
    - warehouse notes
    - support tags
    """
    if not order_id:
        return None

    order_id = order_id.strip().upper()

    for order in load_orders():
        if order.get("order_id") == order_id:
            return {
                "order_id": order["order_id"],
                "status": order["status"],
                "status_updated_at": order["status_updated_at"],
                "shipped_at": order["shipped_at"],
                "delivered_at": order["delivered_at"],
                "carrier": order["carrier"],
                "tracking_number": order["tracking_number"],
                "estimated_delivery": order["estimated_delivery"],
                "customer_safe_message": order["customer_safe_message"],
                "items": [
                    {
                        "sku": item["sku"],
                        "name": item["name"],
                        "quantity": item["quantity"],
                    }
                    for item in order.get("items", [])
                ],
            }

    return None