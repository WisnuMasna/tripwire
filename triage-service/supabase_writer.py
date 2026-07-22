"""Write a finished session row to Supabase (Phase 3).

The service-role key bypasses RLS. supabase-py is sync, so callers wrap this in
asyncio.to_thread. Upsert is idempotent on the cowrie_session unique column, so
re-processing the same session just overwrites the row.
"""
from __future__ import annotations

from supabase import create_client

from config import settings

_sb = create_client(settings.supabase_url, settings.supabase_service_role_key)


def upsert_session(row: dict) -> None:
    _sb.table("sessions").upsert(row, on_conflict="cowrie_session").execute()
