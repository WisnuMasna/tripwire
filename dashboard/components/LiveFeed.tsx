import type { Session } from "@/lib/types";

function ago(iso: string) {
  const secs = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (secs < 60) return `${Math.floor(secs)}s ago`;
  if (secs < 3600) return `${Math.floor(secs / 60)}m ago`;
  if (secs < 86400) return `${Math.floor(secs / 3600)}h ago`;
  return `${Math.floor(secs / 86400)}d ago`;
}

function scoreColor(score: number | null) {
  if (score === null) return "bg-slate-700 text-slate-300";
  if (score >= 5) return "bg-red-500/20 text-red-300 ring-1 ring-red-500/40";
  if (score >= 4) return "bg-orange-500/20 text-orange-300 ring-1 ring-orange-500/40";
  if (score >= 3) return "bg-amber-500/20 text-amber-300 ring-1 ring-amber-500/40";
  return "bg-slate-800 text-slate-400";
}

export default function LiveFeed({ sessions }: { sessions: Session[] }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/50">
      <div className="flex items-center gap-2 border-b border-slate-800 px-4 py-3">
        <span className="live-dot h-2 w-2 rounded-full bg-emerald-400" />
        <h2 className="text-sm font-semibold text-slate-200">Live attack feed</h2>
        <span className="ml-auto text-xs text-slate-500">auto-refreshes every 30s</span>
      </div>
      <ul className="max-h-[32rem] divide-y divide-slate-800/70 overflow-y-auto">
        {sessions.length === 0 && (
          <li className="p-6 text-center text-sm text-slate-600">
            Waiting for the first captured session…
          </li>
        )}
        {sessions.map((s) => (
          <li key={s.id} className="px-4 py-3 hover:bg-slate-800/30">
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
              <span
                className={`rounded px-1.5 py-0.5 text-xs font-semibold tabular-nums ${scoreColor(
                  s.ai_notability_score,
                )}`}
                title="Claude notability score (1-5)"
              >
                {s.ai_notability_score ?? "-"}
              </span>
              <span className="font-mono text-sm text-slate-200">{s.source_ip}</span>
              {s.country && (
                <span className="text-xs text-slate-400">{s.country}</span>
              )}
              <span className="text-xs uppercase text-slate-600">
                {s.protocol ?? "ssh"}
              </span>
              <span className="ml-auto text-xs tabular-nums text-slate-500">
                {ago(s.started_at)}
              </span>
            </div>
            {s.ai_summary && (
              <p className="mt-1 line-clamp-2 text-sm leading-snug text-slate-400">
                {s.ai_summary}
              </p>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
