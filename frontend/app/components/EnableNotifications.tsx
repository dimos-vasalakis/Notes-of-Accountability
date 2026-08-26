"use client";

import { useCurrentUser } from "@/lib/useCurrentUser";
import { usePushNotifications } from "@/lib/usePushNotifications";

export function EnableNotifications() {
  const { user } = useCurrentUser();
  const { supported, permission, loading, error, subscribe } = usePushNotifications();

  if (!user || !supported || permission === "granted" || permission === "denied") {
    return null;
  }

  return (
    <div className="flex items-center justify-between gap-4 border-b border-border bg-accent-soft px-4 py-2 text-sm sm:px-6">
      <span className="text-accent">{error ?? "Get notified when a task is due."}</span>
      <button
        onClick={subscribe}
        disabled={loading}
        className="whitespace-nowrap font-medium text-accent underline decoration-dotted underline-offset-4 hover:opacity-80 disabled:opacity-50"
      >
        {loading ? "Enabling..." : "Enable notifications"}
      </button>
    </div>
  );
}
