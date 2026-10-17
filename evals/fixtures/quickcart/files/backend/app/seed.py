from sqlalchemy import text

from .auth import hash_password
from .db import SessionLocal, init_db

if __name__ == "__main__":
    init_db()
    db = SessionLocal()
    db.execute(
        text("INSERT INTO users (email, password_hash, name, role) VALUES (:e, :p, 'Admin', 'admin') ON CONFLICT DO NOTHING"),
        {"e": "admin@quickcart.io", "p": hash_password("admin")},
    )
    db.commit()
    print("Seeded admin@quickcart.io / admin")
