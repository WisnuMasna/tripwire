"""Tripwire triage service (Phase 3).

Loop: poll the Wazuh indexer for new Cowrie alerts → group into sessions →
when a session closes (or goes idle past the grace period) enrich its source IP,
ask Claude for a summary + notability score, and upsert the row into Supabase.
"""
from __future__ import annotations

import asyncio
import contextlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI

from config import settings
from wazuh_client import WazuhIndexerClient
from sessions import group_sessions
from enrichment import enrich_ip
from claude_client import triage_session
from supabase_writer import upsert_session

_STATE_FILE = Path(__file__).parent / ".state_since"

state = {"processed_total": 0, "pending": 0, "last_error": None}
_pending: dict[str, dict] = {}
_processed: set[str] = set()


def _parse_ts(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _load_since() -> str:
    if _STATE_FILE.exists():
        return _STATE_FILE.read_text().strip()
    return (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()


def _save_since(iso: str) -> None:
    _STATE_FILE.write_text(iso)


def _merge(new: dict[str, dict]) -> None:
    for sid, s in new.items():
        p = _pending.get(sid)
        if p is None:
            _pending[sid] = s
            continue
        p["source_ip"] = p["source_ip"] or s["source_ip"]
        p["protocol"] = p["protocol"] or s["protocol"]
        p["usernames_tried"] = list(dict.fromkeys(p["usernames_tried"] + s["usernames_tried"]))
        p["passwords_tried"] = list(dict.fromkeys(p["passwords_tried"] + s["passwords_tried"]))
        p["commands_tried"] = p["commands_tried"] + s["commands_tried"]
        p["started_at"] = p["started_at"] or s["started_at"]
        p["ended_at"] = s["ended_at"] or p["ended_at"]
        p["closed"] = p["closed"] or s["closed"]
        if s["last_ts"] and (not p["last_ts"] or s["last_ts"] > p["last_ts"]):
            p["last_ts"] = s["last_ts"]


async def _process(s: dict) -> None:
    ip = s.get("source_ip")
    if not ip:
        return  # schema requires source_ip
    enr = await enrich_ip(ip)
    triage = await triage_session({**s, **enr})
    row = {
        "cowrie_session": s["cowrie_session"],
        "source_ip": ip,
        "country": enr.get("country"),
        "asn": enr.get("asn"),
        "protocol": s.get("protocol"),
        "started_at": s.get("started_at"),
        "ended_at": s.get("ended_at"),
        "usernames_tried": s.get("usernames_tried"),
        "passwords_tried": s.get("passwords_tried"),
        "commands_tried": s.get("commands_tried"),
        "abuseipdb_score": enr.get("abuseipdb_score"),
        "vt_malicious_count": enr.get("vt_malicious_count"),
        "mitre_techniques": triage.mitre_techniques,
        "ai_summary": triage.summary,
        "ai_notability_score": triage.notability_score,
    }
    await asyncio.to_thread(upsert_session, row)
    state["processed_total"] += 1
    print(f"[triage] {ip} score={triage.notability_score}: {triage.summary[:80]}")


async def _flush() -> None:
    grace = timedelta(seconds=settings.session_grace_seconds)
    now = datetime.now(timezone.utc)
    ready = [
        sid for sid, s in _pending.items()
        if s["closed"] or (s["last_ts"] and now - _parse_ts(s["last_ts"]) > grace)
    ]
    for sid in ready:
        s = _pending.pop(sid)
        if sid in _processed:
            continue
        try:
            await _process(s)
            _processed.add(sid)
        except Exception as e:  # noqa: BLE001
            state["last_error"] = f"process {sid}: {e}"
            print(state["last_error"])


async def poll_loop() -> None:
    wz = WazuhIndexerClient(
        settings.wazuh_indexer_url, settings.wazuh_indexer_user, settings.wazuh_indexer_password
    )
    since = _load_since()
    try:
        while True:
            try:
                alerts = await wz.new_cowrie_alerts(since)
                if alerts:
                    _merge(group_sessions(alerts))
                    newest = max((a.get("timestamp") for a in alerts if a.get("timestamp")), default=since)
                    since = newest
                    _save_since(since)
                await _flush()
                state["pending"] = len(_pending)
            except Exception as e:  # noqa: BLE001
                state["last_error"] = f"poll: {e}"
                print(state["last_error"])
            await asyncio.sleep(settings.poll_interval_seconds)
    finally:
        await wz.aclose()


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(poll_loop())
    yield
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task


app = FastAPI(title="Tripwire Triage Service", lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", **state}
