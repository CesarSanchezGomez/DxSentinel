# backend/app/main.py
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


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    favicon_path = "frontend/static/images/favicon.ico"
    if os.path.exists(favicon_path):
        return FileResponse(favicon_path)
    return Response(status_code=204)

# ============================================
# RUTAS PÚBLICAS
# ============================================

@app.get("/health")
async def health_check():
    """Health check endpoint - no requiere autenticación"""
    return {
        "status": "ok",
        "app": "DxSentinel",
        "version": "1.0.0"
    }


# ============================================
# RUTAS PROTEGIDAS
# ============================================

@app.get("/", response_class=HTMLResponse)
async def root(request: Request, user=Depends(get_current_user)):
    """Página principal"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "user": {"email": user.email, "id": user.id}
    })


@app.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request, user=Depends(get_current_user)):
    """Página de carga de archivos"""
    return templates.TemplateResponse("upload.html", {
        "request": request,
        "user": {"email": user.email, "id": user.id}
    })


# backend/app/main.py

# @app.get("/result", response_class=HTMLResponse)
# async def result_page(request: Request, user=Depends(get_current_user)):
#     """Página de resultados"""
#     return templates.TemplateResponse("result.txt", {
#         "request": request,
#         "user": {"email": user.email, "id": user.id}
#     })


# backend/app/main.py
@app.get("/split", response_class=HTMLResponse)  # AGREGAR ESTA RUTA
async def split_page(request: Request):
    return templates.TemplateResponse("split.html", {"request": request})

# ============================================
# MANEJADOR DE ERRORES
# ============================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Maneja todos los HTTPException de forma centralizada.
    Redirige a login si es 401/403, sino retorna JSON.
    """
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