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
    // Prefer illustrated movements on the dashboard - a wall of names is not
    // a reason to browse.
    void api
      .get<ExercisePage>("/exercises?limit=60")
      .then((page) => {
        const withImages = page.data.filter((row) => row.image_url);
        setLibrary((withImages.length >= 6 ? withImages : page.data).slice(0, 6));
        setLibraryTotal(page.total);
      });
  }, [profile]);

  if (loading) return <Spinner />;
  if (!profile) return <Landing />;
  if (!stats) return <Spinner label="Reading telemetry" />;

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
            <p className="label">Dashboard</p>
            <h1 className="text-[24px] font-semibold leading-tight">
              {greeting()}, {profile.name.split(" ")[0]}
            </h1>
          </div>
          <p className="readout text-[12px] text-ink-faint">
            {profile.settings.timezone} · week starts{" "}
            {humanize(profile.settings.week_start)}
          </p>
        </div>

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
                  : "Nothing scheduled — train anyway?"}
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
                Empty session
              </Link>
            </div>
          </div>
        )}

        {/* Power level + charge. The number, the name and the bar together. */}
        <div className="grid gap-4 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)]">
          <Panel title="Power">
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
                <p className="label text-accent">Ladder complete</p>
              )}
              {!stats.trained_today && stats.current_streak > 0 && (
                <p className="text-[13px] text-warn">
                  Streak still live — a rest day keeps it, two in a row does not.
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
              Add your equipment and the library fills with movements you can
              actually load.
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
                Nothing logged yet. Your first session starts the streak.
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

          <Panel title="Rank ladder">
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

function Landing() {
  return (
    <div className="flex flex-col gap-16 py-10 sm:py-16">
      {/* Hero */}
      <section className="flex flex-col items-start gap-6">
        <span className="label rounded-full border border-surface-edge px-3 py-1.5">
          Training log · offline-first · no subscription
        </span>
        <h1 className="max-w-3xl text-[36px] font-semibold leading-[1.08] sm:text-[52px]">
          Log every set.
          <br />
          <span className="text-ink-dim">Watch the numbers move.</span>
        </h1>
        <p className="max-w-xl text-[16px] leading-relaxed text-ink-dim sm:text-[17px]">
          A training tracker built for the gym floor rather than the desk. Tell
          it what equipment you own and it only offers movements you can
          actually load. Then it stays out of the way while you train.
        </p>
        <div className="flex flex-wrap gap-3">
          <Link
            href="/register"
            className="flex min-h-tap items-center rounded-lg bg-accent px-6 font-semibold text-surface transition-opacity hover:opacity-90"
          >
            Create an account
          </Link>
          <Link
            href="/login"
            className="flex min-h-tap items-center rounded-lg border border-surface-edge px-6 transition-colors hover:border-ink-faint"
          >
            Log in
          </Link>
        </div>
        <p className="text-[13px] text-ink-faint">
          Free. No card. Your data exports as CSV or JSON on demand.
        </p>
      </section>

      {/* What makes it different */}
      <section className="flex flex-col gap-6">
        <div>
          <p className="label">Why it is built this way</p>
          <h2 className="mt-1 text-[26px] font-semibold">
            Most trackers are spreadsheets with a login.
          </h2>
        </div>
        <dl className="grid gap-4 md:grid-cols-3">
          {[
            [
              "It knows your gym",
              "Set your equipment once. An exercise needing a barbell and a bench is never offered to someone who owns only a barbell — and when something is out of reach, it says which piece you are missing rather than hiding it.",
            ],
            [
              "It survives the basement",
              "Sets are written to your device first and synced when there is signal. Logging never waits on the network, and replaying a whole offline session cannot duplicate a single rep.",
            ],
            [
              "The numbers are honest",
              "Warm-ups are logged but never counted. Bodyweight work scores real volume. Correct a mistyped set and the personal record it wrongly set is revoked everywhere.",
            ],
          ].map(([title, body]) => (
            <div key={title} className="panel flex flex-col gap-2 p-5">
              <dt className="text-[16px] font-medium">{title}</dt>
              <dd className="text-[14px] leading-relaxed text-ink-dim">{body}</dd>
            </div>
          ))}
        </dl>
      </section>

      {/* The loop */}
      <section className="flex flex-col gap-6">
        <div>
          <p className="label">The loop</p>
          <h2 className="mt-1 text-[26px] font-semibold">
            Plan it, do it, see it move.
          </h2>
        </div>
        <ol className="grid gap-4 md:grid-cols-4">
          {[
            ["01", "Set up your kit", "Pick your equipment and units. The catalogue narrows to what you can do."],
            ["02", "Build the week", "Lay out your days, or let the coach draft one from your equipment and goal."],
            ["03", "Train", "Weight, reps, RIR, failure — set by set, with the rest timer running and last week in view."],
            ["04", "Watch it climb", "Volume, estimated 1RM, records, and a streak that survives a rest day."],
          ].map(([step, title, body]) => (
            <li key={step} className="flex flex-col gap-2">
              <span className="readout text-[13px] text-accent">{step}</span>
              <span className="text-[16px] font-medium">{title}</span>
              <span className="text-[14px] leading-relaxed text-ink-dim">{body}</span>
            </li>
          ))}
        </ol>
      </section>

      {/* Detail grid */}
      <section className="grid gap-4 md:grid-cols-2">
        <div className="panel flex flex-col gap-3 p-6">
          <p className="label">In the session</p>
          <ul className="flex flex-col gap-2 text-[14px] leading-relaxed text-ink-dim">
            <li>Sets prefill from the one before — a repeat is a single tap.</li>
            <li>Steppers at your own plate increment, numeric keypad, no modals.</li>
            <li>Rest timer and clock run on wall time, so a sleeping screen does not lie to you.</li>
            <li>The screen stays awake while you train.</li>
            <li>Demonstration, cues and last week&rsquo;s numbers, without leaving the set you are on.</li>
          </ul>
        </div>
        <div className="panel flex flex-col gap-3 p-6">
          <p className="label">Between sessions</p>
          <ul className="flex flex-col gap-2 text-[14px] leading-relaxed text-ink-dim">
            <li>960 exercises with instructions, and images for the common ones.</li>
            <li>Estimated 1RM by Epley, shown only where it is trustworthy.</li>
            <li>Personal records detected automatically, and revoked when a set is corrected.</li>
            <li>A coach that proposes — it never writes to your log without you.</li>
            <li>Ten power ranks, and a streak that treats rest as training.</li>
          </ul>
        </div>
      </section>

      {/* Honest close */}
      <section className="flex flex-col items-start gap-5 border-t border-surface-edge pt-10">
        <h2 className="max-w-2xl text-[24px] font-semibold leading-snug">
          Built to be used every session, not admired once.
        </h2>
        <p className="max-w-xl text-[15px] leading-relaxed text-ink-dim">
          It is a training log — it does not diagnose injuries, and it does not
          replace a coach. What it does is remember exactly what you did, and
          show you whether it is working.
        </p>
        <Link
          href="/register"
          className="flex min-h-tap items-center rounded-lg bg-accent px-6 font-semibold text-surface transition-opacity hover:opacity-90"
        >
          Start your first session
        </Link>
      </section>
    </div>
  );
}
