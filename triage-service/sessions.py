"""Fold a flat list of Cowrie alerts into per-session records (Phase 3).

Cowrie tags every event in a login attempt with the same `session` id, so we
group on that and aggregate the credentials/commands seen across the session.
"""
from __future__ import annotations


def _dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(i for i in items if i))


def group_sessions(alerts: list[dict]) -> dict[str, dict]:
    sessions: dict[str, dict] = {}
    for alert in alerts:
        data = alert.get("data", {})
        sid = data.get("session")
        if not sid:
            continue

        s = sessions.setdefault(
            sid,
            {
                "cowrie_session": sid,
                "source_ip": None,
                "protocol": None,
                "usernames_tried": [],
                "passwords_tried": [],
                "commands_tried": [],
                "started_at": None,
                "ended_at": None,
                "last_ts": None,
                "closed": False,
            },
        )

        ts = alert.get("timestamp")
        eventid = data.get("eventid", "")

        s["source_ip"] = s["source_ip"] or data.get("src_ip")
        s["protocol"] = s["protocol"] or data.get("protocol")
        if data.get("username"):
            s["usernames_tried"].append(data["username"])
        if data.get("password"):
            s["passwords_tried"].append(data["password"])
        if data.get("input"):
            s["commands_tried"].append(data["input"])
        if eventid == "cowrie.session.connect":
            s["started_at"] = s["started_at"] or ts
        if eventid == "cowrie.session.closed":
            s["ended_at"] = ts
            s["closed"] = True
        if ts and (s["last_ts"] is None or ts > s["last_ts"]):
            s["last_ts"] = ts

    for s in sessions.values():
        s["usernames_tried"] = _dedupe(s["usernames_tried"])
        s["passwords_tried"] = _dedupe(s["passwords_tried"])
    return sessions
