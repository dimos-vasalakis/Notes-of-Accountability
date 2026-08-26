"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { api } from "@/lib/api";
import type { Note } from "@/lib/types";
import { useRequireAuth } from "@/lib/useRequireAuth";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input, Textarea } from "@/components/ui/Input";

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
    <div className="animate-fade-in">
      <h1 className="mb-6 text-2xl font-semibold">New note</h1>
      <Card className="p-6">
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <Input
            type="text"
            placeholder="Title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
            className="font-display text-lg"
          />
          <Textarea
            placeholder="Write in markdown..."
            value={content}
            onChange={(e) => setContent(e.target.value)}
            rows={14}
            className="font-mono text-sm"
          />
          <Button type="submit" disabled={submitting} className="self-start">
            {submitting ? "Saving..." : "Save note"}
          </Button>
        </form>
      </Card>
    </div>
  );
}
