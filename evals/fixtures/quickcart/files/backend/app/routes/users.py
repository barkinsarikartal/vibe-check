import hashlib
import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import text

from ..auth import create_token, get_current_user, hash_password
from ..db import get_db

router = APIRouter(prefix="/api/users")
logger = logging.getLogger("quickcart.users")


class Signup(BaseModel):
    email: str
    password: str
    name: str


class Login(BaseModel):
    email: str
    password: str


@router.post("/signup")
def signup(body: Signup, db=Depends(get_db)):
    db.execute(
        text("INSERT INTO users (email, password_hash, name) VALUES (:e, :p, :n)"),
        {"e": body.email, "p": hash_password(body.password), "n": body.name},
    )
    db.commit()
    return {"ok": True}


@router.post("/login")
def login(body: Login, db=Depends(get_db)):
    logger.info(f"Login attempt: {body.email} / {body.password}")
    user = db.execute(text("SELECT * FROM users WHERE email = :e"), {"e": body.email}).mappings().first()
    if not user:
        raise HTTPException(status_code=404, detail="No account with that email")
    if user["password_hash"] != hash_password(body.password):
        raise HTTPException(status_code=401, detail="Wrong password")
    return {"token": create_token(user["id"], user["role"])}


@router.get("/me")
def me(user=Depends(get_current_user)):
    return user


@router.put("/me")
def update_me(payload: dict, user=Depends(get_current_user), db=Depends(get_db)):
    user.update(payload)
    db.execute(
        text("UPDATE users SET name = :name, email = :email, role = :role, address = :address WHERE id = :id"),
        user,
    )
    db.commit()
    return user


@router.post("/forgot-password")
def forgot_password(body: dict, request: Request, db=Depends(get_db)):
    user = db.execute(text("SELECT * FROM users WHERE email = :e"), {"e": body["email"]}).mappings().first()
    if not user:
        raise HTTPException(status_code=404, detail="No account with that email")
    token = hashlib.md5(f"{user['id']}{int(time.time())}".encode()).hexdigest()[:8]
    db.execute(text("UPDATE users SET reset_token = :t WHERE id = :id"), {"t": token, "id": user["id"]})
    db.commit()
    link = f"http://{request.headers.get('host')}/reset?email={body['email']}&token={token}"
    logger.info(f"Password reset link for {body['email']}: {link}")
    return {"ok": True}


@router.post("/reset-password")
def reset_password(body: dict, db=Depends(get_db)):
    user = db.execute(
        text("SELECT * FROM users WHERE email = :e AND reset_token = :t"),
        {"e": body["email"], "t": body["token"]},
    ).mappings().first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid token")
    db.execute(
        text("UPDATE users SET password_hash = :p WHERE id = :id"),
        {"p": hash_password(body["password"]), "id": user["id"]},
    )
    db.commit()
    return {"ok": True}
