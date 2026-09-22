import Link from "next/link";

import { StreakBadge } from "@/components/StreakBadge";

const FEATURES = [
  {
    icon: "✎",
    title: "Markdown notes",
    body: "Capture lectures and ideas in clean markdown, organised and searchable.",
  },
  {
    icon: "✓",
    title: "Tasks that stick",
    body: "Plan your day, tick things off, and see what actually got done.",
  },
  {
    icon: "◷",
    title: "Focus timer",
    body: "Deep-work sessions that count toward your daily streak.",
  },
  {
    icon: "👥",
    title: "Accountability pods",
    body: "Study alongside friends who can see your streak and cheer you on.",
  },
  {
    icon: "🎓",
    title: "Exam prep",
    body: "Countdowns and subject allocation so revision time goes where it matters.",
  },
  {
    icon: "🔔",
    title: "Smart reminders",
    body: "Push notifications nudge you before your streak runs out.",
  },
];

export function Landing() {
  return (
    <div className="animate-fade-in flex flex-col gap-16">
      <header className="flex items-center justify-between">
        <span className="flex items-center gap-2 font-display text-lg font-semibold">
          <img src="/logo-mark.png" alt="" className="h-7 w-7 rounded-lg" />
          Notes of Accountability
        </span>
        <Link
          href="/login"
          className="rounded-lg px-3 py-1.5 text-sm font-medium text-text-muted transition-colors hover:bg-accent-soft hover:text-text"
        >
          Log in
        </Link>
      </header>

      <section className="flex flex-col items-center text-center">
        <h1 className="max-w-2xl bg-gradient-to-r from-accent to-pink-500 bg-clip-text font-display text-4xl font-bold text-transparent sm:text-5xl">
          Show up every day. Keep the streak alive.
        </h1>
        <p className="mt-4 max-w-xl text-base text-text-muted sm:text-lg">
          Note of Accountability brings your notes, tasks, focus sessions and study
          pods together, with an accountability system that keeps you honest.
        </p>
        <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
          <Link
            href="/signup"
            className="rounded-xl bg-accent px-6 py-3 text-sm font-semibold text-accent-contrast shadow-md shadow-accent/30 transition-colors hover:bg-accent-hover"
          >
            Get started
          </Link>
          <Link
            href="/login"
            className="rounded-xl border border-border bg-bg-elevated px-6 py-3 text-sm font-medium transition-colors hover:border-accent"
          >
            I have an account
          </Link>
        </div>
        <div className="mt-10" aria-label="Example streak">
          <StreakBadge days={14} activeToday size="lg" />
        </div>
      </section>

      <section>
        <h2 className="mb-6 text-center text-2xl font-semibold">Everything in one place</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f) => (
            <div
              key={f.title}
              className="rounded-2xl border border-border bg-bg-elevated p-5 shadow-sm transition-shadow hover:shadow-md"
            >
              <span
                className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent-soft text-lg text-accent"
                aria-hidden
              >
                {f.icon}
              </span>
              <h3 className="mt-3 font-semibold">{f.title}</h3>
              <p className="mt-1 text-sm text-text-muted">{f.body}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-3xl bg-accent-soft px-6 py-10 text-center">
        <h2 className="text-2xl font-semibold">Ready to start your streak?</h2>
        <Link
          href="/signup"
          className="mt-5 inline-block rounded-xl bg-accent px-6 py-3 text-sm font-semibold text-accent-contrast shadow-md shadow-accent/30 transition-colors hover:bg-accent-hover"
        >
          Get started
        </Link>
      </section>
    </div>
  );
}
