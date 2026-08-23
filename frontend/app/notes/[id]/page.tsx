"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import type { Note } from "@/lib/types";
import { useRequireAuth } from "@/lib/useRequireAuth";

export default function NoteDetailPage() {
  const { user, loading: authLoading } = useRequireAuth();
  const router = useRouter();
  const params = useParams<{ id: string }>();

  const [note, setNote] = useState<Note | null>(null);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!user) return;
    api.get<Note>(`/api/notes/${params.id}`).then((n) => {
      setNote(n);
      setTitle(n.title);
      setContent(n.content);
      setLoading(false);
    });
  }, [user, params.id]);

  if (authLoading || !user || loading || !note) return null;

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    const updated = await api.patch<Note>(`/api/notes/${params.id}`, { title, content });
    setNote(updated);
    setSaving(false);
  }

  async function handleDelete() {
    await api.del(`/api/notes/${params.id}`);
    router.push("/notes");
  }

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold">Edit note</h1>
      <form onSubmit={handleSave} className="flex flex-col gap-4">
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
          className="rounded border border-neutral-300 px-3 py-2 dark:border-neutral-700 dark:bg-neutral-900"
        />
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          rows={12}
          className="rounded border border-neutral-300 px-3 py-2 font-mono text-sm dark:border-neutral-700 dark:bg-neutral-900"
        />
        <div className="flex gap-2">
          <button
            type="submit"
            disabled={saving}
            className="rounded bg-neutral-900 px-4 py-2 text-sm text-white disabled:opacity-50 dark:bg-white dark:text-neutral-900"
          >
            {saving ? "Saving..." : "Save"}
          </button>
          <button
            type="button"
            onClick={handleDelete}
            className="rounded border border-red-300 px-4 py-2 text-sm text-red-600 hover:bg-red-50 dark:border-red-900 dark:hover:bg-red-950"
          >
            Delete
          </button>
        </div>
      </form>
    </div>
  );
}
