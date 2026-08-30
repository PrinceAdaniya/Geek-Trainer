"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";
import { useState } from "react";
import { ApiError, api } from "@/lib/api";
import { useSession } from "@/lib/session";
import { Button, ErrorNote, Input } from "@/components/ui";
import type { Profile } from "@/lib/types";

export default function LoginPage() {
  const router = useRouter();
  const { setProfile } = useSession();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

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
    <section className="mx-auto flex max-w-sm flex-col gap-5 py-10">
      <h1 className="text-[22px] font-semibold">Log in</h1>
      <form onSubmit={submit} className="flex flex-col gap-4">
        <Input label="Email" name="email" type="email" autoComplete="email" required />
        <Input
          label="Password"
          name="password"
          type="password"
          autoComplete="current-password"
          required
        />
        <ErrorNote>{error}</ErrorNote>
        <Button type="submit" disabled={busy}>
          {busy ? "Logging in…" : "Log in"}
        </Button>
      </form>
      <p className="text-[14px] text-ink-dim">
        No account?{" "}
        <Link href="/register" className="text-accent">
          Sign up
        </Link>
      </p>
    </section>
  );
}
