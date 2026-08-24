"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { useCurrentUser } from "@/lib/useCurrentUser";

export function useRequireAuth() {
  const { user, loading } = useCurrentUser();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.replace("/login");
    }
  }, [loading, user, router]);

  return { user, loading };
}
