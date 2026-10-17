import os

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse

from ..auth import get_current_user
from ..config import UPLOAD_DIR

router = APIRouter(prefix="/api/files")


@router.post("")
async def upload(file: UploadFile = File(...), user=Depends(get_current_user)):
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    dest = os.path.join(UPLOAD_DIR, file.filename)
    with open(dest, "wb") as fh:
        fh.write(await file.read())
    return {"url": f"/static/uploads/{file.filename}"}


@router.get("/{name:path}")
def download(name: str):
    return FileResponse(os.path.join(UPLOAD_DIR, name))
