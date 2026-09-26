"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { ApiError, api } from "@/lib/api";
import { Button, ErrorNote, Input } from "@/components/ui";
import { AuthShell } from "@/components/auth-shell";

export default function ResetPage() {
  return (
    <Suspense>
      <ResetForm />
    </Suspense>
  );
}

function ResetForm() {
  const router = useRouter();
  const token = useSearchParams().get("token") ?? "";
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    if (form.get("password") !== form.get("confirm")) {
      setError("The two passwords don't match.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await api.post("/auth/password/reset", { token, password: form.get("password") });
      router.push("/login?reset=1");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell>
      <div className="flex flex-col gap-1.5">
        <h1 className="font-display text-[44px] uppercase leading-none">New password</h1>
        <p className="text-[14px] leading-relaxed text-ink-dim">Choose a password with at least 10 characters.</p>
      </div>
      {!token ? (
        <ErrorNote>
          This reset link is incomplete. Request a new one from the{" "}
          <Link href="/forgot" className="underline">reset page</Link>.
        </ErrorNote>
      ) : (
        <form onSubmit={submit} className="flex flex-col gap-4">
          <Input label="New password" name="password" type="password" autoComplete="new-password" minLength={10} required />
          <Input label="Confirm new password" name="confirm" type="password" autoComplete="new-password" minLength={10} required />
          <ErrorNote>{error}</ErrorNote>
          <Button type="submit" disabled={busy} className="!min-h-[52px] !rounded-full bg-brand-gradient !text-[16px] !font-bold">
            {busy ? "Saving…" : "Save password"}
          </Button>
        </form>
      )}
    </AuthShell>
  );
}
