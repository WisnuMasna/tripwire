import type { Session } from "@/lib/types";

function tally(values: (string | null | undefined)[], limit = 6) {
  const counts = new Map<string, number>();
  for (const v of values) {
    if (!v) continue;
    counts.set(v, (counts.get(v) ?? 0) + 1);
  }
  return [...counts.entries()].sort((a, b) => b[1] - a[1]).slice(0, limit);
}

function BarList({ title, rows }: { title: string; rows: [string, number][] }) {
  const max = rows.length ? rows[0][1] : 1;
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-4">
      <h3 className="text-xs font-medium uppercase tracking-wider text-slate-500">
        {title}
      </h3>
      <div className="mt-3 space-y-2">
        {rows.length === 0 && <p className="text-sm text-slate-600">No data yet.</p>}
        {rows.map(([label, count]) => (
          <div key={label}>
            <div className="flex items-baseline justify-between gap-3 text-sm">
              <span className="truncate font-mono text-slate-300">{label}</span>
              <span className="tabular-nums text-slate-500">{count}</span>
            </div>
            <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
              <div
                className="h-full rounded-full bg-emerald-500/70"
                style={{ width: `${Math.max(4, (count / max) * 100)}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function TopLists({ sessions }: { sessions: Session[] }) {
  const countries = tally(sessions.map((s) => s.country));
  const usernames = tally(sessions.flatMap((s) => s.usernames_tried ?? []));
  const passwords = tally(sessions.flatMap((s) => s.passwords_tried ?? []));
  const techniques = tally(sessions.flatMap((s) => s.mitre_techniques ?? []));

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      <BarList title="Top attacking countries" rows={countries} />
      <BarList title="Top MITRE techniques" rows={techniques} />
      <BarList title="Most-tried usernames" rows={usernames} />
      <BarList title="Most-tried passwords" rows={passwords} />
    </div>
  );
}
