"use client";

import { FocusTimer } from "@/components/FocusTimer";
import { useRequireAuth } from "@/lib/useRequireAuth";

export default function TimerPage() {
  const { user, loading } = useRequireAuth();

  if (loading || !user) return null;

  return (
    <div className="animate-fade-in">
      <div className="mb-8 text-center">
        <h1 className="text-2xl font-semibold">Focus timer</h1>
        <p className="mt-1 text-sm text-text-muted">
          Work in focused sprints, then take a break. Stay disciplined.
        </p>
      </div>
      <FocusTimer />
    </div>
  );
}
