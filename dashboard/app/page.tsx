"use client";

import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";
import type { Session } from "@/lib/types";
import Stats from "@/components/Stats";
import TopLists from "@/components/TopLists";
import LiveFeed from "@/components/LiveFeed";
import Notable from "@/components/Notable";

export default function Page() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updated, setUpdated] = useState<Date | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      const { data, error } = await supabase
        .from("sessions")
        .select("*")
        .order("started_at", { ascending: false })
        .limit(500);

      if (cancelled) return;
      if (error) {
        setError(error.message);
      } else {
        setSessions((data ?? []) as Session[]);
        setError(null);
        setUpdated(new Date());
      }
      setLoading(false);
    }

    load();
    const timer = setInterval(load, 30_000);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, []);

  return (
    <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <header className="mb-6">
        <div className="flex flex-wrap items-baseline gap-3">
          <h1 className="text-2xl font-bold tracking-tight text-slate-100">
            Tripwire
          </h1>
          <p className="text-sm text-slate-400">
            A real honeypot on the public internet. Every attacker session is
            enriched with threat intel and summarised by Claude.
          </p>
        </div>
        {updated && (
          <p className="mt-2 text-xs text-slate-600">
            Last updated {updated.toLocaleTimeString()}
          </p>
        )}
      </header>

      {error && (
        <div className="mb-6 rounded-lg border border-red-900 bg-red-950/40 p-4 text-sm text-red-300">
          Could not load data: {error}
        </div>
      )}

      {loading ? (
        <p className="py-16 text-center text-sm text-slate-600">Loading…</p>
      ) : (
        <div className="space-y-6">
          <Stats sessions={sessions} />

          <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
            <LiveFeed sessions={sessions} />
            <TopLists sessions={sessions} />
          </div>

          <Notable sessions={sessions} />
        </div>
      )}

      <footer className="mt-10 border-t border-slate-800 pt-6 text-xs leading-relaxed text-slate-500">
        <h2 className="mb-2 text-sm font-semibold text-slate-300">About</h2>
        <p className="mb-2">
          Tripwire runs an emulated SSH/Telnet honeypot (Cowrie) on an isolated,
          disposable server. Connections are logged, parsed into alerts by Wazuh,
          enriched with GeoIP and IP-reputation data, then summarised and scored
          1–5 by Claude. Nothing here is a real production system, and the
          honeypot is never actually compromised.
        </p>
        <p>
          <strong className="text-slate-400">Passive logging only.</strong> No
          counter-hacking, no scanning back, no retaliation. Source addresses are
          attacker-controlled or spoofed and are shown for situational awareness,
          not attribution or doxxing.
        </p>
      </footer>
    </main>
  );
}
