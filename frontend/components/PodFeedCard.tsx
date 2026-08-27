import type { PodMemberFeedItem } from "@/lib/types";
import { StreakBadge } from "@/components/StreakBadge";

function relativeTime(iso: string | null): string {
  if (!iso) return "no activity yet";
  const hours = Math.floor((Date.now() - new Date(iso).getTime()) / 3_600_000);
  if (hours < 1) return "just now";
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return days === 1 ? "yesterday" : `${days} days ago`;
}

export function PodFeedCard({
  member,
  isMe,
}: {
  member: PodMemberFeedItem;
  isMe: boolean;
}) {
  // 24h+ quiet is exactly what triggers the nudge push, so flag it visually too.
  const quiet =
    !member.active_today &&
    (!member.last_active_at ||
      Date.now() - new Date(member.last_active_at).getTime() > 24 * 3_600_000);

  return (
    <li className="flex items-center justify-between gap-3 border-b border-border px-4 py-3 last:border-b-0">
      <div className="flex min-w-0 items-center gap-3">
        <span
          aria-hidden
          className={`h-2 w-2 shrink-0 rounded-full ${
            member.active_today ? "bg-success" : quiet ? "bg-danger" : "bg-border"
          }`}
        />
        <div className="min-w-0">
          <p className="truncate text-sm font-medium">
            {member.display_name}
            {isMe && <span className="ml-1.5 text-xs text-text-faint">you</span>}
          </p>
          <p className="text-xs text-text-muted">
            {member.active_today ? "Active today" : relativeTime(member.last_active_at)}
          </p>
        </div>
      </div>
      <StreakBadge days={member.current_streak} activeToday={member.active_today} />
    </li>
  );
}
