"""Settings loaded from the repo-root .env (Phase 3)."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Load the shared repo-root .env; ignore vars meant for other services.
    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

    # Claude
    anthropic_api_key: str
    anthropic_model: str = "claude-sonnet-5"   # spec chose Sonnet; opus-4-8 also works

    # Threat-intel enrichment (optional — enrichment degrades gracefully if unset)
    abuseipdb_api_key: str | None = None
    virustotal_api_key: str | None = None

    # Supabase (service role — bypasses RLS to write)
    supabase_url: str
    supabase_service_role_key: str

    # Wazuh indexer (OpenSearch) — source of Cowrie alerts
    wazuh_indexer_url: str = "https://localhost:9200"
    wazuh_indexer_user: str = "admin"
    wazuh_indexer_password: str

    poll_interval_seconds: int = 60
    session_grace_seconds: int = 180

    # Slack escalation (SOAR tier 1). Blank = disabled. The webhook URL is a
    # secret; keep it in .env only.
    slack_webhook_url: str | None = None
    slack_notify_threshold: int = 4

    # TheHive case creation (SOAR tier 2). Blank api_key = disabled.
    thehive_url: str = "http://localhost:9000"
    thehive_api_key: str | None = None
    thehive_case_threshold: int = 4


settings = Settings()  # raises at import if required vars are missing
