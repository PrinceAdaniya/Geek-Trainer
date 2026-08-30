"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, query } from "@/lib/api";
import { useSession } from "@/lib/session";
import { Button, Empty, ErrorNote, Input, Select, Spinner } from "@/components/ui";
import { formatWeight, humanize } from "@/lib/units";
import { DAYS, type Exercise, type ExercisePage, type Plan } from "@/lib/types";

export default function PlanPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { profile, loading } = useSession();

  const [plan, setPlan] = useState<Plan | null>(null);
  const [picking, setPicking] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!loading && !profile) router.replace("/login");
  }, [loading, profile, router]);

  const load = useCallback(async () => {
    try {
      setPlan(await api.get<Plan>(`/workouts/${id}`));
    } catch {
      router.replace("/plan");
    }
  }, [id, router]);

  useEffect(() => {
    if (profile) void load();
  }, [profile, load]);

  if (loading || !profile || !plan) return <Spinner />;
  const unit = profile.settings.unit_preference;

  async function patch(body: Record<string, unknown>) {
    setError("");
    try {
      setPlan(await api.put<Plan>(`/workouts/${id}`, body));
    } catch {
      setError("Could not save that.");
    }
  }

  async function addExercise(exercise: Exercise) {
    await api.post(`/workouts/${id}/exercises`, {
      exercise_id: exercise.id,
      planned_sets: 3,
      planned_reps_min: 8,
      planned_reps_max: 12,
    });
    setPicking(false);
    await load();
  }

  async function move(index: number, direction: -1 | 1) {
    const ids = plan!.exercises.map((e) => e.id);
    const target = index + direction;
    if (target < 0 || target >= ids.length) return;
    [ids[index], ids[target]] = [ids[target], ids[index]];
    setPlan(await api.post<Plan>(`/workouts/${id}/reorder`, { exercise_ids: ids }));
  }

  async function removeExercise(weId: string) {
    await api.del(`/workouts/${id}/exercises/${weId}`);
    await load();
  }

  async function deletePlan() {
    await api.del(`/workouts/${id}`);
    router.push("/plan");
  }

  return (
    <section className="flex flex-col gap-6 py-6">
      <header className="flex flex-col gap-3">
        <input
          defaultValue={plan.name}
          aria-label="Workout name"
          onBlur={(e) => e.target.value !== plan.name && void patch({ name: e.target.value })}
          className="rounded-xl border border-transparent bg-transparent text-[22px] font-semibold hover:border-surface-edge focus:border-accent"
        />
        <div className="flex flex-wrap items-end gap-3">
          <Select
            label="Day"
            value={plan.day_of_week ?? ""}
            onChange={(e) =>
              void patch(
                e.target.value ? { day_of_week: e.target.value } : { clear_day: true },
              )
            }
          >
            <option value="">Not scheduled</option>
            {DAYS.map((day) => (
              <option key={day} value={day}>
                {humanize(day)}
              </option>
            ))}
          </Select>
        </div>
      </header>

      <ErrorNote>{error}</ErrorNote>

      {plan.exercises.length === 0 ? (
        <Empty
          title="No exercises yet."
          hint="Add the movements you want to do on this day. You can reorder them at any time."
          action={<Button onClick={() => setPicking(true)}>Add an exercise</Button>}
        />
      ) : (
        <ol className="flex flex-col gap-2">
          {plan.exercises.map((row, index) => (
            <li
              key={row.id}
              className="rounded-2xl border border-surface-edge bg-surface-raised p-4"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-[15px] font-medium">
                    {index + 1}. {row.exercise.name}
                  </p>
                  <p className="mt-0.5 text-[13px] text-ink-dim">
                    {humanize(row.exercise.primary_muscle)} ·{" "}
                    {row.exercise.equipment.map(humanize).join(", ")}
                  </p>
                  {!row.exercise.compatible && (
                    <p className="mt-1 text-[13px] text-warn">
                      Needs {row.exercise.missing_equipment.map(humanize).join(" + ")}
                    </p>
                  )}
                </div>
                <div className="flex shrink-0 gap-1">
                  <IconButton label="Move up" onClick={() => void move(index, -1)}>
                    ↑
                  </IconButton>
                  <IconButton label="Move down" onClick={() => void move(index, 1)}>
                    ↓
                  </IconButton>
                  <IconButton label="Remove" onClick={() => void removeExercise(row.id)}>
                    ×
                  </IconButton>
                </div>
              </div>

              <div className="mt-3 grid grid-cols-3 gap-2">
                <NumberField
                  label="Sets"
                  value={row.planned_sets}
                  onCommit={(v) =>
                    void api
                      .put(`/workouts/${id}/exercises/${row.id}`, { planned_sets: v })
                      .then(load)
                  }
                />
                <NumberField
                  label="Reps from"
                  value={row.planned_reps_min ?? ""}
                  onCommit={(v) =>
                    void api
                      .put(`/workouts/${id}/exercises/${row.id}`, { planned_reps_min: v })
                      .then(load)
                  }
                />
                <NumberField
                  label="to"
                  value={row.planned_reps_max ?? ""}
                  onCommit={(v) =>
                    void api
                      .put(`/workouts/${id}/exercises/${row.id}`, { planned_reps_max: v })
                      .then(load)
                  }
                />
              </div>
              {row.planned_weight_kg && (
                <p className="mt-2 text-[13px] text-ink-dim">
                  Planned {formatWeight(row.planned_weight_kg, unit)}
                </p>
              )}
            </li>
          ))}
        </ol>
      )}

      {plan.exercises.length > 0 && (
        <Button variant="ghost" onClick={() => setPicking(true)}>
          + Add an exercise
        </Button>
      )}

      {picking && <ExercisePicker onPick={addExercise} onClose={() => setPicking(false)} />}

      <div className="mt-6 border-t border-surface-edge pt-5">
        <Button variant="danger" onClick={() => void deletePlan()}>
          Delete this workout
        </Button>
        <p className="mt-2 text-[13px] text-ink-faint">
          Sessions you have already done from it are kept.
        </p>
      </div>
    </section>
  );
}

