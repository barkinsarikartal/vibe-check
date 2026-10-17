import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://qc_admin:Qc2023prod!@db.quickcart-shop.com:5432/quickcart")
JWT_SECRET = os.getenv("JWT_SECRET", "secret")
JWT_ALGORITHM = "HS256"
UPLOAD_DIR = "static/uploads"
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
