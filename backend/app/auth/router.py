# backend/app/auth/router.py
from fastapi import APIRouter, Request, HTTPException, status, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from ..auth.supabase_client import get_supabase_client
from ..core.config import get_settings

router = APIRouter(prefix="/auth", tags=["authentication"])

settings = get_settings()
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "frontend" / "templates"))


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """
    Página de login.
    Si el usuario ya tiene sesión válida, redirige al home.
    """
    token = request.cookies.get("access_token")
    if token:
        try:
            supabase = get_supabase_client()
            user_response = supabase.auth.get_user(token)
            if user_response and user_response.user:
                # Usuario ya autenticado, redirigir
                return RedirectResponse(url="/", status_code=302)
        except Exception:
            pass

    return templates.TemplateResponse("login.html", {
        "request": request,
        "supabase_url": settings.SUPABASE_URL,
        "supabase_key": settings.SUPABASE_KEY
    })


@router.get("/callback", response_class=HTMLResponse)
async def auth_callback(request: Request):
    """Callback de Google OAuth"""
    return templates.TemplateResponse("callback.html", {
        "request": request,
        "allowed_domain": settings.ALLOWED_DOMAIN
    })


@router.post("/session")
async def create_session(
    request: Request,
    access_token: str = Form(...),
    refresh_token: str = Form(None),
    email: str = Form(...)
):
    """Endpoint para crear la sesión"""
    try:
        if not access_token or not email:
            raise HTTPException(
                status_code=400,
                detail="Token o email no proporcionado"
            )

        if not email.endswith(f"@{settings.ALLOWED_DOMAIN}"):
            raise HTTPException(
                status_code=403,
                detail=f"Solo se permite acceso a usuarios de @{settings.ALLOWED_DOMAIN}"
            )

        response = RedirectResponse(url="/", status_code=303)

        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=settings.COOKIE_SECURE,
            samesite=settings.COOKIE_SAMESITE,
            max_age=settings.ACCESS_TOKEN_EXPIRE_SECONDS,
            domain=settings.COOKIE_DOMAIN
        )

        if refresh_token:
            response.set_cookie(
                key="refresh_token",
                value=refresh_token,
                httponly=True,
                secure=settings.COOKIE_SECURE,
                samesite=settings.COOKIE_SAMESITE,
                max_age=settings.REFRESH_TOKEN_EXPIRE_SECONDS,
                domain=settings.COOKIE_DOMAIN
            )

        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/logout")
async def logout(request: Request):
    """Cerrar sesión"""
    supabase = get_supabase_client()

    try:
        token = request.cookies.get("access_token")
        if token:
            supabase.auth.sign_out()
    except Exception:
        pass

    response = RedirectResponse(url="/auth/login", status_code=302)
    response.delete_cookie("access_token", domain=settings.COOKIE_DOMAIN)
    response.delete_cookie("refresh_token", domain=settings.COOKIE_DOMAIN)

    return response


@router.get("/user")
async def get_current_user_endpoint(request: Request):
    """Obtener usuario actual desde las cookies"""
    try:
        token = request.cookies.get("access_token")
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No autenticado"
            )

        supabase = get_supabase_client()
        user = supabase.auth.get_user(token)

        if not user or not user.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido"
            )

        return {
            "user": {
                "id": user.user.id,
                "email": user.user.email,
                "created_at": str(user.user.created_at),
                "user_metadata": user.user.user_metadata
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )