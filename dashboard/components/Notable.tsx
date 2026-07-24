"use client";

import { useState } from "react";
import type { Session } from "@/lib/types";
import { VerdictBadge, ActionBadge } from "./disposition";

function Chip({ children }: { children: React.ReactNode }) {
  return (
    <span className="rounded bg-slate-800 px-1.5 py-0.5 font-mono text-xs text-slate-300">
      {children}
    </span>
  );
}

function Card({ s }: { s: Session }) {
  const [open, setOpen] = useState(false);
  const score = s.ai_notability_score ?? 0;

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/50">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-start gap-3 p-4 text-left hover:bg-slate-800/30"
        aria-expanded={open}
      >
        <span
          className={`mt-0.5 rounded px-2 py-1 text-sm font-bold tabular-nums ${
            score >= 5
              ? "bg-red-500/20 text-red-300 ring-1 ring-red-500/40"
              : score >= 4
                ? "bg-orange-500/20 text-orange-300 ring-1 ring-orange-500/40"
                : "bg-amber-500/20 text-amber-300 ring-1 ring-amber-500/40"
          }`}
        >
          {score}
        </span>
        <span className="min-w-0 flex-1">
          <span className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm">
            <span className="font-mono text-slate-200">{s.source_ip}</span>
            {s.country && <span className="text-slate-400">{s.country}</span>}
            {s.asn && (
              <span className="truncate text-xs text-slate-600">{s.asn}</span>
            )}
            <VerdictBadge verdict={s.verdict} />
            <ActionBadge action={s.recommended_action} />
          </span>
          <span className="mt-1 block text-sm leading-snug text-slate-400">
            {s.ai_summary}
          </span>
        </span>
        <span className="mt-1 text-xs text-slate-600">{open ? "−" : "+"}</span>
      </button>

      {open && (
        <div className="space-y-3 border-t border-slate-800 px-4 py-3 text-sm">
          {!!s.mitre_techniques?.length && (
            <div>
              <div className="mb-1 text-xs uppercase tracking-wider text-slate-500">
                MITRE techniques
              </div>
              <div className="flex flex-wrap gap-1">
                {s.mitre_techniques.map((t) => (
                  <Chip key={t}>{t}</Chip>
                ))}
              </div>
            </div>
          )}

          {!!s.commands_tried?.length && (
            <div>
              <div className="mb-1 text-xs uppercase tracking-wider text-slate-500">
                Commands attempted
              </div>
              <pre className="overflow-x-auto rounded bg-slate-950 p-3 font-mono text-xs text-emerald-300">
                {s.commands_tried.join("\n")}
              </pre>
            </div>
          )}

          <div className="grid grid-cols-2 gap-3 text-xs">
            {!!s.usernames_tried?.length && (
              <div>
                <div className="mb-1 uppercase tracking-wider text-slate-500">
                  Usernames
                </div>
                <div className="flex flex-wrap gap-1">
                  {s.usernames_tried.map((u) => (
                    <Chip key={u}>{u}</Chip>
                  ))}
                </div>
              </div>
            )}
            {!!s.passwords_tried?.length && (
              <div>
                <div className="mb-1 uppercase tracking-wider text-slate-500">
                  Passwords
                </div>
                <div className="flex flex-wrap gap-1">
                  {s.passwords_tried.map((p) => (
                    <Chip key={p}>{p}</Chip>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="flex flex-wrap gap-4 border-t border-slate-800 pt-2 text-xs text-slate-500">
            {s.abuseipdb_score !== null && (
              <span>AbuseIPDB confidence: {s.abuseipdb_score}</span>
            )}
            {s.vt_malicious_count !== null && (
              <span>VirusTotal malicious: {s.vt_malicious_count}</span>
            )}
            <span>{new Date(s.started_at).toUTCString()}</span>
          </div>
        </div>
      )}
    </div>
  );
}

export default function Notable({ sessions }: { sessions: Session[] }) {
  const notable = sessions
    .filter((s) => (s.ai_notability_score ?? 0) >= 3)
    .sort(
      (a, b) =>
        (b.ai_notability_score ?? 0) - (a.ai_notability_score ?? 0) ||
        +new Date(b.started_at) - +new Date(a.started_at),
    )
    .slice(0, 20);

  return (
    <section>
      <h2 className="mb-3 text-sm font-semibold text-slate-200">
        Notable attacks{" "}
        <span className="font-normal text-slate-500">
          — scored 3+ by Claude, most interesting first
        </span>
      </h2>
      <div className="space-y-2">
        {notable.length === 0 && (
          <p className="rounded-lg border border-slate-800 bg-slate-900/50 p-6 text-center text-sm text-slate-600">
            Nothing notable yet — most traffic so far is routine scanning.
          </p>
        )}
        {notable.map((s) => (
          <Card key={s.id} s={s} />
        ))}
      </div>
    </section>
  );
}
