# backend/app/auth/__init__.py
from .supabase_client import get_supabase_client
from .dependencies import get_current_user

__all__ = [
    "get_supabase_client",
    "get_current_user",
]