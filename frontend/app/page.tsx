"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { useCurrentUser } from "@/lib/useCurrentUser";

export default function Home() {
  const { user, loading } = useCurrentUser();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    router.replace(user ? "/notes" : "/login");
  }, [loading, user, router]);

  return null;
}
