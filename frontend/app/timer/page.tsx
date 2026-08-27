"use client";

import { useState } from "react";

import { api } from "@/lib/api";
import { FocusTimer } from "@/components/FocusTimer";
import { useRequireAuth } from "@/lib/useRequireAuth";

export default function TimerPage() {
  const { user, loading } = useRequireAuth();
  const [logError, setLogError] = useState<string | null>(null);

  if (loading || !user) return null;

  return (
    <div className="animate-fade-in">
      <div className="mb-8 text-center">
        <h1 className="text-2xl font-semibold">Focus timer</h1>
        <p className="mt-1 text-sm text-text-muted">
          Work in focused sprints, then take a break. Stay disciplined.
        </p>
      </div>
      {logError && (
        <p className="mb-4 rounded-xl border border-danger/30 bg-danger-soft px-3 py-2 text-center text-sm text-danger">
          {logError}
        </p>
      )}
      <FocusTimer
        // Untagged: this page has no subject picker. Logging it anyway is what
        // makes a completed focus session count toward the streak, which is
        // what the rest of the app promises.
        onFocusSessionComplete={(_subjectCode, durationSeconds) => {
          setLogError(null);
          api
            .post("/api/exam-prep/study-sessions", {
              duration_seconds: durationSeconds,
            })
            .catch(() =>
              setLogError(
                "That session couldn't be saved — check your connection. It won't count toward your streak.",
              ),
            );
        }}
      />
    </div>
  );
}
