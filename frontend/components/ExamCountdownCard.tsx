import type { ExamConfig } from "@/lib/types";
import { Card } from "@/components/ui/Card";

const TRACK_LABELS: Record<string, string> = {
  group_d: "Οικονομίας & Πληροφορικής",
};

export function ExamCountdownCard({ config }: { config: ExamConfig }) {
  const days = config.days_remaining;
  const weeks = Math.floor(Math.abs(days) / 7);
  const passed = days < 0;

  // `exam_date` is a bare YYYY-MM-DD, which Date parses as UTC midnight. Format
  // in UTC too, or viewers west of Greenwich see the exam a day early.
  const examDate = new Date(config.exam_date).toLocaleDateString("el-GR", {
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  });

  return (
    <Card className="relative overflow-hidden p-6">
      <div
        aria-hidden
        className="pointer-events-none absolute -right-12 -top-12 h-40 w-40 rounded-full bg-accent-soft"
      />
      <div className="relative">
        <p className="text-xs font-medium uppercase tracking-wide text-text-faint">
          Πανελλήνιες {config.academic_year}
        </p>
        <div className="mt-3 flex items-baseline gap-2">
          <span className="font-display text-6xl font-semibold tabular-nums text-accent">
            {Math.abs(days)}
          </span>
          <span className="text-lg text-text-muted">
            {passed ? "days ago" : days === 1 ? "day left" : "days left"}
          </span>
        </div>
        <p className="mt-2 text-sm text-text-muted">
          {passed ? "Exams began" : `About ${weeks} ${weeks === 1 ? "week" : "weeks"} —`}{" "}
          {examDate}
        </p>
        <p className="mt-4 text-xs text-text-faint">
          {TRACK_LABELS[config.track] ?? config.track}
        </p>
      </div>
    </Card>
  );
}
