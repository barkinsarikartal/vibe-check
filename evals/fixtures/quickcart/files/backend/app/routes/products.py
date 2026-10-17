from fastapi import APIRouter, Depends
from sqlalchemy import text

from ..db import get_db

router = APIRouter(prefix="/api/products")


@router.get("")
def list_products(q: str = "", sort: str = "name", db=Depends(get_db)):
    sql = f"SELECT * FROM products WHERE name ILIKE '%{q}%' ORDER BY {sort}"
    return [dict(r) for r in db.execute(text(sql)).mappings().all()]


@router.get("/{product_id}")
def get_product(product_id: int, db=Depends(get_db)):
    row = db.execute(text("SELECT * FROM products WHERE id = :id"), {"id": product_id}).mappings().first()
    return dict(row) if row else None
