"use client";

import { useRef, useState } from "react";

import type { ExamSubject } from "@/lib/types";
import type { TimerDurations, TimerMode } from "@/lib/useFocusTimer";
import { useFocusTimer } from "@/lib/useFocusTimer";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";

const MODE_LABELS: Record<TimerMode, string> = {
  focus: "Focus",
  short_break: "Short break",
  long_break: "Long break",
};

const MODE_ACCENTS: Record<TimerMode, string> = {
  focus: "var(--accent)",
  short_break: "var(--success)",
  long_break: "var(--warning)",
};

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
}

const RADIUS = 90;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

export interface FocusTimerProps {
  /** When provided, the timer shows a subject picker and tags each session. */
  subjects?: ExamSubject[];
  onFocusSessionComplete?: (subjectCode: string | null, durationSeconds: number) => void;
}

export function FocusTimer({ subjects, onFocusSessionComplete }: FocusTimerProps = {}) {
  const [showSettings, setShowSettings] = useState(false);
  const [subjectCode, setSubjectCode] = useState<string>("");
  // Read through a ref so the completion callback always sees the subject
  // selected when the session ended, not the one bound on first render.
  const subjectRef = useRef(subjectCode);
  subjectRef.current = subjectCode;

  const timer = useFocusTimer({
    onFocusSessionComplete: onFocusSessionComplete
      ? (durationSeconds) =>
          onFocusSessionComplete(subjectRef.current || null, durationSeconds)
      : undefined,
  });

  const color = MODE_ACCENTS[timer.mode];
  const offset = CIRCUMFERENCE * (1 - timer.progress);

  return (
    <div className="flex flex-col items-center gap-6">
      {subjects && subjects.length > 0 && (
        <label className="flex w-full flex-col gap-1.5">
          <span className="text-xs font-medium uppercase tracking-wide text-text-faint">
            Studying
          </span>
          <select
            value={subjectCode}
            onChange={(e) => setSubjectCode(e.target.value)}
            className="w-full rounded-xl border border-border bg-bg-elevated px-3.5 py-2.5 text-sm text-text transition-colors focus:border-accent focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
          >
            <option value="">No subject</option>
            {subjects.map((subject) => (
              <option key={subject.code} value={subject.code}>
                {subject.name_el}
              </option>
            ))}
          </select>
        </label>
      )}

      <div className="flex items-center gap-2 rounded-full border border-border bg-bg-elevated p-1">
        {(Object.keys(MODE_LABELS) as TimerMode[]).map((m) => (
          <button
            key={m}
            onClick={() => timer.changeMode(m)}
            className={`rounded-full px-3.5 py-1.5 text-sm font-medium transition-colors ${
              timer.mode === m ? "bg-accent-soft text-accent" : "text-text-muted hover:text-text"
            }`}
          >
            {MODE_LABELS[m]}
          </button>
        ))}
      </div>

      <div
        className={`relative flex h-64 w-64 items-center justify-center rounded-full ${timer.running ? "animate-pulse-ring" : ""}`}
      >
        <svg viewBox="0 0 200 200" className="h-full w-full -rotate-90">
          <circle
            cx="100"
            cy="100"
            r={RADIUS}
            fill="none"
            stroke="var(--border)"
            strokeWidth="10"
          />
          <circle
            cx="100"
            cy="100"
            r={RADIUS}
            fill="none"
            stroke={color}
            strokeWidth="10"
            strokeLinecap="round"
            strokeDasharray={CIRCUMFERENCE}
            strokeDashoffset={offset}
            style={{ transition: "stroke-dashoffset 1s linear" }}
          />
        </svg>
        <div className="absolute flex flex-col items-center">
          <span className="font-display text-5xl font-semibold tabular-nums">
            {formatTime(timer.secondsLeft)}
          </span>
          <span className="mt-1 text-sm text-text-muted">{MODE_LABELS[timer.mode]}</span>
        </div>
      </div>

      <div className="flex items-center gap-3">
        {!timer.running ? (
          <Button onClick={timer.start} className="w-32">
            {timer.secondsLeft === timer.total ? "Start" : "Resume"}
          </Button>
        ) : (
          <Button onClick={timer.pause} variant="secondary" className="w-32">
            Pause
          </Button>
        )}
        <Button onClick={timer.reset} variant="ghost">
          Reset
        </Button>
      </div>

      <div className="flex items-center gap-1.5">
        {Array.from({ length: timer.sessionsBeforeLongBreak }).map((_, i) => (
          <span
            key={i}
            className={`h-1.5 w-6 rounded-full ${i < timer.completedInCycle ? "bg-accent" : "bg-border"}`}
          />
        ))}
      </div>

      <Card className="grid w-full grid-cols-2 gap-4 p-4 text-center">
        <div>
          <p className="font-display text-2xl font-semibold">{timer.stats.completedFocusSessions}</p>
          <p className="text-xs text-text-muted">Sessions completed</p>
        </div>
        <div>
          <p className="font-display text-2xl font-semibold">{timer.stats.streakDays}</p>
          <p className="text-xs text-text-muted">Day streak</p>
        </div>
      </Card>

      <button
        onClick={() => setShowSettings((s) => !s)}
        className="text-sm text-text-faint underline decoration-dotted underline-offset-4 hover:text-text-muted"
      >
        {showSettings ? "Hide durations" : "Customize durations"}
      </button>

      {showSettings && <DurationSettings durations={timer.durations} onChange={timer.updateDurations} />}
    </div>
  );
}

function DurationSettings({
  durations,
  onChange,
}: {
  durations: TimerDurations;
  onChange: (next: TimerDurations) => void;
}) {
  const fields: { key: TimerMode; label: string }[] = [
    { key: "focus", label: "Focus (min)" },
    { key: "short_break", label: "Short break (min)" },
    { key: "long_break", label: "Long break (min)" },
  ];

  return (
    <Card className="grid w-full grid-cols-3 gap-3 p-4">
      {fields.map((f) => (
        <label key={f.key} className="flex flex-col gap-1 text-xs text-text-muted">
          {f.label}
          <input
            type="number"
            min={1}
            max={180}
            value={Math.round(durations[f.key] / 60)}
            onChange={(e) =>
              onChange({ ...durations, [f.key]: Math.max(1, Number(e.target.value)) * 60 })
            }
            className="rounded-lg border border-border bg-bg px-2 py-1.5 text-sm text-text focus:border-accent focus:outline-none"
          />
        </label>
      ))}
    </Card>
  );
}
