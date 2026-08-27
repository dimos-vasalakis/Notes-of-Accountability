interface StreakBadgeProps {
  days: number;
  activeToday: boolean;
  size?: "sm" | "lg";
}

/** Flame + day count. Dimmed until today's activity is logged. */
export function StreakBadge({ days, activeToday, size = "sm" }: StreakBadgeProps) {
  const lit = days > 0 && activeToday;
  const smoldering = days > 0 && !activeToday;

  const tone = lit
    ? "bg-warning-soft text-warning"
    : smoldering
      ? "bg-bg text-text-muted"
      : "bg-bg text-text-faint";

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border border-border font-medium tabular-nums ${tone} ${
        size === "lg" ? "px-3.5 py-1.5 text-base" : "px-2.5 py-1 text-xs"
      }`}
      title={
        days === 0
          ? "No streak yet — complete a task or a focus session"
          : activeToday
            ? `${days}-day streak, active today`
            : `${days}-day streak — nothing logged today yet`
      }
    >
      <span className={lit ? "" : "opacity-50 grayscale"} aria-hidden>
        🔥
      </span>
      {days}
      <span className={size === "lg" ? "text-sm font-normal" : "sr-only"}>
        {days === 1 ? "day" : "days"}
      </span>
    </span>
  );
}
