"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useSession } from "@/lib/session";
import { Button, Empty, ErrorNote, Input, Select, Spinner } from "@/components/ui";
import { humanize } from "@/lib/units";
import { DAYS, type DayOfWeek, type Plan, type Week } from "@/lib/types";

export default function WeekPage() {
  const router = useRouter();
  const { profile, loading } = useSession();
  const [week, setWeek] = useState<Week | null>(null);
  const [adding, setAdding] = useState<DayOfWeek | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!loading && !profile) router.replace("/login");
  }, [loading, profile, router]);

  const load = useCallback(async () => {
    setWeek(await api.get<Week>("/week"));
  }, []);

  useEffect(() => {
    if (profile) void load();
  }, [profile, load]);

  if (loading || !profile || !week) return <Spinner />;

  async function createPlan(day: DayOfWeek, name: string) {
    setError("");
    try {
      const plan = await api.post<Plan>("/workouts", { name, day_of_week: day });
      setAdding(null);
      router.push(`/plan/${plan.id}`);
    } catch {
      setError("Could not create that workout.");
    }
  }

  const total = DAYS.reduce((n, day) => n + week.days[day].length, 0) + week.unscheduled.length;

  return (
    <section className="flex flex-col gap-5 py-6">
      <header>
        <h1 className="text-[22px] font-semibold">Your week</h1>
        <p className="text-[13px] text-ink-dim">
          {total === 0
            ? "Nothing planned yet — add a workout to any day."
            : `${total} workout${total === 1 ? "" : "s"} planned.`}
        </p>
      </header>

      <ErrorNote>{error}</ErrorNote>

      <ol className="flex flex-col gap-2">
        {DAYS.map((day) => (
          <li
            key={day}
            className="rounded-2xl border border-surface-edge bg-surface-raised p-4"
          >
            <div className="flex items-center justify-between">
              <h2 className="text-[13px] uppercase tracking-wide text-ink-faint">
                {humanize(day)}
              </h2>
              {adding !== day && (
                <button
                  onClick={() => setAdding(day)}
                  className="min-h-tap px-2 text-[13px] text-ink-dim hover:text-accent"
                >
                  + Add
                </button>
              )}
            </div>

            {week.days[day].length === 0 && adding !== day && (
              <p className="mt-1 text-[14px] text-ink-faint">Rest</p>
            )}

            <ul className="mt-2 flex flex-col gap-2">
              {week.days[day].map((plan) => (
                <li key={plan.id}>
                  <PlanCard plan={plan} />
                </li>
              ))}
            </ul>

            {adding === day && (
              <form
                className="mt-3 flex gap-2"
                onSubmit={(e) => {
                  e.preventDefault();
                  const value = new FormData(e.currentTarget).get("name");
                  if (value) void createPlan(day, String(value));
                }}
              >
                <input
                  name="name"
                  autoFocus
                  placeholder="Back + Biceps"
                  aria-label={`Workout name for ${day}`}
                  className="min-h-tap flex-1 rounded-xl border border-surface-edge bg-surface px-3.5 text-[16px]"
                />
                <Button type="submit">Add</Button>
                <Button type="button" variant="ghost" onClick={() => setAdding(null)}>
                  Cancel
                </Button>
              </form>
            )}
          </li>
        ))}
      </ol>

      {week.unscheduled.length > 0 && (
        <div className="flex flex-col gap-2">
          <h2 className="text-[13px] uppercase tracking-wide text-ink-faint">
            Not on the calendar
          </h2>
          {week.unscheduled.map((plan) => (
            <PlanCard key={plan.id} plan={plan} />
          ))}
        </div>
      )}
    </section>
  );
}

function PlanCard({ plan }: { plan: Plan }) {
  const missing = plan.exercises.filter((e) => !e.exercise.compatible).length;
  return (
    <Link
      href={`/plan/${plan.id}`}
      className="block rounded-xl border border-surface-edge bg-surface px-4 py-3 transition-colors hover:border-ink-faint"
    >
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-[15px] font-medium">{plan.name}</span>
        <span className="text-[13px] text-ink-faint">
          {plan.exercises.length} exercise{plan.exercises.length === 1 ? "" : "s"}
        </span>
      </div>
      {plan.exercises.length > 0 && (
        <p className="mt-1 truncate text-[13px] text-ink-dim">
          {plan.exercises.map((e) => e.exercise.name).join(" · ")}
        </p>
      )}
      {missing > 0 && (
        <p className="mt-1 text-[13px] text-warn">
          {missing} need equipment you have not got
        </p>
      )}
    </Link>
  );
}
