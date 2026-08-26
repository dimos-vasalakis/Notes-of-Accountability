"use client";

import { useEffect } from "react";

export function RegisterServiceWorker() {
  useEffect(() => {
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("/sw.js").catch(() => {
        // Installability/offline support is best-effort; push subscription flow
        // will surface a clearer error if registration is actually required.
      });
    }
  }, []);

  return null;
}
