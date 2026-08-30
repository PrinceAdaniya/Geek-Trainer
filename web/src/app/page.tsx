"use client";

import Link from "next/link";
import { useSession } from "@/lib/session";
import { Spinner } from "@/components/ui";
import { formatWeight } from "@/lib/units";

export default function Home() {
  const { profile, loading } = useSession();

  if (loading) return <Spinner />;

  if (!profile) {
    return (
      <section className="flex flex-col gap-6 py-10">
        <div className="flex flex-col gap-3">
          <h1 className="text-[28px] font-semibold leading-tight">
            Plan your week. Log every set.
            <br />
            <span className="text-ink-dim">Watch the numbers move.</span>
          </h1>
          <p className="max-w-md text-[15px] leading-relaxed text-ink-dim">
            Tell it what equipment you have, and it only ever offers you exercises you can
            actually do. Every set is recorded on its own — weight, reps, effort, whether you
            hit failure.
          </p>
        </div>
        <div className="flex gap-3">
          <Link
            href="/register"
            className="flex min-h-tap items-center rounded-xl bg-accent px-5 font-semibold text-surface"
          >
            Get started
          </Link>
          <Link
            href="/login"
            className="flex min-h-tap items-center rounded-xl border border-surface-edge px-5 text-ink"
          >
            Log in
          </Link>
        </div>
      </section>
    );
  }

  const equipment = profile.settings.available_equipment;

  return (
    <section className="flex flex-col gap-6 py-6">
      <div>
        <h1 className="text-[24px] font-semibold">Hi {profile.name.split(" ")[0]}.</h1>
        <p className="text-[15px] text-ink-dim">
          {equipment.length === 1
            ? "Add your equipment and the catalogue narrows to what you can actually do."
            : `${equipment.length} equipment items set.`}
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <Link
          href="/exercises"
          className="rounded-2xl border border-surface-edge bg-surface-raised p-5 transition-colors hover:border-ink-faint"
        >
          <p className="text-[15px] font-medium">Browse exercises</p>
          <p className="mt-1 text-[13px] text-ink-dim">
            Filtered to your equipment, with nothing you cannot load.
          </p>
        </Link>
        <Link
          href="/profile"
          className="rounded-2xl border border-surface-edge bg-surface-raised p-5 transition-colors hover:border-ink-faint"
        >
          <p className="text-[15px] font-medium">Equipment &amp; settings</p>
          <p className="mt-1 text-[13px] text-ink-dim">
            Units {profile.settings.unit_preference} · bodyweight{" "}
            {formatWeight(profile.latest_bodyweight_kg, profile.settings.unit_preference)}
          </p>
        </Link>
      </div>

      <div className="rounded-2xl border border-dashed border-surface-edge p-5">
        <p className="text-[14px] text-ink-dim">
          Weekly schedule and set logging arrive in the next phases. Right now you can set up
          your equipment and explore the catalogue.
        </p>
      </div>
    </section>
  );
}
