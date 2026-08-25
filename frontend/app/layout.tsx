import type { Metadata } from "next";

import { NavBar } from "@/components/NavBar";

import { EnableNotifications } from "./components/EnableNotifications";
import "./globals.css";

export const metadata: Metadata = {
  title: "Note of Accountability",
  description: "Productivity & accountability system",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-white text-neutral-900 dark:bg-neutral-950 dark:text-neutral-100">
        <NavBar />
        <EnableNotifications />
        <main className="mx-auto max-w-3xl px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
