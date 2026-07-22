"""Threat-intel enrichment for a source IP (Phase 3).

Degrades gracefully: GeoIP uses the free keyless ip-api.com; AbuseIPDB and
VirusTotal are skipped if their keys aren't set. Any lookup failure returns
None for that field rather than aborting the session.
"""
from __future__ import annotations

import httpx

from config import settings


async def enrich_ip(ip: str) -> dict:
    out = {
        "country": None,
        "asn": None,
        "abuseipdb_score": None,
        "vt_malicious_count": None,
    }
    async with httpx.AsyncClient(timeout=15.0) as c:
        # GeoIP + ASN (free, no key)
        try:
            r = await c.get(f"http://ip-api.com/json/{ip}", params={"fields": "country,as"})
            if r.status_code == 200:
                j = r.json()
                out["country"] = j.get("country")
                out["asn"] = j.get("as")
        except Exception:
            pass

        if settings.abuseipdb_api_key:
            try:
                r = await c.get(
                    "https://api.abuseipdb.com/api/v2/check",
                    headers={"Key": settings.abuseipdb_api_key, "Accept": "application/json"},
                    params={"ipAddress": ip, "maxAgeInDays": 90},
                )
                if r.status_code == 200:
                    out["abuseipdb_score"] = r.json()["data"]["abuseConfidenceScore"]
            except Exception:
                pass

        if settings.virustotal_api_key:
            try:
                r = await c.get(
                    f"https://www.virustotal.com/api/v3/ip_addresses/{ip}",
                    headers={"x-apikey": settings.virustotal_api_key},
                )
                if r.status_code == 200:
                    stats = r.json()["data"]["attributes"]["last_analysis_stats"]
                    out["vt_malicious_count"] = stats.get("malicious")
            except Exception:
                pass
    return out
