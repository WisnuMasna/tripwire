-- Tripwire — Supabase Postgres schema.
-- Run in the Supabase SQL editor for the project (Phase 0/3).
-- The triage service writes rows using the SERVICE ROLE key (bypasses RLS);
-- the public dashboard reads using the ANON key (SELECT only, enforced below).

create extension if not exists pgcrypto;

create table if not exists sessions (
  id                  uuid primary key default gen_random_uuid(),
  cowrie_session      text unique,        -- Cowrie session id; makes upserts idempotent
  source_ip           text not null,
  country             text,
  asn                 text,
  started_at          timestamptz not null,
  ended_at            timestamptz,
  protocol            text,               -- ssh, telnet, http
  usernames_tried     text[],
  passwords_tried     text[],
  commands_tried      text[],
  raw_log_ref         text,               -- pointer to sanitized transcript
  abuseipdb_score     int,
  vt_malicious_count  int,
  mitre_techniques    text[],
  ai_summary          text,
  ai_notability_score int,                -- 1-5
  created_at          timestamptz default now()
);

-- Dashboard query paths.
create index if not exists sessions_started_at_idx  on sessions (started_at desc);
create index if not exists sessions_source_ip_idx   on sessions (source_ip);
create index if not exists sessions_notability_idx  on sessions (ai_notability_score desc);

-- Lock the table to read-only for the public API.
alter table sessions enable row level security;

-- Public read; no insert/update/delete policy exists, so anon/authenticated
-- cannot write. The service role key used by the triage service bypasses RLS.
drop policy if exists "public read" on sessions;
create policy "public read" on sessions
  for select using (true);
