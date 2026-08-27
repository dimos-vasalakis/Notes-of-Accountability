"use client";

import { useCallback, useEffect, useState } from "react";

import { api } from "@/lib/api";
import type {
  ExamConfig,
  ExamSubject,
  StudySession,
  SubjectAllocation,
} from "@/lib/types";

export type AllocationWindow = "week" | "month";

export function useExamPrep(enabled: boolean, window: AllocationWindow = "week") {
  const [config, setConfig] = useState<ExamConfig | null>(null);
  const [subjects, setSubjects] = useState<ExamSubject[]>([]);
  const [allocation, setAllocation] = useState<SubjectAllocation[]>([]);
  const [loading, setLoading] = useState(enabled);
  const [error, setError] = useState<string | null>(null);

  const loadAllocation = useCallback(async () => {
    setAllocation(
      await api.get<SubjectAllocation[]>(`/api/exam-prep/allocation?window=${window}`),
    );
  }, [window]);

  useEffect(() => {
    if (!enabled) {
      setLoading(false);
      return;
    }
    let cancelled = false;

    setLoading(true);
    Promise.all([
      api.get<ExamConfig>("/api/exam-prep/config"),
      api.get<ExamSubject[]>("/api/exam-prep/subjects"),
      api.get<SubjectAllocation[]>(`/api/exam-prep/allocation?window=${window}`),
    ])
      .then(([nextConfig, nextSubjects, nextAllocation]) => {
        if (cancelled) return;
        setConfig(nextConfig);
        setSubjects(nextSubjects);
        setAllocation(nextAllocation);
        setError(null);
      })
      .catch(() => {
        if (!cancelled) setError("Could not load your exam plan.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [enabled, window]);

  const logStudySession = useCallback(
    async (subjectCode: string | null, durationSeconds: number) => {
      await api.post<StudySession>("/api/exam-prep/study-sessions", {
        subject_code: subjectCode,
        duration_seconds: durationSeconds,
      });
      // Refresh so the allocation bars move as soon as a session lands.
      await loadAllocation();
    },
    [loadAllocation],
  );

  return { config, subjects, allocation, loading, error, logStudySession };
}
