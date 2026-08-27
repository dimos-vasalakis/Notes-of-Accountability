import type { SubjectAllocation } from "@/lib/types";

function formatDuration(seconds: number): string {
  if (seconds === 0) return "—";
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.round((seconds % 3600) / 60);
  return hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`;
}

/** Delta below this reads as "on target" rather than over/under-studied. */
const ON_TARGET_THRESHOLD = 0.05;

export function SubjectAllocationBar({ row }: { row: SubjectAllocation }) {
  const planned = Math.round(row.planned_share * 100);
  const actual = Math.round(row.actual_share * 100);
  const onTarget = Math.abs(row.delta) < ON_TARGET_THRESHOLD;
  const behind = row.delta < 0;

  return (
    <div className="py-3">
      <div className="flex items-baseline justify-between gap-3">
        <p className="truncate text-sm font-medium" title={row.name_el}>
          {row.name_el}
        </p>
        <p className="shrink-0 text-xs tabular-nums text-text-muted">
          {formatDuration(row.actual_seconds)}
        </p>
      </div>

      <div className="relative mt-2 h-2 rounded-full bg-bg">
        {/* Target marker: where this subject's weight says the bar should reach. */}
        <div
          className="absolute inset-y-0 rounded-full bg-accent-soft"
          style={{ width: `${planned}%` }}
        />
        <div
          className={`absolute inset-y-0 rounded-full transition-all ${
            onTarget ? "bg-success" : behind ? "bg-warning" : "bg-accent"
          }`}
          style={{ width: `${Math.min(actual, 100)}%` }}
        />
        <div
          aria-hidden
          className="absolute -top-0.5 h-3 w-0.5 rounded-full bg-text-faint"
          style={{ left: `${planned}%` }}
        />
      </div>

      <div className="mt-1.5 flex items-center justify-between text-xs">
        <span className="text-text-faint">
          target {planned}% · actual {actual}%
        </span>
        <span
          className={
            onTarget ? "text-success" : behind ? "text-warning" : "text-text-muted"
          }
        >
          {onTarget
            ? "on target"
            : behind
              ? `${Math.abs(planned - actual)}% under`
              : `${actual - planned}% over`}
        </span>
      </div>
    </div>
  );
}
