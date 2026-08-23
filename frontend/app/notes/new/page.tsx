"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { api } from "@/lib/api";
import type { Note } from "@/lib/types";
import { useRequireAuth } from "@/lib/useRequireAuth";

export default function NewNotePage() {
  const { user, loading: authLoading } = useRequireAuth();
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [submitting, setSubmitting] = useState(false);

  if (authLoading || !user) return null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    const note = await api.post<Note>("/api/notes", { title, content });
    router.push(`/notes/${note.id}`);
  }

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold">New note</h1>
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <input
          type="text"
          placeholder="Title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
          className="rounded border border-neutral-300 px-3 py-2 dark:border-neutral-700 dark:bg-neutral-900"
        />
        <textarea
          placeholder="Write in markdown..."
          value={content}
          onChange={(e) => setContent(e.target.value)}
          rows={12}
          className="rounded border border-neutral-300 px-3 py-2 font-mono text-sm dark:border-neutral-700 dark:bg-neutral-900"
        />
        <button
          type="submit"
          disabled={submitting}
          className="self-start rounded bg-neutral-900 px-4 py-2 text-sm text-white disabled:opacity-50 dark:bg-white dark:text-neutral-900"
        >
          {submitting ? "Saving..." : "Save note"}
        </button>
      </form>
    </div>
  );
}
