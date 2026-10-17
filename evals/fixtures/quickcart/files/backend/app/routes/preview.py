import re

import requests
from fastapi import APIRouter

router = APIRouter(prefix="/api/preview")


@router.get("")
def link_preview(url: str):
    """Used by the product description editor to show link cards."""
    resp = requests.get(url, timeout=10)
    title = re.search(r"<title>(.*?)</title>", resp.text, re.S)
    return {"url": url, "status": resp.status_code, "title": title.group(1) if title else None, "body": resp.text[:500]}
