"use client";

/** The dashboard. Everything the user should see before they start training. */

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useSession } from "@/lib/session";
import { Button, Spinner } from "@/components/ui";
import {
  ChargeMeter,
  Panel,
  PowerBadge,
  PowerUp,
  RankLadder,
  Stat,
  TrainingHeatmap,
} from "@/components/hud";
import { formatClock } from "@/lib/hooks";
import { Landing } from "@/components/landing";
import { GymToday, InviteCard } from "@/components/gym-today";
import { formatWeight, humanize } from "@/lib/units";
import type {
  Exercise,
  ExercisePage,
  SessionSummary,
  Stats,
  Week,
  WorkoutSession,
} from "@/lib/types";

export default function Home() {
  const { profile, loading } = useSession();
  const [stats, setStats] = useState<Stats | null>(null);
  const [active, setActive] = useState<WorkoutSession | null>(null);
  const [recent, setRecent] = useState<SessionSummary[]>([]);
  const [week, setWeek] = useState<Week | null>(null);
  const [library, setLibrary] = useState<Exercise[]>([]);
  const [libraryTotal, setLibraryTotal] = useState(0);

  useEffect(() => {
    if (!profile) return;
    void api.get<Stats>("/stats").then(setStats);
    void api.get<WorkoutSession | null>("/sessions/active").then(setActive);
    void api.get<SessionSummary[]>("/sessions").then((r) => setRecent(r.slice(0, 5)));
    void api.get<Week>("/week").then(setWeek);
    // Compound movements with a demonstration, because the point of this
    // panel is to invite browsing - and an alphabetical page of the whole
    // catalogue opens on ankle rolls.
    void Promise.all([
      api.get<ExercisePage>("/exercises?limit=100&type=compound"),
      api.get<ExercisePage>("/exercises?limit=1"),
    ]).then(([compounds, all]) => {
      const illustrated = compounds.data.filter((row) => row.image_url);
      const pool = illustrated.length >= 6 ? illustrated : compounds.data;
      // Rotate daily so the panel is not the same six movements forever.
      const offset = pool.length
        ? Math.floor(Date.now() / 86_400_000) % pool.length
        : 0;
      setLibrary([...pool.slice(offset), ...pool.slice(0, offset)].slice(0, 6));
      setLibraryTotal(all.total);
    });
  }, [profile]);

  if (loading) return <Spinner />;
  if (!profile) return <Landing />;
  if (!stats) return <Spinner />;

  const unit = profile.settings.unit_preference;
  const todayKey = new Date()
    .toLocaleDateString("en-US", { weekday: "long" })
    .toLowerCase();
  const todaysPlans = week?.days[todayKey as keyof typeof week.days] ?? [];

  return (
    <>
      <PowerUp
        level={stats.rank.level}
        name={stats.rank.name}
        color={stats.rank.color}
        blurb={stats.rank.blurb}
      />

      <div className="flex flex-col gap-4 py-5">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="label text-brand-orange">Member dashboard</p>
            <h1 className="font-display text-[34px] uppercase leading-none sm:text-[40px]">
              {greeting()}, {profile.name.split(" ")[0]}
            </h1>
          </div>
          <p className="readout text-[12px] text-ink-faint">
            {profile.settings.timezone} · week starts{" "}
            {humanize(profile.settings.week_start)}
          </p>
        </div>

        <GymToday />

        {active ? (
          <Link
            href="/session"
            className="panel relative flex items-center justify-between gap-4 overflow-hidden p-4"
          >
            <span
              className="pointer-events-none absolute inset-x-0 h-16 bg-accent/5 blur-xl"
              aria-hidden
            />
            <div className="relative">
              <p className="label text-accent">Session in progress</p>
              <p className="mt-1 text-[17px] font-semibold">{active.name}</p>
              <p className="readout text-[13px] text-ink-dim">
                {active.exercises.reduce((n, e) => n + e.sets.length, 0)} sets logged
              </p>
            </div>
            <span className="relative rounded-lg bg-accent px-4 py-2.5 text-[14px] font-semibold text-surface">
              Resume →
            </span>
          </Link>
        ) : (
          <div className="panel flex flex-wrap items-center justify-between gap-3 p-4">
            <div>
              <p className="label">Today · {humanize(todayKey)}</p>
              <p className="mt-1 text-[15px]">
                {todaysPlans.length > 0
                  ? todaysPlans.map((p) => p.name).join(" · ")
                  : "No workout scheduled today."}
              </p>
            </div>
            <div className="flex gap-2">
              {todaysPlans.length > 0 && (
                <StartButton workoutId={todaysPlans[0].id} label={`Start ${todaysPlans[0].name}`} />
              )}
              <Link
                href="/session"
                className="flex min-h-tap items-center rounded-lg border border-surface-edge px-4 text-[14px]"
              >
                Start a workout
              </Link>
            </div>
          </div>
        )}

        <Panel
          title="Exercise library"
          right={
            <Link href="/exercises" className="label hover:text-accent">
              browse all {libraryTotal || ""} →
            </Link>
          }
        >
          {library.length === 0 ? (
            <p className="text-[13px] text-ink-dim">
              Set your equipment in Profile to see matching exercises.
            </p>
          ) : (
            <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
              {library.map((exercise) => (
                <li key={exercise.id}>
                  <Link
                    href={`/exercises/${exercise.id}`}
                    className="group flex h-full flex-col gap-2 rounded-xl border border-surface-edge bg-surface p-2.5 transition-colors hover:border-accent/50"
                  >
                    <span className="flex aspect-square items-center justify-center overflow-hidden rounded-lg bg-surface-raised">
                      {exercise.image_url ? (
                        /* eslint-disable-next-line @next/next/no-img-element */
                        <img
                          src={exercise.image_url}
                          alt=""
                          loading="lazy"
                          className="h-full w-full object-contain transition-transform group-hover:scale-105"
                        />
                      ) : (
                        <span className="label px-2 text-center">
                          {humanize(exercise.primary_muscle)}
                        </span>
                      )}
                    </span>
                    <span className="flex flex-col gap-0.5">
                      <span className="line-clamp-2 text-[13px] leading-snug">
                        {exercise.name}
                      </span>
                      <span className="label">
                        {humanize(exercise.primary_muscle)}
                      </span>
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Panel>


        {/* Streak level and progress to the next one. */}
        <div className="grid gap-4 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)]">
          <Panel title="Streak">
            <div className="flex flex-col gap-5">
              <PowerBadge
                level={stats.rank.level}
                name={stats.rank.name}
                color={stats.rank.color}
                streak={stats.current_streak}
              />
              <p className="text-[13px] text-ink-dim">{stats.rank.blurb}</p>
              {stats.next_rank ? (
                <ChargeMeter
                  progress={stats.progress_to_next}
                  color={stats.rank.color}
                  fromLabel={stats.rank.name}
                  toLabel={`${stats.next_rank.name} · ${stats.next_rank.threshold}d`}
                />
              ) : (
                <p className="label text-accent">Highest level reached</p>
              )}
              {!stats.trained_today && stats.current_streak > 0 && (
                <p className="text-[13px] text-warn">
                  Train today or tomorrow to keep your streak. Two rest days in a row resets it.
                </p>
              )}
            </div>
          </Panel>

          <Panel title="Last 12 weeks">
            <TrainingHeatmap activeDays={stats.active_days} ramp={stats.heatmap_ramp} />
          </Panel>
        </div>

        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <Stat
            label="Current streak"
            value={stats.current_streak}
            unit="days"
            tone={stats.current_streak > 0 ? "accent" : "default"}
            hint={`Best ${stats.longest_streak}`}
          />
          <Stat label="Sessions" value={stats.total_sessions} hint="All time" />
          <Stat
            label="Volume this week"
            value={formatWeight(stats.volume_this_week_kg, unit).split(" ")[0]}
            unit={unit}
            hint={`${stats.sets_this_week} working sets`}
          />
          <Stat
            label="Total volume"
            value={Math.round(
              parseFloat(formatWeight(stats.total_volume_kg, unit).split(" ")[0]) / 1000,
            )}
            unit={`k ${unit}`}
            hint="Warm-ups excluded"
          />
        </div>

        <InviteCard />

        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
          <Panel
            title="Recent sessions"
            right={
              <Link href="/history" className="label hover:text-accent">
                all →
              </Link>
            }
          >
            {recent.length === 0 ? (
              <p className="text-[13px] text-ink-dim">
                No workouts logged yet.
              </p>
            ) : (
              <ul className="flex flex-col divide-y divide-surface-edge">
                {recent.map((row) => (
                  <li key={row.id}>
                    <Link
                      href={`/history/${row.id}`}
                      className="flex items-center justify-between gap-3 py-2.5"
                    >
                      <span className="min-w-0">
                        <span className="block truncate text-[14px]">{row.name}</span>
                        <span className="readout text-[12px] text-ink-faint">
                          {row.date} · {row.set_count} sets
                          {row.duration_seconds
                            ? ` · ${formatClock(row.duration_seconds)}`
                            : ""}
                        </span>
                      </span>
                      <span className="text-ink-faint">→</span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </Panel>

          <Panel title="Streak levels">
            <RankLadder
              ladder={stats.ladder}
              currentLevel={stats.rank.level}
              streak={stats.current_streak}
            />
          </Panel>
        </div>
      </div>
    </>
  );
}

function greeting(): string {
  const hour = new Date().getHours();
  if (hour < 5) return "Still up";
  if (hour < 12) return "Morning";
  if (hour < 18) return "Afternoon";
  return "Evening";
}

function StartButton({ workoutId, label }: { workoutId: string; label: string }) {
  const [busy, setBusy] = useState(false);
  return (
    <Button
      disabled={busy}
      onClick={async () => {
        setBusy(true);
        const { uuid7 } = await import("@/lib/hooks");
        await api.post("/sessions", { id: uuid7(), workout_id: workoutId });
        window.location.href = "/session";
      }}
    >
      {busy ? "Starting…" : label}
    </Button>
  );
}
