# backend/app/auth/supabase_client.py
from supabase import create_client, Client
from ..core.config import get_settings

settings = get_settings()

supabase: Client = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_KEY,
)

def get_supabase_client() -> Client:
    """Obtiene el cliente de Supabase"""
    return supabase