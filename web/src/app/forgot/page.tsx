"use client";

import Link from "next/link";
import { useState } from "react";
import { ApiError, api } from "@/lib/api";
import { Button, ErrorNote, Input } from "@/components/ui";
import { AuthShell } from "@/components/auth-shell";

export default function ForgotPage() {
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setError("");
    try {
      await api.post("/auth/password/reset-request", { email: form.get("email") });
      setSent(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell>
      <div className="flex flex-col gap-1.5">
        <h1 className="font-display text-[44px] uppercase leading-none">Reset password</h1>
        <p className="text-[14px] leading-relaxed text-ink-dim">
          Enter the email address on your account and we&rsquo;ll send you a link to choose a new password.
        </p>
      </div>
      {sent ? (
        <p role="status" className="rounded-2xl border border-brand-lime/40 bg-brand-lime/10 px-4 py-3 text-[15px] text-brand-lime">
          If an account exists for that address, a reset link is on its way. The link is valid for 15 minutes.
        </p>
      ) : (
        <form onSubmit={submit} className="flex flex-col gap-4">
          <Input label="Email" name="email" type="email" autoComplete="email" required />
          <ErrorNote>{error}</ErrorNote>
          <Button type="submit" disabled={busy} className="!min-h-[52px] !rounded-full bg-brand-gradient !text-[16px] !font-bold">
            {busy ? "Sending…" : "Send reset link"}
          </Button>
        </form>
      )}
      <p className="text-[14px] text-ink-dim">
        <Link href="/login" className="font-semibold text-accent">Back to log in</Link>
      </p>
    </AuthShell>
  );
}
