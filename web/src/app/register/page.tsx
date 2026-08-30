"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";
import { useState } from "react";
import { ApiError, api } from "@/lib/api";
import { useSession } from "@/lib/session";
import { Button, ErrorNote, Input } from "@/components/ui";
import type { Profile } from "@/lib/types";

export default function RegisterPage() {
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
      const profile = await api.post<Profile>("/auth/register", {
        name: form.get("name"),
        email: form.get("email"),
        password: form.get("password"),
        // Sec 3.3 - the browser knows the user's timezone; do not make them pick.
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
      });
      setProfile(profile);
      router.push("/profile");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="mx-auto flex max-w-sm flex-col gap-5 py-10">
      <h1 className="text-[22px] font-semibold">Create your account</h1>
      <form onSubmit={submit} className="flex flex-col gap-4">
        <Input label="Name" name="name" autoComplete="name" required />
        <Input label="Email" name="email" type="email" autoComplete="email" required />
        <Input
          label="Password"
          name="password"
          type="password"
          autoComplete="new-password"
          minLength={10}
          required
        />
        <p className="-mt-1 text-[13px] text-ink-faint">At least 10 characters.</p>
        <ErrorNote>{error}</ErrorNote>
        <Button type="submit" disabled={busy}>
          {busy ? "Creating…" : "Create account"}
        </Button>
      </form>
      <p className="text-[14px] text-ink-dim">
        Already have one?{" "}
        <Link href="/login" className="text-accent">
          Log in
        </Link>
      </p>
    </section>
  );
}
