// Shared styling for the analyst disposition (verdict + recommended action).

const VERDICT_STYLE: Record<string, string> = {
  malicious: "bg-red-500/20 text-red-300 ring-1 ring-red-500/40",
  suspicious: "bg-orange-500/20 text-orange-300 ring-1 ring-orange-500/40",
  reconnaissance: "bg-sky-500/15 text-sky-300 ring-1 ring-sky-500/30",
  noise: "bg-slate-700/40 text-slate-400 ring-1 ring-slate-600/40",
};

const ACTION_STYLE: Record<string, string> = {
  escalate: "bg-red-500/15 text-red-300",
  block: "bg-orange-500/15 text-orange-300",
  monitor: "bg-slate-700/40 text-slate-300",
  dismiss: "bg-slate-800 text-slate-500",
};

export function VerdictBadge({ verdict }: { verdict: string | null }) {
  if (!verdict) return null;
  return (
    <span
      className={`rounded px-1.5 py-0.5 text-[11px] font-medium capitalize ${
        VERDICT_STYLE[verdict] ?? "bg-slate-800 text-slate-400"
      }`}
    >
      {verdict}
    </span>
  );
}

export function ActionBadge({ action }: { action: string | null }) {
  if (!action) return null;
  return (
    <span
      className={`rounded px-1.5 py-0.5 text-[11px] font-medium capitalize ${
        ACTION_STYLE[action] ?? "bg-slate-800 text-slate-400"
      }`}
      title="Recommended action"
    >
      → {action}
    </span>
  );
}
