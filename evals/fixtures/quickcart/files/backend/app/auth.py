import hashlib
import logging
import time

import jwt
from fastapi import Depends, Header, HTTPException
from sqlalchemy import text

from .config import JWT_ALGORITHM, JWT_SECRET
from .db import get_db

logger = logging.getLogger("quickcart.auth")


def hash_password(password: str) -> str:
    return hashlib.md5(password.encode()).hexdigest()


def create_token(user_id: int, role: str) -> str:
    return jwt.encode({"sub": user_id, "role": role, "iat": int(time.time())}, JWT_SECRET, algorithm=JWT_ALGORITHM)


def get_current_user(authorization: str = Header(...), db=Depends(get_db)):
    token = authorization.replace("Bearer ", "")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.execute(text("SELECT * FROM users WHERE id = :id"), {"id": payload["sub"]}).mappings().first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return dict(user)
