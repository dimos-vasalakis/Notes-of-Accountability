import type { HTMLAttributes } from "react";

export function Card({ className = "", ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={`rounded-2xl border border-border bg-bg-elevated shadow-sm shadow-black/[0.02] ${className}`}
      {...props}
    />
  );
}
