"""
services/supabase_client.py
Thread-safe client instantiations for Supabase operations.
Provides dual interfaces: privileged service-role client and user-scoped RLS client.
"""
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions
from config import Config

# Memoized singletons for administrative services
_service_client: Client | None = None
_anon_client: Client | None = None


def get_service_client() -> Client:
    """
    Returns the privileged Supabase administrative client.
    Bypasses Row Level Security (RLS).
    MUST ONLY be used for system tasks: audit logs, landlord approvals,
    and generating short-lived signed URLs for administrators.
    """
    global _service_client
    if _service_client is None:
        _service_client = create_client(
            Config.SUPABASE_URL,
            Config.SUPABASE_SERVICE_ROLE_KEY
        )
    return _service_client


def get_anon_client() -> Client:
    """
    Returns the public client initialized with the anonymous key.
    Used for initial sign-in, OTP verification, and public reads.
    """
    global _anon_client
    if _anon_client is None:
        _anon_client = create_client(
            Config.SUPABASE_URL,
            Config.SUPABASE_KEY
        )
    return _anon_client


def get_user_client(access_token: str) -> Client:
    """
    Returns a scoped Supabase client authenticated on behalf of a specific user.
    Uses the user's JWT access token to respect PostgreSQL Row Level Security (RLS).
    """
    headers = {"Authorization": f"Bearer {access_token}"}
    options = ClientOptions(headers=headers)
    return create_client(
        Config.SUPABASE_URL,
        Config.SUPABASE_KEY,
        options=options
    )