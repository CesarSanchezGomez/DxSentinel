# backend/app/auth/dependencies.py
from fastapi import Request, HTTPException, status
from ..core.config import get_settings
from .supabase_client import get_supabase_client

settings = get_settings()


async def get_current_user(request: Request):
    """
    Obtiene y valida el usuario actual desde las cookies.
    Única dependencia necesaria para proteger rutas.
    """
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado"
        )

    try:
        supabase = get_supabase_client()
        user_response = supabase.auth.get_user(token)

        if not user_response or not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido o expirado"
            )

        user = user_response.user

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Error al verificar token"
        )

    if not user.email.endswith(f"@{settings.ALLOWED_DOMAIN}"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Solo se permite acceso a usuarios de @{settings.ALLOWED_DOMAIN}"
        )

    return user