"use client";

import { useEffect, useState } from "react";

type Theme = "bright" | "default";

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>("default");

  useEffect(() => {
    setTheme(document.documentElement.dataset.theme === "bright" ? "bright" : "default");
  }, []);

  function toggle() {
    const next: Theme = theme === "bright" ? "default" : "bright";
    setTheme(next);
    if (next === "bright") {
      document.documentElement.dataset.theme = "bright";
    } else {
      delete document.documentElement.dataset.theme;
    }
    try {
      localStorage.setItem("noa-theme", next);
    } catch {
      // Storage unavailable (private mode); the theme still applies for this session.
    }
  }

  const bright = theme === "bright";
  return (
    <button
      type="button"
      onClick={toggle}
      aria-pressed={bright}
      aria-label={bright ? "Switch to default theme" : "Switch to bright theme"}
      title={bright ? "Default theme" : "Bright theme"}
      className="rounded-lg px-2.5 py-1.5 text-sm text-text-muted transition-colors hover:bg-accent-soft hover:text-text"
    >
      <span aria-hidden>{bright ? "🌙" : "☀️"}</span>
    </button>
  );
}
