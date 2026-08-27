"use client";

import { useCallback, useEffect, useState } from "react";

import { api, ApiError } from "@/lib/api";
import type { Pod, PodFeed } from "@/lib/types";

export function usePods(enabled: boolean = true) {
  const [pods, setPods] = useState<Pod[]>([]);
  const [loading, setLoading] = useState(enabled);

  const refresh = useCallback(async () => {
    setPods(await api.get<Pod[]>("/api/pods"));
  }, []);

  useEffect(() => {
    if (!enabled) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    api
      .get<Pod[]>("/api/pods")
      .then((next) => {
        if (!cancelled) setPods(next);
      })
      .catch(() => {
        if (!cancelled) setPods([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [enabled]);

  const createPod = useCallback(
    async (name: string) => {
      const pod = await api.post<Pod>("/api/pods", { name });
      await refresh();
      return pod;
    },
    [refresh],
  );

  const joinPod = useCallback(
    async (inviteCode: string) => {
      try {
        const pod = await api.post<Pod>("/api/pods/join", { invite_code: inviteCode });
        await refresh();
        return pod;
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) {
          throw new Error("No pod found with that code.");
        }
        if (err instanceof ApiError && err.status === 409) {
          throw new Error("You're already in this pod.");
        }
        throw new Error("Could not join that pod.");
      }
    },
    [refresh],
  );

  const getFeed = useCallback(
    (podId: string) => api.get<PodFeed>(`/api/pods/${podId}/feed`),
    [],
  );

  const leavePod = useCallback(
    async (podId: string) => {
      await api.del(`/api/pods/${podId}/members/me`);
      await refresh();
    },
    [refresh],
  );

  return { pods, loading, createPod, joinPod, getFeed, leavePod, refresh };
}
