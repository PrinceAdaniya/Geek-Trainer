"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";
import { useState } from "react";
import { ApiError, api } from "@/lib/api";
import { useSession } from "@/lib/session";
import { Button, ErrorNote, Input } from "@/components/ui";
import { AuthShell } from "@/components/auth-shell";
import type { Profile } from "@/lib/types";
import { GYM, GYM_EQUIPMENT } from "@/lib/gym";

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
      // Members train here, so start them with the gym's full equipment list:
      // the exercise library then shows everything the floor can load.
      try {
        setProfile(await api.put<Profile>("/profile", { available_equipment: GYM_EQUIPMENT }));
      } catch {
        setProfile(profile);
      }
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
        <h1 className="font-display text-[44px] uppercase leading-none">Create your account</h1>
        <p className="text-[14px] leading-relaxed text-ink-dim">Create your {GYM.name} member account to log workouts, check the class timetable and contact the team.</p>
      </div>
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
        <Button type="submit" disabled={busy} className="!min-h-[52px] !rounded-full bg-brand-gradient !text-[16px] !font-bold">
          {busy ? "Creating account…" : "Create account"}
        </Button>
      </form>
      <p className="text-[14px] text-ink-dim">
        Already have one?{" "}
        <Link href="/login" className="text-accent">
          Log in
        </Link>
      </p>
    </AuthShell>
  );
}
