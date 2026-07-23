# Phase 3 — triage service

Turns Wazuh Cowrie alerts into enriched, AI-scored rows in Supabase.

```
Wazuh indexer (:9200)  →  poll + group by session  →  enrich source IP
   →  Claude summary + notability score  →  upsert into Supabase.sessions
```

| File | Purpose |
|------|---------|
| `main.py` | FastAPI app + async poll loop (the orchestrator) |
| `config.py` | Settings from the repo-root `.env` (pydantic-settings) |
| `wazuh_client.py` | Queries the indexer for `cowrie`-group alerts since a timestamp |
| `sessions.py` | Groups flat alerts into per-session records |
| `enrichment.py` | GeoIP (ip-api.com) + AbuseIPDB + VirusTotal for the source IP |
| `claude_client.py` | Structured-output Claude call → summary / MITRE / score |
| `prompts/triage_prompt.md` | The system prompt — edit to tune the AI's voice |
| `supabase_writer.py` | Idempotent upsert on `cowrie_session` |

## Prerequisites you must create (Phase-0-style, your step)

1. **Supabase project** → run [`../db/schema.sql`](../db/schema.sql) in its SQL editor.
   Copy the project URL + **service_role** key.
2. **Anthropic API key** (console.anthropic.com).
3. *(optional but recommended)* **AbuseIPDB** and **VirusTotal** API keys (free tiers).

Fill these into the repo-root `.env` (see [`../.env.example`](../.env.example)).
`WAZUH_INDEXER_*` defaults already match the wazuh-lab stack.

## Run it (on TheHive-5, next to the indexer)

```bash
cp ../.env.example ../.env      # then fill in the keys above
cd triage-service
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

The loop starts automatically. Watch it:
```bash
curl -s localhost:8000/health    # {"status":"ok","processed_total":N,"pending":M,...}
```
and it prints one line per triaged session — `[ai]` when Claude wrote the
summary, `[fast]` when it was a trivial scan handled without an LLM call:
```
[ai]   195.178.110.217 score=3: Automated scanner ran OS-fingerprinting commands...
[fast] 45.153.34.235   score=1: Automated SSH login scan from 45.153.34.235 (The Netherlands)...
```

## Run it as a service (survives reboots)

`uvicorn` in a terminal dies with your shell. For anything long-lived, install
the bundled systemd unit:

```bash
sudo cp triage-service/tripwire-triage.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now tripwire-triage
```

```bash
systemctl status tripwire-triage      # is it up?
journalctl -u tripwire-triage -f      # live triage output
sudo systemctl restart tripwire-triage
```

It starts after Docker (the Wazuh indexer it polls runs there) and restarts
automatically on failure.

## Cost control

The honeypot is scanned continuously and most sessions are a bare connect or a
single failed login. Those are summarised from a template and never reach the
API — Claude is spent only on sessions where the attacker ran commands,
transferred a file, or attempted a tunnel. `/health` reports the split via
`triaged_by_ai` and `triaged_heuristically`.

## Verify end to end

1. Trigger a session: `ssh root@<honeypot-ip>` (the honeypot), run a few commands, exit.
2. Within ~a minute the loop enriches + triages it and the row appears in Supabase
   (Table editor → `sessions`).
3. That row is exactly what the **Phase 4** dashboard reads.

## Notes / first-version scope

- Reads from the **indexer** (`:9200`), not the manager API — alerts are stored there.
- A session is triaged when Cowrie sends `cowrie.session.closed`, or after
  `SESSION_GRACE_SECONDS` of no new events (catches sessions that never close cleanly).
- `.state_since` persists the last-seen timestamp so restarts don't re-scan history.
- Model + prompt are env/file configurable; thinking is off by default for
  cost — flip to adaptive in `claude_client.py` for richer scoring.
