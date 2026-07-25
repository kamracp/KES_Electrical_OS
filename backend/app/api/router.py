"""
Central API router for KES Electrical OS.
"""

from fastapi import APIRouter

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