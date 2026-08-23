"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import type { Note } from "@/lib/types";
import { useRequireAuth } from "@/lib/useRequireAuth";

export default function NotesPage() {
  const { user, loading: authLoading } = useRequireAuth();
  const [notes, setNotes] = useState<Note[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) return;
    api
      .get<Note[]>("/api/notes")
      .then(setNotes)
      .finally(() => setLoading(false));
  }, [user]);

  if (authLoading || !user) return null;

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Notes</h1>
        <Link
          href="/notes/new"
          className="rounded bg-neutral-900 px-4 py-2 text-sm text-white dark:bg-white dark:text-neutral-900"
        >
          New note
        </Link>
      </div>

      {loading && <p className="text-neutral-500">Loading...</p>}

      {!loading && notes.length === 0 && (
        <p className="text-neutral-500">No notes yet.</p>
      )}

      <ul className="flex flex-col gap-2">
        {notes.map((note) => (
          <li key={note.id}>
            <Link
              href={`/notes/${note.id}`}
              className="block rounded border border-neutral-200 px-4 py-3 hover:bg-neutral-50 dark:border-neutral-800 dark:hover:bg-neutral-900"
            >
              <span className="font-medium">{note.title || "Untitled"}</span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
