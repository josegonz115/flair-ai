import os
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
BUCKET_NAME = "images"  

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

__all__ = ["supabase", "BUCKET_NAME"]