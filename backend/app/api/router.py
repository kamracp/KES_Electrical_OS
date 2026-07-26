"""
Central API router for KES Electrical OS.
"""

from fastapi import APIRouter

from app.api.v1.unit import router as unit_router

api_router = APIRouter()


@api_router.get("/health", tags=["System"])
async def health():
    return {
        "status": "healthy",
        "service": "KES Electrical OS API",
    }


@api_router.get("/version", tags=["System"])
async def version():
    return {
        "application": "KES Electrical OS API",
        "version": "0.1.0",
    }


api_router.include_router(unit_router)