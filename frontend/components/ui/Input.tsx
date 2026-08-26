import type { InputHTMLAttributes, TextareaHTMLAttributes } from "react";

const FIELD_CLASSES =
  "w-full rounded-xl border border-border bg-bg-elevated px-3.5 py-2.5 text-sm text-text placeholder:text-text-faint transition-colors focus:border-accent focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]";

export function Input({ className = "", ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={`${FIELD_CLASSES} ${className}`} {...props} />;
}

export function Textarea({ className = "", ...props }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea className={`${FIELD_CLASSES} ${className}`} {...props} />;
}
