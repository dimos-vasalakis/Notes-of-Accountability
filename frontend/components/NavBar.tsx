"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { api } from "@/lib/api";
import { useCurrentUser } from "@/lib/useCurrentUser";

const LINKS = [
  { href: "/notes", label: "Notes" },
  { href: "/tasks", label: "Tasks" },
  { href: "/timer", label: "Focus" },
  { href: "/pods", label: "Pods" },
  { href: "/exam-prep", label: "Exam", studentOnly: true },
];

export function NavBar() {
  const { user, loading } = useCurrentUser();
  const router = useRouter();
  const pathname = usePathname();

  if (loading || !user) {
    return null;
  }

  const links = LINKS.filter((link) => !link.studentOnly || user.is_student);

  async function handleLogout() {
    await api.post("/api/auth/logout");
    router.push("/login");
    router.refresh();
  }

  return (
    <nav className="sticky top-0 z-20 border-b border-border bg-bg/80 backdrop-blur-md">
      <div className="mx-auto flex max-w-4xl items-center justify-between px-4 py-3 sm:px-6">
        <div className="flex items-center gap-6">
          <Link href="/" className="flex items-center gap-2 font-display text-lg font-semibold">
            <img src="/logo-mark.png" alt="" className="h-7 w-7 rounded-lg" />
            NoA
            <span className="text-xs font-normal text-text-faint">v2</span>
          </Link>
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
