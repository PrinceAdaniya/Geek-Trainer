"use client";

/** One completed session, exactly as it was logged. SPECIFICATIONS.MD Sec 16. */

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useSession } from "@/lib/session";
import { Spinner } from "@/components/ui";
import { formatClock } from "@/lib/hooks";
import { formatWeight, humanize } from "@/lib/units";
import type { SetRecord, WorkoutSession } from "@/lib/types";

export default function SessionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { profile, loading } = useSession();
  const [session, setSession] = useState<WorkoutSession | null>(null);

  useEffect(() => {
    if (!loading && !profile) router.replace("/login");
  }, [loading, profile, router]);

  useEffect(() => {
    if (profile) {
      api
        .get<WorkoutSession>(`/sessions/${id}`)
        .then(setSession)
        .catch(() => router.replace("/history"));
    }
  }, [profile, id, router]);

  if (loading || !profile || !session) return <Spinner />;
  const unit = profile.settings.unit_preference;

  return (
    <section className="flex flex-col gap-5 py-6">
      <header>
        <Link href="/history" className="text-[13px] text-ink-dim hover:text-ink">
          ← History
        </Link>
        <h1 className="mt-1 text-[22px] font-semibold">{session.name}</h1>
        <p className="text-[13px] text-ink-dim">
          {session.date}
          {session.duration_seconds ? ` · ${formatClock(session.duration_seconds)}` : ""}
          {session.status === "cancelled" && " · discarded"}
        </p>
      </header>

      <ol className="flex flex-col gap-3">
        {session.exercises.map((exercise, index) => (
          <li
            key={exercise.id}
            className="rounded-2xl border border-surface-edge bg-surface-raised p-4"
          >
            <p className="text-[15px] font-medium">
              {index + 1}. {exercise.exercise.name}
            </p>
            <p className="mt-0.5 text-[13px] text-ink-dim">
              {humanize(exercise.exercise.primary_muscle)}
              {exercise.replaced_from_exercise_id && " · substituted"}
            </p>

            {exercise.sets.length === 0 ? (
              <p className="mt-2 text-[13px] text-ink-faint">
                {exercise.skipped ? "Skipped." : "No sets logged."}
              </p>
            ) : (
              <ul className="mt-2 flex flex-col gap-1">
                {exercise.sets.map((row) => (
                  <li key={row.id} className="flex gap-3 text-[14px] tabular-nums">
                    <span className="w-6 text-ink-faint">{row.set_number}</span>
                    <span>{describe(row, unit)}</span>
                    {row.set_type !== "working" && (
                      <span className="text-[12px] text-ink-faint">
                        {humanize(row.set_type)}
                      </span>
                    )}
                    {row.failure && <span className="text-[12px] text-warn">failure</span>}
                    {row.rir !== null && !row.failure && (
                      <span className="text-[12px] text-ink-faint">RIR {row.rir}</span>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </li>
        ))}
      </ol>
    </section>
  );
}

function describe(row: SetRecord, unit: "kg" | "lb"): string {
  if (row.duration_seconds != null && row.distance_m != null)
    return `${formatClock(row.duration_seconds)} / ${Math.round(parseFloat(row.distance_m))} m`;
  if (row.duration_seconds != null) return formatClock(row.duration_seconds);
  if (row.distance_m != null) return `${Math.round(parseFloat(row.distance_m))} m`;
  if (row.weight_kg != null) return `${formatWeight(row.weight_kg, unit)} × ${row.reps}`;
  return `${row.reps} reps`;
}
