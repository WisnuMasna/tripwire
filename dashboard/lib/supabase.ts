import { createClient } from "@supabase/supabase-js";

// Public, read-only. Row-level security on the `sessions` table permits SELECT
// only, so the anon key is safe to ship to the browser.
//
// The fallbacks keep `next build` working when env vars are absent (createClient
// throws on an empty URL, which would fail prerendering). At runtime the real
// values come from NEXT_PUBLIC_* .
const url = process.env.NEXT_PUBLIC_SUPABASE_URL || "https://placeholder.supabase.co";
const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "placeholder-anon-key";

export const supabase = createClient(url, key);
