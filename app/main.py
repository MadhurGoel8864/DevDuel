# app/main.py
from fastapi import FastAPI

from app.api.main import api_router
from app.core.config import settings

app = FastAPI(title=settings.app_name)

app.include_router(api_router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
