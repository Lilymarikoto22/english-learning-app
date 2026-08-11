import os
from supabase import create_client, Client


def get_client() -> Client:
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_KEY", "")
    if not url or not key:
        raise ValueError("SUPABASE_URL と SUPABASE_KEY を .env に設定してください")
    return create_client(url, key)
