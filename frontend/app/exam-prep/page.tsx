"use client";

import { useState } from "react";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/AuthContext";
import type { UserPublic } from "@/lib/types";
import { useExamPrep, type AllocationWindow } from "@/lib/useExamPrep";
import { useRequireAuth } from "@/lib/useRequireAuth";
import { ExamCountdownCard } from "@/components/ExamCountdownCard";
import { FocusTimer } from "@/components/FocusTimer";
import { SubjectAllocationBar } from "@/components/SubjectAllocationBar";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";

export default function ExamPrepPage() {
  const { user, loading } = useRequireAuth();
  const [optedIn, setOptedIn] = useState(false);
  const [allocationWindow, setAllocationWindow] = useState<AllocationWindow>("week");
  const [logError, setLogError] = useState<string | null>(null);

  const isStudent = (user?.is_student ?? false) || optedIn;
  const { config, subjects, allocation, loading: dataLoading, error, logStudySession } =
    useExamPrep(Boolean(user) && isStudent, allocationWindow);

  if (loading || !user) return null;

  if (!isStudent) {
    return <StudentModeUpsell onEnabled={() => setOptedIn(true)} />;
  }

  const totalSeconds = allocation.reduce((sum, row) => sum + row.actual_seconds, 0);

  return (
    <div className="animate-fade-in flex flex-col gap-6">
      <header>
        <h1 className="text-2xl font-semibold">Exam prep</h1>
        <p className="mt-1 text-sm text-text-muted">
          Your countdown, and whether your hours match what each subject is worth.
        </p>
      </header>

      {error && <p className="text-sm text-danger">{error}</p>}
      {dataLoading && <p className="text-sm text-text-muted">Loading…</p>}

      {config && <ExamCountdownCard config={config} />}

      <Card className="p-5">
        <div className="mb-1 flex items-center justify-between gap-3">
          <div>
            <h2 className="font-display text-lg font-semibold">Time by subject</h2>
            <p className="text-xs text-text-muted">
              The marker shows each subject&apos;s target share, set by its coefficient.
            </p>
          </div>
          <div className="flex shrink-0 rounded-full border border-border p-0.5">
            {(["week", "month"] as AllocationWindow[]).map((w) => (
              <button
                key={w}
                onClick={() => setAllocationWindow(w)}
                className={`rounded-full px-3 py-1 text-xs font-medium capitalize transition-colors ${
                  allocationWindow === w ? "bg-accent-soft text-accent" : "text-text-muted"
                }`}
              >
                {w}
              </button>
            ))}
          </div>
        </div>

        {totalSeconds === 0 ? (
          <p className="py-6 text-center text-sm text-text-muted">
            No study time logged this {allocationWindow} yet. Run a focus session below and tag it
            with a subject.
          </p>
        ) : (
          <div className="divide-y divide-border">
            {allocation.map((row) => (
              <SubjectAllocationBar key={row.subject_code} row={row} />
            ))}
          </div>
        )}
      </Card>

      <Card className="p-6">
        <h2 className="mb-6 text-center font-display text-lg font-semibold">
          Log study time
        </h2>
        {logError && (
          <p className="mb-4 rounded-xl border border-danger/30 bg-danger-soft px-3 py-2 text-center text-sm text-danger">
            {logError}
          </p>
        )}
        <FocusTimer
          subjects={subjects}
          // The timer fires this and moves on, so a failed POST would
          // otherwise lose the session silently.
          onFocusSessionComplete={(subjectCode, durationSeconds) => {
            setLogError(null);
            logStudySession(subjectCode, durationSeconds).catch(() =>
              setLogError(
                "That session couldn't be saved — check your connection. It won't count toward your streak.",
              ),
            );
          }}
        />
      </Card>
    </div>
  );
}

function StudentModeUpsell({ onEnabled }: { onEnabled: () => void }) {
  const { setUser } = useAuth();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function enable() {
    setSubmitting(true);
    setError(null);
    try {
      const updated = await api.patch<UserPublic>("/api/auth/me", {
        is_student: true,
        exam_track: "group_d",
      });
      setUser(updated);
      onEnabled();
    } catch {
      setError("Could not enable student mode. Try again.");
      setSubmitting(false);
    }
  }

  return (
    <div className="animate-fade-in mx-auto max-w-md pt-8 text-center">
      <p className="text-4xl" aria-hidden>
        🎓
      </p>
      <h1 className="mt-4 text-2xl font-semibold">Preparing for the Πανελλήνιες?</h1>
      <p className="mt-2 text-sm text-text-muted">
        Turn on student mode to get an exam countdown and see whether your study hours
        match what each subject is actually worth.
      </p>
      <Card className="mt-6 p-6">
        <p className="text-sm text-text-muted">
          Built for the <strong className="text-text">Ομάδα Οικονομίας &amp; Πληροφορικής</strong>{" "}
          track — Νεοελληνική, Μαθηματικά, ΑΕΠΠ and ΑΟΘ.
        </p>
        {error && <p className="mt-4 text-sm text-danger">{error}</p>}
        <Button onClick={enable} disabled={submitting} className="mt-5 w-full">
          {submitting ? "Enabling…" : "Enable student mode"}
        </Button>
      </Card>
    </div>
  );
}
