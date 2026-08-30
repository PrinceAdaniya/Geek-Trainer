"use client";

/**
 * The coach. SPECIFICATIONS.MD Sec 17-21.
 *
 * Everything here is a *proposal*. Nothing changes your data until you press
 * save, which is what keeps a hallucination an annoyance rather than silent
 * corruption (Sec 17.2).
 */

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError, api, query } from "@/lib/api";
import { useSession } from "@/lib/session";
import { Button, Chip, ErrorNote, Input, Select, Spinner } from "@/components/ui";
import { Panel } from "@/components/hud";
import { humanize } from "@/lib/units";
import type {
  AiBudget,
  Analysis,
  Exercise,
  ExercisePage,
  Plan,
  Vocabulary,
  WorkoutProposal,
} from "@/lib/types";

const GOALS = ["hypertrophy", "strength", "endurance", "general", "fat_loss"];

export default function CoachPage() {
  const router = useRouter();
  const { profile, loading } = useSession();
  const [vocab, setVocab] = useState<Vocabulary | null>(null);
  const [budget, setBudget] = useState<AiBudget | null>(null);

  const [targets, setTargets] = useState<string[]>(["back"]);
  const [goal, setGoal] = useState("hypertrophy");
  const [minutes, setMinutes] = useState(60);
  const [proposal, setProposal] = useState<WorkoutProposal | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState<string | null>(null);

  useEffect(() => {
    if (!loading && !profile) router.replace("/login");
  }, [loading, profile, router]);

  useEffect(() => {
    if (!profile) return;
    void api.get<Vocabulary>("/vocabulary").then(setVocab);
    void api.get<AiBudget>("/ai/budget").then(setBudget);
  }, [profile]);

  if (loading || !profile) return <Spinner />;

  async function generate() {
    setBusy(true);
    setError("");
    setSaved(null);
    try {
      setProposal(
        await api.post<WorkoutProposal>("/ai/workout", {
          targets,
          goal,
          session_minutes: minutes,
        }),
      );
      setBudget(await api.get<AiBudget>("/ai/budget"));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not build a plan.");
      setProposal(null);
    } finally {
      setBusy(false);
    }
  }

  async function savePlan() {
    if (!proposal) return;
    setBusy(true);
    try {
      const plan = await api.post<Plan>("/workouts", {
        name: proposal.name,
        target_muscles: proposal.target_muscles.filter(
          (t) => vocab?.muscles.includes(t) || vocab?.body_parts.includes(t),
        ),
        notes: proposal.notes,
      });
      for (const row of proposal.exercises) {
        await api.post(`/workouts/${plan.id}/exercises`, {
          exercise_id: row.exercise.id,
          planned_sets: row.sets,
          planned_reps_min: row.reps_min,
          planned_reps_max: row.reps_max,
        });
      }
      setSaved(plan.id);
    } catch {
      setError("Could not save that plan.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="flex flex-col gap-4 py-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="label">Assistant</p>
          <h1 className="text-[24px] font-semibold">Coach</h1>
        </div>
        {budget && (
          <p className="readout text-[12px] text-ink-faint">
            {budget.ai_configured
              ? `${budget.remaining} of ${budget.daily_limit} AI requests left today`
              : "AI not configured — plans are built from rules"}
          </p>
        )}
      </header>

      {budget && !budget.ai_configured && (
        /* Sec 21.6 - visibly disabled with a reason, never silently broken. */
        <p className="rounded-lg border border-surface-edge bg-surface-raised px-4 py-3 text-[13px] text-ink-dim">
          No AI provider is configured, so everything below is built by rules
          instead: filtered to your equipment, compounds first, capped by session
          length. Set <code className="text-accent">ANTHROPIC_API_KEY</code> on the
          API to turn the assistant on.
        </p>
      )}

      <Panel title="Build me a session">
        <div className="flex flex-col gap-4">
          <div>
            <p className="label mb-2">Train what?</p>
            <div className="flex flex-wrap gap-2">
              {vocab?.body_parts.map((part) => (
                <Chip
                  key={part}
                  selected={targets.includes(part)}
                  onClick={() =>
                    setTargets((current) =>
                      current.includes(part)
                        ? current.filter((t) => t !== part)
                        : [...current, part],
                    )
                  }
                >
                  {humanize(part)}
                </Chip>
              ))}
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            <Select label="Goal" value={goal} onChange={(e) => setGoal(e.target.value)}>
              {GOALS.map((g) => (
                <option key={g} value={g}>
                  {humanize(g)}
                </option>
              ))}
            </Select>
            <Input
              label="Minutes"
              type="number"
              inputMode="numeric"
              value={minutes}
              onChange={(e) => setMinutes(Number(e.target.value) || 60)}
            />
            <div className="flex items-end">
              <Button
                className="w-full"
                disabled={busy || targets.length === 0}
                onClick={() => void generate()}
              >
                {busy ? "Building…" : "Build it"}
              </Button>
            </div>
          </div>

          <ErrorNote>{error}</ErrorNote>
        </div>
      </Panel>

      {proposal && (
        <Panel
          title={`Proposal · built by ${proposal.source === "ai" ? "AI" : "rules"}`}
          right={
            saved ? (
              <a href={`/plan/${saved}`} className="label text-accent">
                saved → open it
              </a>
            ) : (
              <Button onClick={() => void savePlan()} disabled={busy}>
                Save as a workout
              </Button>
            )
          }
        >
          <div className="flex flex-col gap-3">
            <div>
              <h3 className="text-[17px] font-semibold">{proposal.name}</h3>
              {proposal.notes && (
                <p className="mt-1 text-[13px] text-ink-dim">{proposal.notes}</p>
              )}
            </div>

            {proposal.warnings.length > 0 && (
              <ul className="flex flex-col gap-1">
                {proposal.warnings.map((warning) => (
                  <li key={warning} className="text-[13px] text-warn">
                    {warning}
                  </li>
                ))}
              </ul>
            )}

            <ol className="flex flex-col gap-2">
              {proposal.exercises.map((row, index) => (
                <li
                  key={row.exercise.id}
                  className="rounded-xl border border-surface-edge bg-surface p-3"
                >
                  <div className="flex items-baseline justify-between gap-3">
                    <span className="text-[15px] font-medium">
                      {index + 1}. {row.exercise.name}
                    </span>
                    <span className="readout shrink-0 text-[13px] text-ink-dim">
                      {row.sets} × {row.reps_min}–{row.reps_max}
                    </span>
                  </div>
                  <p className="mt-1 text-[13px] text-ink-dim">{row.rationale}</p>
                  <p className="mt-0.5 text-[12px] text-ink-faint">
                    {humanize(row.exercise.primary_muscle)} ·{" "}
                    {row.exercise.equipment.map(humanize).join(", ")}
                  </p>
                </li>
              ))}
            </ol>

            <p className="text-[12px] text-ink-faint">
              Nothing has been saved yet. Review it, then save — or change the
              inputs and build another.
            </p>
          </div>
        </Panel>
      )}

      <AnalysisPanel />
    </section>
  );
}

function AnalysisPanel() {
  const [q, setQ] = useState("");
  const [options, setOptions] = useState<Exercise[]>([]);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (q.length < 2) {
      setOptions([]);
      return;
    }
    const timer = setTimeout(async () => {
      const page = await api.get<ExercisePage>(`/exercises${query({ q, limit: 6 })}`);
      setOptions(page.data);
    }, 200);
    return () => clearTimeout(timer);
  }, [q]);

  return (
    <Panel title="How am I doing on…">
      <div className="flex flex-col gap-3">
        <Input
          label="Exercise"
          placeholder="bench press, squat…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        {options.length > 0 && (
          <ul className="flex flex-wrap gap-2">
            {options.map((option) => (
              <li key={option.id}>
                <button
                  onClick={async () => {
                    setBusy(true);
                    setAnalysis(
                      await api.post<Analysis>("/ai/analyze", { exercise_id: option.id }),
                    );
                    setQ("");
                    setOptions([]);
                    setBusy(false);
                  }}
                  className="min-h-tap rounded-full border border-surface-edge px-4 text-[13px] hover:border-accent"
                >
                  {option.name}
                </button>
              </li>
            ))}
          </ul>
        )}

        {busy && <Spinner label="Reading your log" />}

        {analysis && !busy && (
          <div className="flex flex-col gap-3">
            <h3 className="text-[16px] font-medium">
              {analysis.exercise_name}
              <span className="readout ml-2 text-[12px] text-ink-faint">
                {analysis.sessions} session{analysis.sessions === 1 ? "" : "s"}
              </span>
            </h3>

            {/* Sec 19 - observation and interpretation are visibly separated. */}
            <div>
              <p className="label">What the log says</p>
              <ul className="mt-1 flex flex-col gap-1">
                {analysis.observed.map((line) => (
                  <li key={line} className="text-[14px] leading-relaxed">
                    {line}
                  </li>
                ))}
              </ul>
            </div>

            {analysis.interpretation.length > 0 && (
              <div>
                <p className="label">What that might mean</p>
                <ul className="mt-1 flex flex-col gap-1">
                  {analysis.interpretation.map((line) => (
                    <li key={line} className="text-[14px] leading-relaxed text-ink-dim">
                      {line}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {analysis.suggestion && (
              <p className="rounded-lg border border-surface-edge bg-surface px-3 py-2 text-[14px] text-ink-dim">
                {analysis.suggestion}
              </p>
            )}

            {!analysis.enough_data && (
              <p className="text-[12px] text-ink-faint">
                Three sessions is the minimum before a trend means anything.
              </p>
            )}
          </div>
        )}
      </div>
    </Panel>
  );
}
