"use client";

import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { Suspense, useState } from "react";
import { ApiError, api } from "@/lib/api";
import { useSession } from "@/lib/session";
import { Button, ErrorNote, Input } from "@/components/ui";
import { AuthShell } from "@/components/auth-shell";
import { GYM } from "@/lib/gym";
import type { Profile } from "@/lib/types";

export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  );
}

function LoginForm() {
  const router = useRouter();
  const justReset = useSearchParams().get("reset") === "1";
  const { setProfile } = useSession();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setError("");
    try {
      const profile = await api.post<Profile>("/auth/login", {
        email: form.get("email"),
        password: form.get("password"),
      });
      setProfile(profile);
      router.push("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell>
      <div className="flex flex-col gap-1.5">
        <h1 className="font-display text-[44px] uppercase leading-none">Member log in</h1>
        <p className="text-[14px] leading-relaxed text-ink-dim">
          Sign in to your {GYM.name} account.
        </p>
      </div>
      {justReset && (
        <p role="status" className="rounded-2xl border border-brand-lime/40 bg-brand-lime/10 px-4 py-3 text-[14px] text-brand-lime">
          Your password has been updated. Log in with your new password.
        </p>
      )}
      <form onSubmit={submit} className="flex flex-col gap-4">
        <Input label="Email" name="email" type="email" autoComplete="email" required />
        <div className="flex flex-col gap-1.5">
          <Input
            label="Password"
            name="password"
            type={showPassword ? "text" : "password"}
            autoComplete="current-password"
            required
          />
          <div className="flex items-center justify-between text-[13px]">
            <label className="flex cursor-pointer items-center gap-2 text-ink-dim">
              <input
                type="checkbox"
                checked={showPassword}
                onChange={(e) => setShowPassword(e.target.checked)}
                className="h-4 w-4 accent-[#ff4d8d]"
              />
              Show password
            </label>
            <Link href="/forgot" className="font-semibold text-accent">
              Forgot password?
            </Link>
          </div>
        </div>
        <ErrorNote>{error}</ErrorNote>
        <Button type="submit" disabled={busy} className="!min-h-[52px] !rounded-full bg-brand-gradient !text-[16px] !font-bold">
          {busy ? "Logging in…" : "Log in"}
        </Button>
      </form>
      <div className="flex flex-col gap-1 border-t border-surface-edge pt-5 text-[14px] text-ink-dim">
        <p>
          Member without an online account?{" "}
          <Link href="/register" className="font-semibold text-accent">Create one</Link>
        </p>
        <p>
          Not a member yet?{" "}
          <Link href="/join" className="font-semibold text-accent">Get a free week pass</Link>
        </p>
      </div>
    </AuthShell>
  );
}
