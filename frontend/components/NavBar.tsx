"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { api } from "@/lib/api";
import { useCurrentUser } from "@/lib/useCurrentUser";

export function NavBar() {
  const { user, loading } = useCurrentUser();
  const router = useRouter();

  if (loading || !user) {
    return null;
  }

  async function handleLogout() {
    await api.post("/api/auth/logout");
    router.push("/login");
    router.refresh();
  }

  return (
    <nav className="flex items-center justify-between border-b border-neutral-200 px-6 py-4 dark:border-neutral-800">
      <div className="flex items-center gap-6">
        <Link href="/notes" className="font-semibold">
          NoA
        </Link>
        <Link href="/notes" className="text-sm text-neutral-600 hover:text-neutral-900 dark:text-neutral-400 dark:hover:text-neutral-100">
          Notes
        </Link>
        <Link href="/tasks" className="text-sm text-neutral-600 hover:text-neutral-900 dark:text-neutral-400 dark:hover:text-neutral-100">
          Tasks
        </Link>
      </div>
      <div className="flex items-center gap-4">
        <span className="text-sm text-neutral-500">{user.email}</span>
        <button
          onClick={handleLogout}
          className="text-sm text-neutral-600 hover:text-neutral-900 dark:text-neutral-400 dark:hover:text-neutral-100"
        >
          Logout
        </button>
      </div>
    </nav>
  );
}
