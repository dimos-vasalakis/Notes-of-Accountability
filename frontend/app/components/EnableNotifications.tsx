"use client";

import { useCurrentUser } from "@/lib/useCurrentUser";
import { usePushNotifications } from "@/lib/usePushNotifications";

export function EnableNotifications() {
  const { user } = useCurrentUser();
  const { supported, permission, loading, subscribe } = usePushNotifications();

  if (!user || !supported || permission === "granted" || permission === "denied") {
    return null;
  }

  return (
    <div className="flex items-center justify-between border-b border-neutral-200 bg-neutral-50 px-6 py-2 text-sm dark:border-neutral-800 dark:bg-neutral-900">
      <span className="text-neutral-600 dark:text-neutral-400">
        Get notified when a task is due.
      </span>
      <button
        onClick={subscribe}
        disabled={loading}
        className="text-neutral-900 underline dark:text-neutral-100"
      >
        {loading ? "Enabling..." : "Enable notifications"}
      </button>
    </div>
  );
}
