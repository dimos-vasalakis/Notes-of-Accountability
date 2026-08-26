import type { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "secondary" | "ghost" | "danger";

const VARIANT_CLASSES: Record<Variant, string> = {
  primary:
    "bg-accent text-accent-contrast hover:bg-accent-hover shadow-sm shadow-accent/20",
  secondary:
    "bg-bg-elevated text-text border border-border hover:border-text-faint",
  ghost: "text-text-muted hover:text-text hover:bg-accent-soft",
  danger: "text-danger border border-danger/30 hover:bg-danger-soft",
};

export function Button({
  variant = "primary",
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium transition-all duration-150 disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)] ${VARIANT_CLASSES[variant]} ${className}`}
      {...props}
    />
  );
}
