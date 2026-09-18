import type { Metadata, Viewport } from "next";
import { Inter, Space_Grotesk } from "next/font/google";

import { NavBar } from "@/components/NavBar";
import { AuthProvider } from "@/lib/AuthContext";

import { EnableNotifications } from "./components/EnableNotifications";
import { RegisterServiceWorker } from "./components/RegisterServiceWorker";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-space-grotesk",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Note of Accountability",
  description: "Notes, tasks and focus timers for staying disciplined.",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "NoA",
  },
};

export const viewport: Viewport = {
  themeColor: "#6d5ef0",
};

// Runs before first paint so a saved bright theme doesn't flash the default one.
const THEME_INIT_SCRIPT = `try{if(localStorage.getItem("noa-theme")==="bright")document.documentElement.dataset.theme="bright"}catch(e){}`;

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${spaceGrotesk.variable}`}
      suppressHydrationWarning
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
      </head>
      <body className="min-h-screen bg-bg text-text">
        <AuthProvider>
          <RegisterServiceWorker />
          <NavBar />
          <EnableNotifications />
          <main className="mx-auto max-w-4xl px-4 py-8 sm:px-6 sm:py-10">{children}</main>
        </AuthProvider>
      </body>
    </html>
  );
}
