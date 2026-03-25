from fastapi import APIRouter
from datetime import datetime, timezone

router = APIRouter()

@router.get("/health")
async def health():
    return {"status": "ok", "app": "KT Monetization OS", "ts": datetime.now(timezone.utc).isoformat()}

@router.get("/")
async def root():
    return {"message": "KT Monetization OS — online"}
