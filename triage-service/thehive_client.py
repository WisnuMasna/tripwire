"""Open a TheHive case for high-notability attacker sessions (SOAR tier 2).

Reuses the TheHive instance already running on the SIEM host. When Claude scores
a session at or above THEHIVE_CASE_THRESHOLD, a case is created with the AI
writeup, MITRE tags and the command transcript, plus the source IP added as an
IOC observable. A no-op (and never raises) when THEHIVE_API_KEY is unset.
"""
from __future__ import annotations

import httpx

from config import settings

DASHBOARD_URL = "https://tripwire-chi.vercel.app/"


def _severity(score: int) -> int:
    # TheHive severity: 1 Low, 2 Medium, 3 High, 4 Critical.
    return {5: 4, 4: 3}.get(score, 2)


def _description(session: dict, enr: dict, summary: str, techniques: list[str], score: int) -> str:
    ip = session.get("source_ip", "?")
    loc = enr.get("country") or "unknown"
    asn = enr.get("asn")
    cmds = session.get("commands_tried") or []
    parts = [
        summary,
        "",
        f"**Source:** {ip} ({loc}" + (f", {asn}" if asn else "") + ")",
        f"**Notability:** {score}/5",
    ]
    if techniques:
        parts.append("**MITRE:** " + ", ".join(techniques))
    if enr.get("abuseipdb_score") is not None:
        parts.append(f"**AbuseIPDB confidence:** {enr['abuseipdb_score']}")
    if enr.get("vt_malicious_count") is not None:
        parts.append(f"**VirusTotal malicious:** {enr['vt_malicious_count']}")
    if cmds:
        parts.append("**Commands:**\n```\n" + "\n".join(cmds[:20]) + "\n```")
    parts.append(f"[Live dashboard]({DASHBOARD_URL})")
    return "\n".join(parts)


async def create_case(
    session: dict,
    enr: dict,
    summary: str,
    techniques: list[str],
    score: int,
) -> str | None:
    if not settings.thehive_api_key or score < settings.thehive_case_threshold:
        return None

    ip = session.get("source_ip", "?")
    loc = enr.get("country") or "unknown"
    tags = ["tripwire", "honeypot"]
    tags += [t.split(":")[0].strip() for t in techniques]
    if enr.get("country"):
        tags.append(enr["country"])

    headers = {"Authorization": f"Bearer {settings.thehive_api_key}"}
    try:
        async with httpx.AsyncClient(
            base_url=settings.thehive_url, headers=headers, timeout=15.0
        ) as c:
            r = await c.post(
                "/api/case",
                json={
                    "title": f"Honeypot attack from {ip} ({loc}) — score {score}/5",
                    "description": _description(session, enr, summary, techniques, score),
                    "severity": _severity(score),
                    "tlp": 2,
                    "pap": 2,
                    "tags": tags,
                },
            )
            r.raise_for_status()
            body = r.json()
            case_id = body.get("_id") or body.get("id")

            # Add the attacker IP as an IOC observable.
            await c.post(
                f"/api/case/{case_id}/artifact",
                json={
                    "dataType": "ip",
                    "data": ip,
                    "message": f"Honeypot attacker source ({loc})",
                    "tags": ["tripwire"],
                    "tlp": 2,
                    "ioc": True,
                },
            )
            return case_id
    except Exception as e:  # never break triage
        print(f"thehive: {type(e).__name__}: {e}")
        return None
