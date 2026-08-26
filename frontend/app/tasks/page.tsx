"use client";

import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import type { Task, TaskStatus } from "@/lib/types";
import { useRequireAuth } from "@/lib/useRequireAuth";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";

const STATUS_LABELS: Record<TaskStatus, string> = {
  todo: "To do",
  in_progress: "In progress",
  done: "Done",
};

const STATUS_BADGE: Record<TaskStatus, string> = {
  todo: "bg-accent-soft text-accent",
  in_progress: "bg-warning-soft text-warning",
  done: "bg-success-soft text-success",
};

const STATUS_ORDER: TaskStatus[] = ["todo", "in_progress", "done"];

function nextStatus(status: TaskStatus): TaskStatus {
  const idx = STATUS_ORDER.indexOf(status);
  return STATUS_ORDER[(idx + 1) % STATUS_ORDER.length];
}

export default function TasksPage() {
  const { user, loading: authLoading } = useRequireAuth();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [newTitle, setNewTitle] = useState("");
  const [newDueDate, setNewDueDate] = useState("");

  async function refresh() {
    const data = await api.get<Task[]>("/api/tasks");
    setTasks(data);
    setLoading(false);
  }

  useEffect(() => {
    if (!user) return;
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  if (authLoading || !user) return null;

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!newTitle.trim()) return;
    await api.post<Task>("/api/tasks", {
      title: newTitle,
      due_date: newDueDate ? new Date(newDueDate).toISOString() : null,
    });
    setNewTitle("");
    setNewDueDate("");
    refresh();
  }

  async function handleToggleStatus(task: Task) {
    await api.patch<Task>(`/api/tasks/${task.id}`, { status: nextStatus(task.status) });
    refresh();
  }

  async function handleDelete(task: Task) {
    await api.del(`/api/tasks/${task.id}`);
    refresh();
  }

  const doneCount = tasks.filter((t) => t.status === "done").length;

  return (
    <div className="animate-fade-in">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Tasks</h1>
          <p className="mt-1 text-sm text-text-muted">
            {tasks.length > 0 ? `${doneCount} of ${tasks.length} done` : "Plan what needs to get done."}
          </p>
        </div>
      </div>

      <Card className="mb-6 p-4">
        <form onSubmit={handleCreate} className="flex flex-col gap-2 sm:flex-row">
          <Input
            type="text"
            placeholder="New task..."
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            className="flex-1"
          />
          <Input
            type="datetime-local"
            value={newDueDate}
            onChange={(e) => setNewDueDate(e.target.value)}
            className="sm:w-56"
          />
          <Button type="submit">Add</Button>
        </form>
      </Card>

      {loading && <p className="text-text-muted">Loading...</p>}
      {!loading && tasks.length === 0 && (
        <Card className="flex flex-col items-center gap-2 px-6 py-14 text-center">
          <span className="text-3xl">✅</span>
          <p className="font-medium">No tasks yet</p>
          <p className="text-sm text-text-muted">Add something above to get started.</p>
        </Card>
      )}

      <ul className="flex flex-col gap-2">
        {tasks.map((task) => (
          <li key={task.id}>
            <Card className="flex items-center justify-between gap-4 p-4">
              <div>
                <p className={task.status === "done" ? "text-text-faint line-through" : "font-medium"}>
                  {task.title}
                </p>
                <div className="mt-1.5 flex items-center gap-2">
                  <button
                    onClick={() => handleToggleStatus(task)}
                    className={`rounded-full px-2.5 py-0.5 text-xs font-medium transition-opacity hover:opacity-80 ${STATUS_BADGE[task.status]}`}
                  >
                    {STATUS_LABELS[task.status]}
                  </button>
                  {task.due_date && (
                    <span className="text-xs text-text-faint">
                      Due {new Date(task.due_date).toLocaleString()}
                    </span>
                  )}
                </div>
              </div>
              <button
                onClick={() => handleDelete(task)}
                className="text-sm text-text-faint hover:text-danger"
              >
                Delete
              </button>
            </Card>
          </li>
        ))}
      </ul>
    </div>
  );
}
