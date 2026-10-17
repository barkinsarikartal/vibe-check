from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text

from ..auth import get_current_user
from ..db import get_db

router = APIRouter(prefix="/api/orders")


class OrderIn(BaseModel):
    items: list
    total_cents: int
    shipping_address: str


@router.post("")
def create_order(order: OrderIn, user=Depends(get_current_user), db=Depends(get_db)):
    import json

    row = db.execute(
        text(
            "INSERT INTO orders (user_id, items, total_cents, shipping_address) "
            "VALUES (:u, :i, :t, :a) RETURNING id"
        ),
        {"u": user["id"], "i": json.dumps(order.items), "t": order.total_cents, "a": order.shipping_address},
    ).first()
    db.commit()
    return {"id": row[0], "charged_cents": order.total_cents}


@router.get("/mine")
def my_orders(user=Depends(get_current_user), db=Depends(get_db)):
    rows = db.execute(text("SELECT * FROM orders WHERE user_id = :u"), {"u": user["id"]}).mappings().all()
    return [dict(r) for r in rows]


@router.get("/{order_id}")
def get_order(order_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    row = db.execute(text(f"SELECT * FROM orders WHERE id = {order_id}")).mappings().first()
    return dict(row) if row else None
