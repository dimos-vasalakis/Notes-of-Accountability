"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import type { Note } from "@/lib/types";
import { useRequireAuth } from "@/lib/useRequireAuth";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input, Textarea } from "@/components/ui/Input";

export default function NoteDetailPage() {
  const { user, loading: authLoading } = useRequireAuth();
  const router = useRouter();
  const params = useParams<{ id: string }>();

  const [note, setNote] = useState<Note | null>(null);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState<Date | null>(null);

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
    setSavedAt(new Date());
  }

  async function handleDelete() {
    await api.del(`/api/notes/${params.id}`);
    router.push("/notes");
  }

  return (
    <div className="animate-fade-in">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Edit note</h1>
        {savedAt && <span className="text-xs text-text-faint">Saved {savedAt.toLocaleTimeString()}</span>}
      </div>
      <Card className="p-6">
        <form onSubmit={handleSave} className="flex flex-col gap-4">
          <Input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
            className="font-display text-lg"
          />
          <Textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            rows={14}
            className="font-mono text-sm"
          />
          <div className="flex gap-2">
            <Button type="submit" disabled={saving}>
              {saving ? "Saving..." : "Save"}
            </Button>
            <Button type="button" variant="danger" onClick={handleDelete}>
              Delete
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
