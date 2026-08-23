"use client";

import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import type { Task, TaskStatus } from "@/lib/types";
import { useRequireAuth } from "@/lib/useRequireAuth";

const STATUS_LABELS: Record<TaskStatus, string> = {
  todo: "To do",
  in_progress: "In progress",
  done: "Done",
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
    await api.post<Task>("/api/tasks", { title: newTitle });
    setNewTitle("");
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

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold">Tasks</h1>

      <form onSubmit={handleCreate} className="mb-6 flex gap-2">
        <input
          type="text"
          placeholder="New task..."
          value={newTitle}
          onChange={(e) => setNewTitle(e.target.value)}
          className="flex-1 rounded border border-neutral-300 px-3 py-2 dark:border-neutral-700 dark:bg-neutral-900"
        />
        <button
          type="submit"
          className="rounded bg-neutral-900 px-4 py-2 text-sm text-white dark:bg-white dark:text-neutral-900"
        >
          Add
        </button>
      </form>

      {loading && <p className="text-neutral-500">Loading...</p>}
      {!loading && tasks.length === 0 && (
        <p className="text-neutral-500">No tasks yet.</p>
      )}

      <ul className="flex flex-col gap-2">
        {tasks.map((task) => (
          <li
            key={task.id}
            className="flex items-center justify-between rounded border border-neutral-200 px-4 py-3 dark:border-neutral-800"
          >
            <div>
              <p className={task.status === "done" ? "line-through text-neutral-400" : ""}>
                {task.title}
              </p>
              <button
                onClick={() => handleToggleStatus(task)}
                className="mt-1 text-xs text-neutral-500 underline"
              >
                {STATUS_LABELS[task.status]} — mark next
              </button>
            </div>
            <button
              onClick={() => handleDelete(task)}
              className="text-sm text-red-600 hover:underline"
            >
              Delete
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
