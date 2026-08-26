import { NextResponse } from "next/server";

// Served at /sw.js so it can be registered as a service worker with root scope.
// Kept as a TypeScript route handler (rather than public/sw.js) per the
// project's TypeScript-only rule for frontend code.
const serviceWorkerScript = `
self.addEventListener("push", (event) => {
  let payload = { title: "Note of Accountability", body: "You have a task due." };
  if (event.data) {
    try {
      payload = event.data.json();
    } catch {
      payload.body = event.data.text();
    }
  }

  event.waitUntil(
    self.registration.showNotification(payload.title, {
      body: payload.body,
      data: { taskId: payload.task_id },
    })
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil(
    self.clients.matchAll({ type: "window" }).then((clients) => {
      for (const client of clients) {
        if ("focus" in client) return client.focus();
      }
      return self.clients.openWindow("/tasks");
    })
  );
});
`;

export function GET() {
  return new NextResponse(serviceWorkerScript, {
    headers: {
      "Content-Type": "application/javascript",
      "Service-Worker-Allowed": "/",
    },
  });
}
