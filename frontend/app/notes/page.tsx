"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import type { Note } from "@/lib/types";
import { useRequireAuth } from "@/lib/useRequireAuth";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";

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
    <div className="animate-fade-in">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Notes</h1>
          <p className="mt-1 text-sm text-text-muted">Capture what you're learning.</p>
        </div>
        <Link href="/notes/new">
          <Button>+ New note</Button>
        </Link>
      </div>

      {loading && <p className="text-text-muted">Loading...</p>}

      {!loading && notes.length === 0 && (
        <Card className="flex flex-col items-center gap-2 px-6 py-14 text-center">
          <span className="text-3xl">📝</span>
          <p className="font-medium">No notes yet</p>
          <p className="text-sm text-text-muted">Start writing down what you're studying.</p>
          <Link href="/notes/new" className="mt-2">
            <Button variant="secondary">Create your first note</Button>
          </Link>
        </Card>
      )}

      <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {notes.map((note) => (
          <li key={note.id}>
            <Link href={`/notes/${note.id}`}>
              <Card className="flex h-full flex-col gap-2 p-4 transition-transform hover:-translate-y-0.5 hover:border-accent/40">
                <span className="font-medium">{note.title || "Untitled"}</span>
                <span className="line-clamp-3 text-sm text-text-muted">
                  {note.content || "No content yet."}
                </span>
                <span className="mt-auto pt-2 text-xs text-text-faint">
                  Updated {new Date(note.updated_at).toLocaleDateString()}
                </span>
              </Card>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
