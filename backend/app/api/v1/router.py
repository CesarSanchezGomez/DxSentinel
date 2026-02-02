# backend/app/api/v1/router.py
from fastapi import APIRouter
from .endpoints import upload, process, health, split
from . import structure 

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(upload.router, prefix="/upload", tags=["upload"])
api_router.include_router(process.router, prefix="/process", tags=["process"])
api_router.include_router(split.router, prefix="/split", tags=["split"])
api_router.include_router(structure.router, prefix="/structure", tags=["structure"])