# Phase 4 — public dashboard

Next.js (App Router, TypeScript, Tailwind v4) reading the `sessions` table from
Supabase with the **anon** key. Row-level security permits `SELECT` only, so the
key is safe in the browser.

## Local development

```bash
cd dashboard
npm install
cp .env.local.example .env.local   # fill in the two NEXT_PUBLIC_ values
npm run dev                        # http://localhost:3000
```

Required environment variables:

| Variable | Where to find it |
|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase → Project Settings → API → Project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | same page → **anon / publishable** key (never the service role key) |

## Deploy to Vercel

1. Import the repo at [vercel.com/new](https://vercel.com/new)
2. Set **Root Directory** to `dashboard`
3. Add both `NEXT_PUBLIC_*` variables above
4. Deploy

## What it renders

- **Stats** — sessions, unique IPs, countries, how many reached a shell, notable count
- **Live feed** — most recent sessions, auto-refreshing every 30s, colour-coded by score
- **Top lists** — attacking countries, MITRE techniques, most-tried usernames/passwords
- **Notable attacks** — everything Claude scored 3+, expandable to show the full
  command transcript, credentials tried, and reputation data
