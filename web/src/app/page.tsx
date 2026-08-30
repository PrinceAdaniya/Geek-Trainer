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
import type { SessionSummary, Stats, Week, WorkoutSession } from "@/lib/types";

export default function Home() {
  const { profile, loading } = useSession();
  const [stats, setStats] = useState<Stats | null>(null);
  const [active, setActive] = useState<WorkoutSession | null>(null);
  const [recent, setRecent] = useState<SessionSummary[]>([]);
  const [week, setWeek] = useState<Week | null>(null);

  useEffect(() => {
    if (!profile) return;
    void api.get<Stats>("/stats").then(setStats);
    void api.get<WorkoutSession | null>("/sessions/active").then(setActive);
    void api.get<SessionSummary[]>("/sessions").then((r) => setRecent(r.slice(0, 5)));
    void api.get<Week>("/week").then(setWeek);
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
            <p className="label">Operator</p>
            <h1 className="text-[24px] font-semibold leading-tight">{profile.name}</h1>
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
    <section className="mx-auto flex max-w-3xl flex-col gap-8 py-16">
      <div className="flex flex-col gap-4">
        <p className="label text-accent">Training telemetry</p>
        <h1 className="text-[36px] font-semibold leading-[1.1] sm:text-[44px]">
          Every set logged.
          <br />
          <span className="text-ink-dim">Every number earned.</span>
        </h1>
        <p className="max-w-xl text-[16px] leading-relaxed text-ink-dim">
          Tell it what equipment you own and it only offers you exercises you can
          actually load. Log weight, reps, RIR and failure set by set. Keep the streak
          alive and the power level climbs.
        </p>
      </div>
      <div className="flex gap-3">
        <Link
          href="/register"
          className="flex min-h-tap items-center rounded-lg bg-accent px-6 font-semibold text-surface"
        >
          Start training
        </Link>
        <Link
          href="/login"
          className="flex min-h-tap items-center rounded-lg border border-surface-edge px-6"
        >
          Log in
        </Link>
      </div>
      <dl className="grid gap-4 sm:grid-cols-3">
        {[
          ["Equipment-aware", "No barbell? You will never be shown a barbell row."],
          ["Set-level truth", "Weight, reps, RIR, failure, set type — per set, not per exercise."],
          ["Streaks with teeth", "Rest days keep the streak. Drifting does not."],
        ].map(([title, body]) => (
          <div key={title} className="panel p-4">
            <dt className="text-[14px] font-medium">{title}</dt>
            <dd className="mt-1 text-[13px] text-ink-dim">{body}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
