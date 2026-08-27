"use client";

import { useCallback, useEffect, useState } from "react";

import { api } from "@/lib/api";
import type { Pod, PodFeed } from "@/lib/types";
import { usePods } from "@/lib/usePods";
import { useRequireAuth } from "@/lib/useRequireAuth";
import { PodFeedCard } from "@/components/PodFeedCard";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";

export default function PodsPage() {
  const { user, loading } = useRequireAuth();
  const { pods, loading: podsLoading, createPod, joinPod, leavePod } = usePods();

  if (loading || !user) return null;

  return (
    <div className="animate-fade-in flex flex-col gap-6">
      <header>
        <h1 className="text-2xl font-semibold">Pods</h1>
        <p className="mt-1 text-sm text-text-muted">
          Small accountability groups. Your pod sees your streak — and gets pinged when
          you go quiet.
        </p>
      </header>

      <div className="grid gap-4 sm:grid-cols-2">
        <CreatePodForm onCreate={createPod} />
        <JoinPodForm onJoin={joinPod} />
      </div>

      {podsLoading ? (
        <p className="text-sm text-text-muted">Loading your pods…</p>
      ) : pods.length === 0 ? (
        <Card className="p-8 text-center">
          <p className="text-3xl" aria-hidden>
            👥
          </p>
          <p className="mt-3 text-sm font-medium">You&apos;re not in a pod yet</p>
          <p className="mt-1 text-sm text-text-muted">
            Create one and share the code with two or three people who are studying for
            the same exams.
          </p>
        </Card>
      ) : (
        pods.map((pod) => (
          <PodPanel
            key={pod.id}
            pod={pod}
            currentUserId={user.id}
            onLeave={() => leavePod(pod.id)}
          />
        ))
      )}
    </div>
  );
}

function PodPanel({
  pod,
  currentUserId,
  onLeave,
}: {
  pod: Pod;
  currentUserId: string;
  onLeave: () => Promise<void>;
}) {
  const [feed, setFeed] = useState<PodFeed | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api
      .get<PodFeed>(`/api/pods/${pod.id}/feed`)
      .then((next) => {
        if (!cancelled) setFeed(next);
      })
      .catch(() => {
        if (!cancelled) setFeed(null);
      });
    return () => {
      cancelled = true;
    };
  }, [pod.id]);

  const copyCode = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(pod.invite_code);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // Clipboard unavailable (insecure context) — the code is visible anyway.
    }
  }, [pod.invite_code]);

  return (
    <Card className="overflow-hidden">
      <div className="flex items-center justify-between gap-3 border-b border-border px-4 py-3">
        <div className="min-w-0">
          <h2 className="truncate font-display text-lg font-semibold">{pod.name}</h2>
          <p className="text-xs text-text-muted">
            {pod.member_count} {pod.member_count === 1 ? "member" : "members"}
          </p>
        </div>
        <button
          onClick={copyCode}
          title="Copy invite code"
          className="shrink-0 rounded-lg border border-border px-2.5 py-1.5 font-mono text-xs tracking-wider text-text-muted transition-colors hover:border-accent hover:text-accent"
        >
          {copied ? "Copied!" : pod.invite_code}
        </button>
      </div>

      {feed === null ? (
        <p className="px-4 py-6 text-sm text-text-muted">Loading feed…</p>
      ) : (
        <ul>
          {feed.members.map((member) => (
            <PodFeedCard
              key={member.user_id}
              member={member}
              isMe={member.user_id === currentUserId}
            />
          ))}
        </ul>
      )}

      <div className="border-t border-border px-4 py-2 text-right">
        <button
          onClick={onLeave}
          className="text-xs text-text-faint transition-colors hover:text-danger"
        >
          Leave pod
        </button>
      </div>
    </Card>
  );
}

function CreatePodForm({ onCreate }: { onCreate: (name: string) => Promise<Pod> }) {
  const [name, setName] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setSubmitting(true);
    try {
      await onCreate(name.trim());
      setName("");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card className="p-4">
      <h2 className="text-sm font-medium">Create a pod</h2>
      <form onSubmit={submit} className="mt-3 flex flex-col gap-2">
        <Input
          placeholder="e.g. Πανελλήνιες 2027"
          value={name}
          onChange={(e) => setName(e.target.value)}
          maxLength={100}
        />
        <Button type="submit" disabled={submitting || !name.trim()}>
          {submitting ? "Creating…" : "Create"}
        </Button>
      </form>
    </Card>
  );
}

function JoinPodForm({ onJoin }: { onJoin: (code: string) => Promise<Pod> }) {
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!code.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      await onJoin(code.trim());
      setCode("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not join that pod.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card className="p-4">
      <h2 className="text-sm font-medium">Join with a code</h2>
      <form onSubmit={submit} className="mt-3 flex flex-col gap-2">
        <Input
          placeholder="INVITE CODE"
          value={code}
          onChange={(e) => setCode(e.target.value.toUpperCase())}
          maxLength={12}
          className="font-mono tracking-wider"
        />
        {error && <p className="text-xs text-danger">{error}</p>}
        <Button type="submit" variant="secondary" disabled={submitting || !code.trim()}>
          {submitting ? "Joining…" : "Join"}
        </Button>
      </form>
    </Card>
  );
}
