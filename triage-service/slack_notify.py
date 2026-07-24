"""Post high-notability attacker sessions to a Slack incoming webhook.

Tier 1 of the Hivewire-style SOAR layer: the honeypot stays wide open, but when
Claude scores a session at or above SLACK_NOTIFY_THRESHOLD it escalates to Slack.
Heuristic-filtered scans are always score 1, so this only fires on genuinely
interesting attackers. A no-op (and never raises) when the webhook is unset.
"""
from __future__ import annotations

import httpx

from config import settings

DASHBOARD_URL = "https://tripwire-chi.vercel.app/"


async def notify(
    session: dict,
    enr: dict,
    summary: str,
    techniques: list[str],
    score: int,
    disp: dict | None = None,
) -> None:
    if not settings.slack_webhook_url or score < settings.slack_notify_threshold:
        return

    ip = session.get("source_ip", "?")
    loc = enr.get("country") or "unknown location"
    asn = enr.get("asn")
    cmds = session.get("commands_tried") or []
    disp = disp or {}

    rep = []
    if enr.get("abuseipdb_score") is not None:
        rep.append(f"AbuseIPDB {enr['abuseipdb_score']}")
    if enr.get("vt_malicious_count") is not None:
        rep.append(f"VT malicious {enr['vt_malicious_count']}")

    lines = [
        f":rotating_light: *Notable attack — score {score}/5*",
        f"*{ip}* — {loc}" + (f" · {asn}" if asn else "") + (f" · {' · '.join(rep)}" if rep else ""),
    ]
    if disp.get("verdict"):
        lines.append(
            f"*Verdict:* {disp['verdict']}   *Recommended action:* {disp.get('recommended_action', '?')}"
        )
    lines.append(summary)
    if techniques:
        lines.append("*MITRE:* " + ", ".join(techniques))
    if cmds:
        lines.append("*Commands:*\n```" + "\n".join(cmds[:12]) + "```")
    lines.append(f"<{DASHBOARD_URL}|View dashboard>")

    try:
        async with httpx.AsyncClient(timeout=10.0) as c:
            await c.post(settings.slack_webhook_url, json={"text": "\n".join(lines)})
    except Exception:
        # Slack must never break the triage pipeline.
        pass
