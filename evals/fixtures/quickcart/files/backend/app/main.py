import logging
import traceback

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .db import init_db
from .routes import admin, orders, preview, products, uploads, users

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="QuickCart API", debug=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"error": str(exc), "trace": traceback.format_exc()})


@app.on_event("startup")
def startup():
    init_db()


app.include_router(users.router)
app.include_router(products.router)
app.include_router(orders.router)
app.include_router(uploads.router)
app.include_router(preview.router)
app.include_router(admin.router)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/health")
def health():
    return {"ok": True}
