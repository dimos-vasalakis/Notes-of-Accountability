"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef } from "react";

import { ThemeToggle } from "@/components/ThemeToggle";
import { useCurrentUser } from "@/lib/useCurrentUser";

const LINKS = [
  { href: "/notes", label: "Notes" },
  { href: "/tasks", label: "Tasks" },
  { href: "/timer", label: "Focus" },
  { href: "/pods", label: "Pods" },
  { href: "/exam-prep", label: "Exam", studentOnly: true },
];

export function NavBar() {
  const { user, loading, logout } = useCurrentUser();
  const router = useRouter();
  const pathname = usePathname();

  const initialPathname = useRef(pathname);
  const hasNavigatedInApp = useRef(false);

  useEffect(() => {
    if (pathname !== initialPathname.current) {
      hasNavigatedInApp.current = true;
    }
  }, [pathname]);

  const canGoBack = !!pathname && pathname !== "/";

  function handleBack() {
    if (hasNavigatedInApp.current) {
      router.back();
    } else {
      router.push("/");
    }
  }

  const backButton = (
    <button
      onClick={handleBack}
      aria-label="Go back"
      className="rounded-lg p-1.5 text-text-muted transition-colors hover:bg-accent-soft/60 hover:text-text"
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
        className="h-5 w-5"
      >
        <path d="M15 18l-6-6 6-6" />
      </svg>
    </button>
  );

  if (loading) return null;

  if (!user) {
    // Logged-out pages (landing, login, signup) get a slim bar: back + theme.
    return (
      <nav className="mx-auto flex max-w-4xl items-center justify-between px-4 pt-3 sm:px-6">
        <div className="h-8">{canGoBack && backButton}</div>
        <ThemeToggle />
      </nav>
    );
  }

  const links = LINKS.filter((link) => !link.studentOnly || user.is_student);
  async function handleLogout() {
    await logout();
    // Logging out invalidates the whole in-app history stack, so a single
    // press of the back button should land on the landing page rather than
    // stepping back through now-unreachable authenticated pages. Advancing
    // initialPathname here too keeps the pathname-watching effect below from
    // immediately flipping hasNavigatedInApp back to true once the route
    // changes to /login.
    hasNavigatedInApp.current = false;
    initialPathname.current = "/login";
    router.push("/login");
    router.refresh();
  }

  return (
    <nav className="sticky top-0 z-20 border-b border-border bg-bg/80 backdrop-blur-md">
      <div className="mx-auto flex max-w-4xl items-center justify-between px-4 py-3 sm:px-6">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            {canGoBack && backButton}
            <Link href="/" className="flex items-center gap-2 font-display text-lg font-semibold">
              <img src="/logo-mark.png" alt="" className="h-7 w-7 rounded-lg" />
              Notes of Accountability
              <span className="text-xs font-normal text-text-faint">v2</span>
            </Link>
          </div>
          <div className="hidden items-center gap-1 sm:flex">
            {links.map((link) => {
              const active = pathname?.startsWith(link.href);
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
                    active
                      ? "bg-accent-soft text-accent"
                      : "text-text-muted hover:bg-accent-soft/60 hover:text-text"
                  }`}
                >
                  {link.label}
                </Link>
              );
            })}
          </div>
        </div>
        <div className="flex items-center gap-3">
          <ThemeToggle />
          <span className="hidden text-sm text-text-faint sm:inline">{user.email}</span>
          <button
            onClick={handleLogout}
            className="rounded-lg px-3 py-1.5 text-sm font-medium text-text-muted transition-colors hover:bg-accent-soft/60 hover:text-text"
          >
            Logout
          </button>
        </div>
      </div>
      <div className="flex items-center gap-1 border-t border-border px-4 py-2 sm:hidden">
        {links.map((link) => {
          const active = pathname?.startsWith(link.href);
          return (
            <Link
              key={link.href}
              href={link.href}
              className={`flex-1 rounded-lg px-3 py-1.5 text-center text-sm font-medium transition-colors ${
                active ? "bg-accent-soft text-accent" : "text-text-muted"
              }`}
            >
              {link.label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
