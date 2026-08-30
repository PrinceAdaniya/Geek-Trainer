"use client";

/** Progress and records. SPECIFICATIONS.MD Sec 14, Sec 15. */

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, query } from "@/lib/api";
import { useSession } from "@/lib/session";
import { Empty, Input, Spinner } from "@/components/ui";
import { Panel, Stat } from "@/components/hud";
import { BarSeries, LineSeries, RankedBars } from "@/components/charts";
import { toDisplay, humanize } from "@/lib/units";
import type {
  Exercise,
  ExercisePage,
  ExerciseProgress,
  PersonalRecord,
  Progress,
} from "@/lib/types";

const RECORD_LABEL: Record<string, string> = {
  heaviest_weight: "Heaviest",
  best_e1rm: "Best est. 1RM",
  highest_session_volume: "Best session volume",
  longest_duration: "Longest hold",
  furthest_distance: "Furthest",
  most_reps_at_weight: "Most reps",
};

export default function ProgressPage() {
  const router = useRouter();
  const { profile, loading } = useSession();
  const [progress, setProgress] = useState<Progress | null>(null);
  const [records, setRecords] = useState<PersonalRecord[]>([]);
  const [picked, setPicked] = useState<ExerciseProgress | null>(null);
  const [q, setQ] = useState("");
  const [options, setOptions] = useState<Exercise[]>([]);

  useEffect(() => {
    if (!loading && !profile) router.replace("/login");
  }, [loading, profile, router]);

  useEffect(() => {
    if (!profile) return;
    void api.get<Progress>("/progress").then(setProgress);
    void api.get<PersonalRecord[]>("/records").then(setRecords);
  }, [profile]);

  useEffect(() => {
    if (!profile || q.length < 2) {
      setOptions([]);
      return;
    }
    const timer = setTimeout(async () => {
      const page = await api.get<ExercisePage>(`/exercises${query({ q, limit: 8 })}`);
      setOptions(page.data);
    }, 200);
    return () => clearTimeout(timer);
  }, [profile, q]);

  if (loading || !profile || !progress) return <Spinner />;
  const unit = profile.settings.unit_preference;

  const weekly = progress.weekly.map((row) => ({
    key: row.week_start,
    value: toDisplay(parseFloat(row.volume_kg), unit),
    caption: row.week_start.slice(5),
  }));

  const totalVolume = weekly.reduce((n, w) => n + w.value, 0);

  return (
    <section className="flex flex-col gap-4 py-5">
      <header>
        <p className="label">Telemetry</p>
        <h1 className="text-[24px] font-semibold">Progress</h1>
      </header>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat label="Sessions (12 wk)" value={progress.sessions_completed} />
        <Stat
          label="Volume (12 wk)"
          value={Math.round(totalVolume).toLocaleString()}
          unit={unit}
        />
        <Stat
          label="Active weeks"
          value={`${progress.consistency_weeks}/${progress.weekly.length}`}
          hint="Weeks with at least one session"
        />
        <Stat label="Records" value={records.length} tone="accent" />
      </div>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
        <Panel title={`Weekly volume · ${unit}`}>
          <BarSeries data={weekly} unit={unit} label="Weekly training volume" />
          <p className="mt-2 text-[12px] text-ink-faint">
            Working sets only — warm-ups are logged but never counted.
          </p>
        </Panel>

        <Panel title="Sets by muscle · 12 weeks">
          <RankedBars
            rows={progress.muscles.slice(0, 8).map((m) => ({
              label: humanize(m.muscle),
              value: m.sets,
            }))}
            unit="sets"
          />
        </Panel>
      </div>

      <Panel title="One exercise">
        <div className="flex flex-col gap-3">
          <Input
            label="Which movement?"
            placeholder="bench press, squat, pull-up…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
          {options.length > 0 && (
            <ul className="flex flex-wrap gap-2">
              {options.map((option) => (
                <li key={option.id}>
                  <button
                    onClick={async () => {
                      setPicked(
                        await api.get<ExerciseProgress>(
                          `/progress/exercises/${option.id}`,
                        ),
                      );
                      setQ("");
                      setOptions([]);
                    }}
                    className="min-h-tap rounded-full border border-surface-edge px-4 text-[13px] hover:border-accent"
                  >
                    {option.name}
                  </button>
                </li>
              ))}
            </ul>
          )}

          {picked && (
            <div className="flex flex-col gap-4">
              <div className="flex items-baseline justify-between">
                <h3 className="text-[16px] font-medium">{picked.exercise_name}</h3>
                <span className="readout text-[12px] text-ink-faint">
                  {picked.points.length} session{picked.points.length === 1 ? "" : "s"}
                </span>
              </div>

              {picked.points.length < 3 ? (
                <p className="text-[13px] text-ink-dim">
                  {picked.points.length === 0
                    ? "You have not logged this movement yet."
                    : "Not enough sessions to show a trend yet — three is the minimum."}
                </p>
              ) : (
                <LineSeries
                  points={picked.points
                    .filter((p) => p.best_e1rm_kg)
                    .map((p) => ({
                      x: p.date.slice(5),
                      y: toDisplay(parseFloat(p.best_e1rm_kg!), unit),
                    }))}
                  unit={unit}
                  label={`${picked.exercise_name} estimated 1RM`}
                />
              )}
              <p className="text-[12px] text-ink-faint">
                Estimated 1RM uses Epley — weight × (1 + reps ÷ 30) — and only for
                sets of 12 reps or fewer, where it is trustworthy.
              </p>

              {picked.records.length > 0 && (
                <ul className="flex flex-wrap gap-2">
                  {picked.records
                    .filter((r) => r.record_type !== "most_reps_at_weight")
                    .map((record) => (
                      <li
                        key={record.record_type}
                        className="rounded-lg border border-surface-edge px-3 py-2"
                      >
                        <span className="label">{RECORD_LABEL[record.record_type]}</span>
                        <p className="readout text-[15px]">
                          {formatRecord(record, unit)}
                        </p>
                      </li>
                    ))}
                </ul>
              )}
            </div>
          )}
        </div>
      </Panel>

      <Panel title="Personal records">
        {records.length === 0 ? (
          <Empty
            title="No records yet."
            hint="Finish a session and the first ones appear here automatically."
          />
        ) : (
          <ul className="flex flex-col divide-y divide-surface-edge">
            {records.map((record) => (
              <li
                key={`${record.exercise_id}-${record.record_type}`}
                className="flex items-center justify-between gap-3 py-2.5"
              >
                <span className="min-w-0">
                  <span className="block truncate text-[14px]">{record.exercise_name}</span>
                  <span className="label">{RECORD_LABEL[record.record_type]}</span>
                </span>
                <span className="text-right">
                  <span className="readout block text-[15px] text-accent">
                    {formatRecord(record, unit)}
                  </span>
                  <span className="readout text-[11px] text-ink-faint">
                    {record.achieved_on}
                  </span>
                </span>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </section>
  );
}

function formatRecord(record: PersonalRecord, unit: "kg" | "lb"): string {
  const value = parseFloat(record.value);
  switch (record.record_type) {
    case "longest_duration":
      return `${Math.round(value)} s`;
    case "furthest_distance":
      return `${Math.round(value)} m`;
    case "most_reps_at_weight":
      return `${value} × ${Math.round(toDisplay(parseFloat(record.qualifier), unit))} ${unit}`;
    default: {
      const shown = Math.round(toDisplay(value, unit) * 10) / 10;
      const reps = record.reps ? ` × ${record.reps}` : "";
      return `${shown} ${unit}${record.record_type === "heaviest_weight" ? reps : ""}`;
    }
  }
}
