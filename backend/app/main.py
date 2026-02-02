import os

from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse, Response
from pathlib import Path

from .api.v1.router import api_router
from .auth.router import router as auth_router
from .auth.dependencies import get_current_user
from .core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="DxSentinel",
    version="1.0.0",
    description="SAP SuccessFactors XML Processor"
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "frontend" / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "frontend" / "templates"))

app.include_router(auth_router)
app.include_router(api_router, prefix="/api/v1")


def get_user_context(user):
    """Extrae información del usuario incluyendo avatar de Google"""
    user_data = {
        "email": user.email,
        "id": user.id,
        "avatar_url": None
    }

    if user.user_metadata:
        user_data["avatar_url"] = user.user_metadata.get("avatar_url") or user.user_metadata.get("picture")

    return user_data


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    favicon_path = "frontend/static/images/favicon.ico"
    if os.path.exists(favicon_path):
        return FileResponse(favicon_path)
    return Response(status_code=204)


@app.get("/health")
async def health_check():
    """Health check endpoint - no requiere autenticación"""
    return {
        "status": "ok",
        "app": "DxSentinel",
        "version": "1.0.0"
    }


@app.get("/", response_class=HTMLResponse)
async def root(request: Request, user=Depends(get_current_user)):
    """Página principal"""
    return templates.TemplateResponse("home.html", {
        "request": request,
        "user": get_user_context(user)
    })


@app.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request, user=Depends(get_current_user)):
    """Página de carga de archivos"""
    return templates.TemplateResponse("upload.html", {
        "request": request,
        "user": get_user_context(user)
    })


@app.get("/split", response_class=HTMLResponse)
async def split_page(request: Request, user=Depends(get_current_user)):
    """Página de split layouts"""
    return templates.TemplateResponse("split.html", {
        "request": request,
        "user": get_user_context(user)
    })


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Maneja todos los HTTPException de forma centralizada"""
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail}
        )

    if exc.status_code in [401, 403]:
        return RedirectResponse(url="/auth/login", status_code=302)

    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

@app.get("/structure", response_class=HTMLResponse)
async def structure_page(request: Request, user=Depends(get_current_user)):
    """Página de structure version"""
    return templates.TemplateResponse("structure.html", {
        "request": request,
        "user": get_user_context(user)
    })