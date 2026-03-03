# app/api/main.py
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth.routes import AuthRouter, OAuthRouter
from app.api.contests.routes.contests import router as contests_router
from app.api.teams.routes.teams import router as teams_router
from app.api.users.routes.users import router as users_router
from app.core.database import get_db

# routers will be added later


api_router = APIRouter(prefix="/api")


@api_router.get("/db-check")
async def db_check(db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("SELECT 1"))
    return {"db": result.scalar()}


@api_router.get("/health")
async def health_check():
    return {"status": "ok"}


api_router.include_router(users_router)
api_router.include_router(AuthRouter)
api_router.include_router(OAuthRouter)
api_router.include_router(teams_router)
api_router.include_router(contests_router)
