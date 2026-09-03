"use client";

import { useAuth } from "@/lib/AuthContext";

export function useCurrentUser() {
  return useAuth();
}
