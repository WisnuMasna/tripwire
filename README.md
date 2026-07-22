# Tripwire — public honeypot + AI-triage dashboard

A real, internet-facing honeypot that attracts genuine attack traffic, pipes it
through a detection stack, enriches each session with threat intel, has Claude
write a plain-English summary and risk score for every attack, and surfaces it
all on a public, auto-updating dashboard.

Portfolio piece. Priorities: works end-to-end against real attackers, looks good
in a 30-second screen recording, and is safely isolated.

## Architecture

```
Internet attackers
      → Cowrie honeypot (Docker, isolated VPS)        [honeypot/]   Phase 1  ✅
      → Wazuh agent ships cowrie.json → Wazuh manager  [wazuh/]      Phase 2
      → FastAPI triage: enrich + Claude summary/score  [triage-service/] Phase 3
      → Supabase Postgres (RLS, read-only public)      [db/schema.sql]
      → Next.js dashboard on Vercel                    [dashboard/]  Phase 4
```

The Wazuh manager already runs locally in [`wazuh-lab/`](wazuh-lab) (v4.9.2,
API on `55000`) — Phase 2 reuses it rather than standing up a new one.

## Repo layout

| Path | Phase | Status |
|------|-------|--------|
| [`honeypot/`](honeypot) | 1 — Cowrie SSH/Telnet honeypot | **built + testable** |
| [`wazuh/`](wazuh) | 2 — custom decoders/rules + agent config | scaffold |
| [`triage-service/`](triage-service) | 3 — FastAPI enrich + Claude triage | scaffold |
| [`db/schema.sql`](db/schema.sql) | 3 — Supabase table + RLS | ready to run |
| [`dashboard/`](dashboard) | 4 — Next.js public dashboard | scaffold |
| `.env.example` | — | copy to `.env`, fill per phase |

## Quick start (Phase 1)

```bash
cd honeypot
./setup.sh
docker compose up -d
./test-connection.sh
```

See [`honeypot/README.md`](honeypot/README.md) for the VPS deployment + isolation
checklist (spec §4 — non-negotiable).

## Build order

Phases are independently testable and built in order: **1 → 2 → 3 → 4 → 5 (polish)**.
Phase 0 (VPS, Supabase project, API keys) is manual and done outside this repo.

## Safety / disclaimer

Passive logging only. No counter-hacking. Source IPs shown on the dashboard are
attacker-controlled or spoofed addresses, surfaced for situational awareness, not
doxxing. The honeypot is emulated (Cowrie) and isolated; it is never actually
compromised.

> This folder is also a VirtualBox VM directory. `.gitignore` excludes the VM
> disk/snapshots (`*.vdi`, `Snapshots/`, …) and all secrets. `git init` has **not**
> been run — do that yourself when ready.
