"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/AuthContext";
import type { UserPublic } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";

export default function SignupPage() {
  const router = useRouter();
  const { setUser } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isStudent, setIsStudent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const user = await api.post<UserPublic>("/api/auth/signup", {
        email,
        password,
        is_student: isStudent,
      });
      setUser(user);
      router.push("/");
    } catch (err) {
      setError(err instanceof ApiError && err.status === 409 ? "An account with this email already exists" : "Something went wrong");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto flex max-w-sm animate-fade-in flex-col items-center pt-8">
      <img src="/logo-mark.png" alt="Note of Accountability" className="mb-4 h-11 w-11 rounded-xl" />
      <h1 className="text-2xl font-semibold">Create your account</h1>
      <p className="mb-8 mt-1 text-sm text-text-muted">Notes, tasks and focus timers in one place.</p>
      <Card className="w-full p-6">
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <Input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <Input
            type="password"
            placeholder="Password (min. 8 characters)"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={8}
          />
          <label className="flex cursor-pointer items-start gap-2.5 rounded-xl border border-border bg-bg p-3 transition-colors hover:border-accent">
            <input
              type="checkbox"
              checked={isStudent}
              onChange={(e) => setIsStudent(e.target.checked)}
              className="mt-0.5 h-4 w-4 accent-[var(--accent)]"
            />
            <span className="text-sm">
              I&apos;m preparing for the Πανελλήνιες
              <span className="mt-0.5 block text-xs text-text-muted">
                Unlocks the exam countdown and subject-weighted study tracking.
              </span>
            </span>
          </label>
          {error && <p className="text-sm text-danger">{error}</p>}
          <Button type="submit" disabled={submitting}>
            {submitting ? "Signing up..." : "Sign up"}
          </Button>
        </form>
      </Card>
      <p className="mt-6 text-sm text-text-muted">
        Already have an account?{" "}
        <Link href="/login" className="font-medium text-accent hover:underline">
          Log in
        </Link>
      </p>
    </div>
  );
}
