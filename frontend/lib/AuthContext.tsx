"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";

import { api, ApiError } from "@/lib/api";
import type { UserPublic } from "@/lib/types";

interface AuthContextValue {
  user: UserPublic | null;
  loading: boolean;
  refresh: () => Promise<void>;
  setUser: (user: UserPublic) => void;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUserState] = useState<UserPublic | null>(null);
  const [loading, setLoading] = useState(true);
  const requestIdRef = useRef(0);

  const refresh = useCallback(async () => {
    const requestId = ++requestIdRef.current;
    try {
      const current = await api.get<UserPublic>("/api/auth/me");
      if (requestIdRef.current === requestId) setUserState(current);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        if (requestIdRef.current === requestId) setUserState(null);
      } else {
        throw err;
      }
    } finally {
      if (requestIdRef.current === requestId) setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  // Marks any in-flight refresh() as stale so it can't clobber this update
  // with an older response (e.g. a mount-time /me call resolving after login).
  const setUser = useCallback((next: UserPublic) => {
    requestIdRef.current += 1;
    setUserState(next);
    setLoading(false);
  }, []);

  const logout = useCallback(async () => {
    await api.post("/api/auth/logout");
    requestIdRef.current += 1;
    setUserState(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, refresh, setUser, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
