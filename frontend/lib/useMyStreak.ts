"use client";

import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import type { Streak } from "@/lib/types";

export function useMyStreak(enabled: boolean = true) {
  const [streak, setStreak] = useState<Streak | null>(null);
  const [loading, setLoading] = useState(enabled);

  useEffect(() => {
    if (!enabled) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    api
      .get<Streak>("/api/pods/me/streak")
      .then((next) => {
        if (!cancelled) setStreak(next);
      })
      .catch(() => {
        if (!cancelled) setStreak(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [enabled]);

  return { streak, loading };
}
