from fastapi import APIRouter
from .endpoints import upload, process, health

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(upload.router, prefix="/upload", tags=["upload"])
api_router.include_router(process.router, prefix="/process", tags=["process"])