function IconButton({
  label,
  children,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { label: string }) {
  return (
    <button
      aria-label={label}
      title={label}
      className="min-h-tap min-w-tap rounded-lg border border-surface-edge text-ink-dim hover:border-ink-faint hover:text-ink"
      {...props}
    >
      {children}
    </button>
  );
}

function NumberField({
  label,
  value,
  onCommit,
}: {
  label: string;
  value: number | string;
  onCommit: (value: number) => void;
}) {
  return (
    <label className="flex flex-col gap-1 text-[12px] text-ink-faint">
      {label}
      <input
        type="number"
        inputMode="numeric"
        defaultValue={value}
        onBlur={(e) => {
          const parsed = Number(e.target.value);
          if (e.target.value !== String(value) && !Number.isNaN(parsed)) onCommit(parsed);
        }}
        className="min-h-tap rounded-lg border border-surface-edge bg-surface px-2.5 text-[16px] text-ink"
      />
    </label>
  );
}

function ExercisePicker({
  onPick,
  onClose,
}: {
  onPick: (exercise: Exercise) => void;
  onClose: () => void;
}) {
  const [q, setQ] = useState("");
  const [rows, setRows] = useState<Exercise[]>([]);

  useEffect(() => {
    const timer = setTimeout(async () => {
      const page = await api.get<ExercisePage>(`/exercises${query({ q, limit: 20 })}`);
      setRows(page.data);
    }, 200);
    return () => clearTimeout(timer);
  }, [q]);

  return (
    <div className="fixed inset-0 z-10 flex items-end justify-center bg-black/60 p-0 sm:items-center sm:p-4">
      <div className="flex max-h-[85dvh] w-full max-w-lg flex-col gap-3 rounded-t-3xl border border-surface-edge bg-surface-raised p-4 sm:rounded-3xl">
        <div className="flex items-center justify-between">
          <h2 className="text-[16px] font-medium">Add an exercise</h2>
          <button onClick={onClose} aria-label="Close" className="min-h-tap min-w-tap text-ink-dim">
            ×
          </button>
        </div>
        <Input label="Search" autoFocus value={q} onChange={(e) => setQ(e.target.value)} />
        <ul className="flex-1 overflow-y-auto">
          {rows.map((exercise) => (
            <li key={exercise.id}>
              <button
                onClick={() => onPick(exercise)}
                className="min-h-tap w-full rounded-xl px-3 py-3 text-left hover:bg-surface"
              >
                <span className="text-[15px]">{exercise.name}</span>
                <span className="ml-2 text-[13px] text-ink-faint">
                  {humanize(exercise.primary_muscle)}
                </span>
              </button>
            </li>
          ))}
          {rows.length === 0 && (
            <li className="px-3 py-6 text-[14px] text-ink-faint">Nothing matches that.</li>
          )}
        </ul>
      </div>
    </div>
  );
}
