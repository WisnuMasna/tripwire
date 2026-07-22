"""Query the Wazuh indexer (OpenSearch) for Cowrie alerts (Phase 3)."""
from __future__ import annotations

import httpx


class WazuhIndexerClient:
    def __init__(self, url: str, user: str, password: str):
        # Self-signed cert in the lab → verify=False. Fine for localhost/tailnet.
        self._client = httpx.AsyncClient(
            base_url=url.rstrip("/"),
            auth=(user, password),
            verify=False,
            timeout=30.0,
        )

    async def new_cowrie_alerts(self, since_iso: str, size: int = 1000) -> list[dict]:
        """Return alert _source docs in the 'cowrie' rule group newer than since_iso."""
        body = {
            "size": size,
            "sort": [{"@timestamp": "asc"}],
            "query": {
                "bool": {
                    "filter": [
                        # rule.groups is an array of keywords; a term match works.
                        {"term": {"rule.groups": "cowrie"}},
                        {"range": {"@timestamp": {"gt": since_iso}}},
                    ]
                }
            },
        }
        r = await self._client.post("/wazuh-alerts-*/_search", json=body)
        r.raise_for_status()
        return [h["_source"] for h in r.json()["hits"]["hits"]]

    async def aclose(self) -> None:
        await self._client.aclose()
