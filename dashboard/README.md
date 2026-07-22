# Phase 4 — dashboard (scaffold)

> Status: **not built yet.** This is the public, auto-updating Next.js site — the
> piece people actually look at.

Scaffold in Phase 4 with:

```bash
cd dashboard
npx create-next-app@latest . --typescript --tailwind --app --eslint
```

Then build:
- **Live feed** — Supabase realtime subscription (or 30s polling) on `sessions`.
- **Stats header** — total sessions, unique IPs, top countries / usernames /
  passwords / ATT&CK techniques.
- **World map** — attacker origins (`react-simple-maps` or Mapbox).
- **Notable attacks** — expandable cards with Claude's writeup + sanitized transcript.
- **About / disclaimer** — passive logging only, no counter-hacking (spec §4).

Reads Supabase with the **anon** key only (`NEXT_PUBLIC_SUPABASE_URL`,
`NEXT_PUBLIC_SUPABASE_ANON_KEY`). RLS keeps it SELECT-only — see
[`../db/schema.sql`](../db/schema.sql). Deploys to Vercel.

`lib/supabase.ts` holds the browser client (stub in place).
