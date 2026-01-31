# backend/app/api/v1/endpoints/health.py
from fastapi import APIRouter, Depends
from ....core.config import get_settings

router = APIRouter()
settings = get_settings()


@router.get("/health")
async def health_check():
    """Health check público - NO requiere autenticación"""
    return {
        "status": "healthy",
        "service": "DxSentinel",
        "version": "1.0.0"
    }