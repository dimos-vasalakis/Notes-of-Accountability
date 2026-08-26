"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export type TimerMode = "focus" | "short_break" | "long_break";

export interface TimerDurations {
  focus: number;
  short_break: number;
  long_break: number;
}

const DEFAULT_DURATIONS: TimerDurations = {
  focus: 25 * 60,
  short_break: 5 * 60,
  long_break: 15 * 60,
};

const STORAGE_KEY = "noa.focusTimer.durations";
const STATS_KEY = "noa.focusTimer.stats";
const SESSIONS_BEFORE_LONG_BREAK = 4;

interface Stats {
  completedFocusSessions: number;
  lastCompletedDate: string | null;
  streakDays: number;
}

function loadDurations(): TimerDurations {
  if (typeof window === "undefined") return DEFAULT_DURATIONS;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return raw ? { ...DEFAULT_DURATIONS, ...JSON.parse(raw) } : DEFAULT_DURATIONS;
  } catch {
    return DEFAULT_DURATIONS;
  }
}

function loadStats(): Stats {
  if (typeof window === "undefined") {
    return { completedFocusSessions: 0, lastCompletedDate: null, streakDays: 0 };
  }
  try {
    const raw = window.localStorage.getItem(STATS_KEY);
    return raw
      ? JSON.parse(raw)
      : { completedFocusSessions: 0, lastCompletedDate: null, streakDays: 0 };
  } catch {
    return { completedFocusSessions: 0, lastCompletedDate: null, streakDays: 0 };
  }
}

function todayKey(): string {
  return new Date().toISOString().slice(0, 10);
}

function playChime() {
  try {
    const AudioContextCtor =
      window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    const ctx = new AudioContextCtor();
    const notes = [880, 1108.73];
    notes.forEach((freq, i) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = "sine";
      osc.frequency.value = freq;
      const start = ctx.currentTime + i * 0.18;
      gain.gain.setValueAtTime(0, start);
      gain.gain.linearRampToValueAtTime(0.15, start + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.001, start + 0.5);
      osc.connect(gain).connect(ctx.destination);
      osc.start(start);
      osc.stop(start + 0.55);
    });
    setTimeout(() => ctx.close(), 1200);
  } catch {
    // Web Audio unavailable — fail silently.
  }
}

export function useFocusTimer() {
  const [durations, setDurations] = useState<TimerDurations>(DEFAULT_DURATIONS);
  const [mode, setMode] = useState<TimerMode>("focus");
  const [secondsLeft, setSecondsLeft] = useState(DEFAULT_DURATIONS.focus);
  const [running, setRunning] = useState(false);
  const [completedInCycle, setCompletedInCycle] = useState(0);
  const [stats, setStats] = useState<Stats>({
    completedFocusSessions: 0,
    lastCompletedDate: null,
    streakDays: 0,
  });
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    const loadedDurations = loadDurations();
    setDurations(loadedDurations);
    setSecondsLeft(loadedDurations.focus);
    setStats(loadStats());
    if (typeof window !== "undefined" && "Notification" in window && Notification.permission === "default") {
      Notification.requestPermission().catch(() => {});
    }
  }, []);

  useEffect(() => {
    if (!running) {
      if (intervalRef.current) clearInterval(intervalRef.current);
      return;
    }
    intervalRef.current = setInterval(() => {
      setSecondsLeft((prev) => {
        if (prev <= 1) {
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [running]);

  const notify = useCallback((title: string, body: string) => {
    playChime();
    if (typeof window !== "undefined" && "Notification" in window && Notification.permission === "granted") {
      new Notification(title, { body, icon: "/icon.png" });
    }
  }, []);

  const switchMode = useCallback(
    (nextMode: TimerMode, autostart: boolean) => {
      setMode(nextMode);
      setSecondsLeft(durations[nextMode]);
      setRunning(autostart);
    },
    [durations],
  );

  useEffect(() => {
    if (secondsLeft !== 0 || !running) return;

    setRunning(false);

    if (mode === "focus") {
      const nextCount = completedInCycle + 1;
      setCompletedInCycle(nextCount % SESSIONS_BEFORE_LONG_BREAK);

      setStats((prev) => {
        const today = todayKey();
        const wasYesterday =
          prev.lastCompletedDate &&
          new Date(today).getTime() - new Date(prev.lastCompletedDate).getTime() === 86400000;
        const streakDays =
          prev.lastCompletedDate === today
            ? prev.streakDays
            : wasYesterday
              ? prev.streakDays + 1
              : 1;
        const next: Stats = {
          completedFocusSessions: prev.completedFocusSessions + 1,
          lastCompletedDate: today,
          streakDays,
        };
        window.localStorage.setItem(STATS_KEY, JSON.stringify(next));
        return next;
      });

      const isLongBreak = nextCount % SESSIONS_BEFORE_LONG_BREAK === 0;
      notify("Focus session complete", isLongBreak ? "Time for a long break." : "Time for a short break.");
      switchMode(isLongBreak ? "long_break" : "short_break", false);
    } else {
      notify("Break's over", "Ready for another focus session?");
      switchMode("focus", false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [secondsLeft, running]);

  const start = useCallback(() => setRunning(true), []);
  const pause = useCallback(() => setRunning(false), []);
  const reset = useCallback(() => {
    setRunning(false);
    setSecondsLeft(durations[mode]);
  }, [durations, mode]);

  const changeMode = useCallback(
    (nextMode: TimerMode) => switchMode(nextMode, false),
    [switchMode],
  );

  const updateDurations = useCallback(
    (next: TimerDurations) => {
      setDurations(next);
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      setSecondsLeft(next[mode]);
      setRunning(false);
    },
    [mode],
  );

  const total = durations[mode];
  const progress = total > 0 ? (total - secondsLeft) / total : 0;

  return {
    mode,
    secondsLeft,
    total,
    progress,
    running,
    durations,
    stats,
    completedInCycle,
    sessionsBeforeLongBreak: SESSIONS_BEFORE_LONG_BREAK,
    start,
    pause,
    reset,
    changeMode,
    updateDurations,
  };
}
