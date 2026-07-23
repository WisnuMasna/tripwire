import type { Session } from "@/lib/types";

function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-4">
      <div className="text-xs font-medium uppercase tracking-wider text-slate-500">
        {label}
      </div>
      <div className="mt-1 text-3xl font-semibold tabular-nums text-slate-100">
        {value}
      </div>
      {hint && <div className="mt-1 text-xs text-slate-500">{hint}</div>}
    </div>
  );
}

export default function Stats({ sessions }: { sessions: Session[] }) {
  const uniqueIps = new Set(sessions.map((s) => s.source_ip)).size;
  const countries = new Set(
    sessions.map((s) => s.country).filter((c): c is string => !!c),
  ).size;
  const notable = sessions.filter((s) => (s.ai_notability_score ?? 0) >= 3).length;
  const withCommands = sessions.filter((s) => (s.commands_tried?.length ?? 0) > 0).length;

  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
      <Stat label="Sessions" value={sessions.length.toLocaleString()} hint="most recent 500" />
      <Stat label="Unique IPs" value={uniqueIps.toLocaleString()} />
      <Stat label="Countries" value={countries.toLocaleString()} />
      <Stat label="Ran commands" value={withCommands.toLocaleString()} hint="reached a shell" />
      <Stat label="Notable" value={notable.toLocaleString()} hint="scored 3+" />
    </div>
  );
}
