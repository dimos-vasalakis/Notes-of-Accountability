"use client";

import { useEffect, useState } from "react";

import { api, ApiError } from "@/lib/api";
import type { UserPublic } from "@/lib/types";

export function useCurrentUser() {
  const [user, setUser] = useState<UserPublic | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    api
      .get<UserPublic>("/api/auth/me")
      .then((current) => {
        if (!cancelled) setUser(current);
      })
      .catch((err) => {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 401) {
          setUser(null);
        } else {
          throw err;
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  async function logout() {
    await api.post("/api/auth/logout");
    setUser(null);
  }

  return { user, loading, logout };
}
