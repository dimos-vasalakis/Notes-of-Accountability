"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { api } from "@/lib/api";
import type { PodFeed } from "@/lib/types";
import { useCurrentUser } from "@/lib/useCurrentUser";
import { useExamPrep } from "@/lib/useExamPrep";
import { useMyStreak } from "@/lib/useMyStreak";
import { usePods } from "@/lib/usePods";
import { ExamCountdownCard } from "@/components/ExamCountdownCard";
import { PodFeedCard } from "@/components/PodFeedCard";
import { StreakBadge } from "@/components/StreakBadge";
import { Card } from "@/components/ui/Card";

const QUICK_LINKS = [
  { href: "/tasks", label: "Tasks", icon: "✓" },
  { href: "/notes", label: "Notes", icon: "✎" },
  { href: "/timer", label: "Focus", icon: "◷" },
  { href: "/pods", label: "Pods", icon: "👥" },
];

export default function Home() {
  const { user, loading } = useCurrentUser();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  // Gated on `user` so a logged-out visitor does not fire two 401s
  // before the redirect to /login lands.
  const { streak } = useMyStreak(Boolean(user));
  const { pods } = usePods(Boolean(user));
  const { config } = useExamPrep(Boolean(user?.is_student));

  if (loading || !user) return null;

  const primaryPod = pods[0] ?? null;
  const greeting = user.display_name ?? user.email.split("@")[0];

  return (
    <div className="animate-fade-in flex flex-col gap-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Today</h1>
          <p className="mt-1 text-sm text-text-muted">
            Welcome back, {greeting}.
          </p>
        </div>
        {streak && (
          <StreakBadge
            days={streak.current_streak}
            activeToday={streak.active_today}
            size="lg"
          />
        )}
      </header>

      {streak && !streak.active_today && (
        <Card className="border-warning/30 bg-warning-soft p-4">
          <p className="text-sm text-text">
            {streak.current_streak > 0
              ? `Nothing logged today — your ${streak.current_streak}-day streak is still standing, but only until midnight.`
              : "Nothing logged today. Finish one task or one focus session to start a streak."}
          </p>
        </Card>
      )}

      {config && <ExamCountdownCard config={config} />}

      {primaryPod ? (
        <PodSnapshot podId={primaryPod.id} currentUserId={user.id} />
      ) : (
        <Card className="p-6 text-center">
          <p className="text-2xl" aria-hidden>
            👥
          </p>
          <p className="mt-2 text-sm font-medium">Study with people who show up</p>
          <p className="mt-1 text-sm text-text-muted">
            Join a pod and your streak becomes visible to the people studying alongside
            you.
          </p>
          <Link
            href="/pods"
            className="mt-4 inline-block text-sm font-medium text-accent hover:underline"
          >
            Create or join a pod →
          </Link>
        </Card>
      )}

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {QUICK_LINKS.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className="flex flex-col items-center gap-1.5 rounded-2xl border border-border bg-bg-elevated px-3 py-4 text-sm font-medium transition-colors hover:border-accent hover:text-accent"
          >
            <span className="text-lg" aria-hidden>
              {link.icon}
            </span>
            {link.label}
          </Link>
        ))}
      </div>
    </div>
  );
}

function PodSnapshot({
  podId,
  currentUserId,
}: {
  podId: string;
  currentUserId: string;
}) {
  const [feed, setFeed] = useState<PodFeed | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .get<PodFeed>(`/api/pods/${podId}/feed`)
      .then((next) => {
        if (!cancelled) setFeed(next);
      })
      .catch(() => {
        if (!cancelled) setFeed(null);
      });
    return () => {
      cancelled = true;
    };
  }, [podId]);

  if (!feed) return null;

  return (
    <Card className="overflow-hidden">
      <div className="flex items-center justify-between gap-3 border-b border-border px-4 py-3">
        <h2 className="truncate font-display text-lg font-semibold">{feed.pod.name}</h2>
        <Link href="/pods" className="shrink-0 text-xs text-accent hover:underline">
          All pods →
        </Link>
      </div>
      <ul>
        {feed.members.slice(0, 5).map((member) => (
          <PodFeedCard
            key={member.user_id}
            member={member}
            isMe={member.user_id === currentUserId}
          />
        ))}
      </ul>
    </Card>
  );
}
