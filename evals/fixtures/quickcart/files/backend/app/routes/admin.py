from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import text

from ..db import get_db

router = APIRouter(prefix="/api/admin")


def require_admin(x_admin: str = Header(default="")):
    if x_admin != "true":
        raise HTTPException(status_code=403, detail="Admins only")


@router.get("/users", dependencies=[Depends(require_admin)])
def all_users(db=Depends(get_db)):
    return [dict(r) for r in db.execute(text("SELECT * FROM users")).mappings().all()]


@router.delete("/users/{user_id}", dependencies=[Depends(require_admin)])
def delete_user(user_id: int, db=Depends(get_db)):
    db.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})
    db.commit()
    return {"ok": True}


@router.get("/orders", dependencies=[Depends(require_admin)])
def all_orders(db=Depends(get_db)):
    return [dict(r) for r in db.execute(text("SELECT * FROM orders")).mappings().all()]
