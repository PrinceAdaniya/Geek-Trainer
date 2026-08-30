"use client";

/**
 * The active session. SPECIFICATIONS.MD Sec 10, Sec 11.
 *
 * This is the screen the product lives or dies on: it has to be operable
 * one-handed, mid-set, without reading anything. Nothing here may block on the
 * network before showing the user their set.
 */

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ApiError, api, query } from "@/lib/api";
import { useSession } from "@/lib/session";
import { Button, Empty, ErrorNote, Input, Spinner } from "@/components/ui";
import { SetEntry, type SetDraft } from "@/components/set-entry";
import { formatClock, useElapsed, useRestTimer, useWakeLock, uuid7 } from "@/lib/hooks";
import { cacheActiveSession, drain, enqueue, pending, readCachedSession } from "@/lib/offline";
import { formatWeight, humanize } from "@/lib/units";
import type {
  Exercise,
  ExercisePage,
  SessionExercise,
  SetRecord,
  WorkoutSession,
} from "@/lib/types";

export default function SessionPage() {
  const router = useRouter();
  const { profile, loading } = useSession();

  const [session, setSession] = useState<WorkoutSession | null>(null);
  const [checked, setChecked] = useState(false);
  const [openId, setOpenId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [picking, setPicking] = useState(false);
  const [queued, setQueued] = useState(0);
  const [offline, setOffline] = useState(false);

  const rest = useRestTimer();
  const elapsed = useElapsed(session?.start_time ?? null);
  useWakeLock(session?.status === "in_progress");

  useEffect(() => {
    if (!loading && !profile) router.replace("/login");
  }, [loading, profile, router]);

  const load = useCallback(async () => {
    // Sec 12.1 - the session must open with no network. The cache answers
    // first; the server corrects it if it can be reached.
    let active: WorkoutSession | null = null;
    try {
      active = await api.get<WorkoutSession | null>("/sessions/active");
      setOffline(false);
      void cacheActiveSession(active);
    } catch {
      active = await readCachedSession();
      setOffline(true);
    }
    setSession(active);
    setChecked(true);
    setQueued(await pending());
    if (active && !openId) {
      const next = active.exercises.find((e) => !e.skipped);
      setOpenId(next?.id ?? null);
    }
  }, [openId]);

  useEffect(() => {
    if (profile) void load();
  }, [profile, load]);

  // Drain the outbox whenever the connection comes back, and on a slow poll
  // so a flaky link settles without the user doing anything.
  useEffect(() => {
    if (!profile) return;
    let cancelled = false;

    async function flush() {
      try {
        const result = await drain();
        if (cancelled || !result) return;
        setOffline(false);
        setQueued(await pending());
        if (result.rejected.length > 0) {
          setError(
            `${result.rejected.length} change(s) could not be saved: ` +
              result.rejected.map((r) => r.message).join(" "),
          );
        }
        if (result.sent > 0) await load();
      } catch {
        if (!cancelled) setOffline(true);
      }
    }

    void flush();
    const onOnline = () => void flush();
    window.addEventListener("online", onOnline);
    const timer = setInterval(flush, 20000);
    return () => {
      cancelled = true;
      window.removeEventListener("online", onOnline);
      clearInterval(timer);
    };
  }, [profile, load]);

  if (loading || !profile || !checked) return <Spinner />;
  const unit = profile.settings.unit_preference;

  if (!session) {
    return (
      <section className="py-8">
        <Empty
          title="No workout in progress."
          hint="Start one from your week, or begin an empty session and add exercises as you go."
          action={
            <div className="flex gap-2">
              <Link
                href="/plan"
                className="flex min-h-tap items-center rounded-xl bg-accent px-5 font-semibold text-surface"
              >
                Go to my week
              </Link>
              <Button variant="ghost" onClick={() => void startAdHoc()}>
                Empty session
              </Button>
            </div>
          }
        />
      </section>
    );
  }

  async function startAdHoc() {
    try {
      const created = await api.post<WorkoutSession>("/sessions", {
        id: uuid7(),
        name: "Workout",
      });
      setSession(created);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not start.");
    }
  }

  async function logSet(exercise: SessionExercise, draft: SetDraft) {
    setBusy(true);
    setError("");
    const body: Record<string, unknown> = {
      id: uuid7(),
      set_type: draft.set_type,
      failure: draft.failure,
      // Sec 11.3 - the rest actually taken, whether or not the timer was used.
      rest_seconds: rest.running ? rest.elapsed : undefined,
    };
    if (draft.weight !== "") body.weight = Number(draft.weight);
    if (draft.reps !== "") body.reps = Number(draft.reps);
    if (draft.duration_seconds !== "") body.duration_seconds = Number(draft.duration_seconds);
    if (draft.distance_m !== "") body.distance_m = Number(draft.distance_m);
    if (draft.rir !== "") body.rir = Number(draft.rir);

    // Optimistic: the set appears now, and the queue is what guarantees it
    // eventually reaches the server (Sec 12.2).
    const setId = body.id as string;
    await enqueue("set.upsert", {
      ...body,
      session_id: session!.id,
      session_exercise_id: exercise.id,
    }, uuid7());
    setQueued(await pending());

    try {
      await api.post(`/sessions/${session!.id}/exercises/${exercise.id}/sets`, body);
      // It landed directly, so the queued copy is redundant; the drain will
      // find the set already there and treat it as a duplicate either way.
      await load();
      setOffline(false);
    } catch (err) {
      if (err instanceof ApiError && err.status === 0) {
        // Offline. The set is queued; show it locally rather than an error.
        setOffline(true);
        setSession((current) =>
          current
            ? {
                ...current,
                exercises: current.exercises.map((e) =>
                  e.id === exercise.id
                    ? {
                        ...e,
                        sets: [
                          ...e.sets,
                          {
                            id: setId,
                            set_number: e.sets.length + 1,
                            weight_kg: body.weight != null ? String(body.weight) : null,
                            reps: (body.reps as number) ?? null,
                            duration_seconds: (body.duration_seconds as number) ?? null,
                            distance_m: body.distance_m != null ? String(body.distance_m) : null,
                            rir: (body.rir as number) ?? null,
                            rpe: null,
                            failure: Boolean(body.failure),
                            set_type: draft.set_type,
                            rest_seconds: (body.rest_seconds as number) ?? null,
                            notes: null,
                            performed_at: new Date().toISOString(),
                          },
                        ],
                      }
                    : e,
                ),
              }
            : current,
        );
      } else {
        setError(err instanceof ApiError ? err.message : "Could not save that set.");
      }
    } finally {
      rest.start(
        exercise.exercise.default_rest_seconds || profile!.settings.default_rest_seconds,
      );
      setBusy(false);
    }
  }

  async function removeSet(setId: string) {
    await api.del(`/sessions/${session!.id}/sets/${setId}`);
    await load();
  }

  async function addExercise(exercise: Exercise) {
    const updated = await api.post<WorkoutSession>(`/sessions/${session!.id}/exercises`, {
      id: uuid7(),
      exercise_id: exercise.id,
    });
    setSession(updated);
    setPicking(false);
    setOpenId(updated.exercises[updated.exercises.length - 1]?.id ?? null);
  }

  async function finish() {
    await api.post(`/sessions/${session!.id}/finish`);
    router.push(`/history/${session!.id}`);
  }

  async function cancel() {
    if (!confirm("Discard this session? Sets you have logged are kept in history as cancelled.")) return;
    await api.post(`/sessions/${session!.id}/cancel`);
    setSession(null);
  }

  const totalSets = session.exercises.reduce((n, e) => n + e.sets.length, 0);

  return (
    <section className="flex flex-col gap-4 py-4">
      <header className="sticky top-[57px] z-10 -mx-4 flex items-center justify-between gap-3 border-b border-surface-edge bg-surface/95 px-4 py-3 backdrop-blur sm:-mx-6 sm:px-6">
        <div className="min-w-0">
          <h1 className="truncate text-[17px] font-semibold">{session.name}</h1>
          <p className="readout text-[13px] text-ink-dim">
            {formatClock(elapsed)} · {totalSets} set{totalSets === 1 ? "" : "s"}
          </p>
        </div>
        {(queued > 0 || offline) && (
          /* Sec 12.2 - one honest indicator. A pending change is never shown
             as saved, and a failed sync never looks like data loss. */
          <span
            className={`readout rounded-lg border px-2.5 py-1.5 text-[12px] ${
              offline ? "border-warn/40 text-warn" : "border-surface-edge text-ink-dim"
            }`}
            aria-live="polite"
          >
            {queued > 0 ? `${queued} pending` : "offline"}
          </span>
        )}
        {rest.running && (
          <button
            onClick={rest.stop}
            className={`min-h-tap rounded-xl px-4 tabular-nums ${
              rest.done ? "bg-accent text-surface" : "border border-surface-edge text-ink"
            }`}
            aria-live="polite"
          >
            {rest.done ? "Rest done" : `Rest ${formatClock(rest.remaining)}`}
          </button>
        )}
      </header>

      <ErrorNote>{error}</ErrorNote>

      {session.exercises.length === 0 ? (
        <Empty
          title="Nothing added yet."
          hint="Add the first exercise and start logging."
          action={<Button onClick={() => setPicking(true)}>Add an exercise</Button>}
        />
      ) : (
        <ol className="flex flex-col gap-2">
          {session.exercises.map((exercise, index) => (
            <li
              key={exercise.id}
              className={`panel ${
                openId === exercise.id ? "!border-accent/40" : ""
              } ${exercise.skipped ? "opacity-50" : ""}`}
            >
              <button
                onClick={() => setOpenId(openId === exercise.id ? null : exercise.id)}
                aria-expanded={openId === exercise.id}
                className="flex w-full items-center justify-between gap-3 p-4 text-left"
              >
                <div className="min-w-0">
                  <p className="text-[15px] font-medium">
                    {index + 1}. {exercise.exercise.name}
                  </p>
                  <p className="mt-0.5 text-[13px] text-ink-dim">
                    {exercise.sets.length}
                    {exercise.planned_sets ? ` of ${exercise.planned_sets}` : ""} set
                    {exercise.sets.length === 1 ? "" : "s"}
                    {exercise.planned_reps_min
                      ? ` · ${exercise.planned_reps_min}–${exercise.planned_reps_max} reps`
                      : ""}
                  </p>
                </div>
                <span className="text-ink-faint">{openId === exercise.id ? "▾" : "▸"}</span>
              </button>

              {openId === exercise.id && (
                <div className="flex flex-col gap-3 border-t border-surface-edge p-4">
                  {exercise.last_performance && (
                    /* Sec 11.2 - always visible while logging. */
                    <div className="rounded-xl bg-surface px-3 py-2">
                      <p className="text-[12px] uppercase tracking-wide text-ink-faint">
                        Last session · {exercise.last_performance.date}
                      </p>
                      <p className="mt-1 text-[14px] text-ink-dim">
                        {exercise.last_performance.sets
                          .map((s) => describeSet(s, unit))
                          .join("   ")}
                      </p>
                    </div>
                  )}

                  {exercise.sets.length > 0 && (
                    <table className="w-full text-[14px]">
                      <thead>
                        <tr className="text-left text-[12px] uppercase tracking-wide text-ink-faint">
                          <th className="py-1 font-normal">Set</th>
                          <th className="py-1 font-normal">Done</th>
                          <th className="py-1 font-normal">RIR</th>
                          <th className="py-1 font-normal" />
                        </tr>
                      </thead>
                      <tbody>
                        {exercise.sets.map((row) => (
                          <tr key={row.id} className="border-t border-surface-edge/60">
                            <td className="py-2 tabular-nums text-ink-dim">
                              {row.set_number}
                              {row.set_type !== "working" && (
                                <span className="ml-1 text-[11px] text-ink-faint">
                                  {row.set_type === "warmup" ? "W" : row.set_type[0].toUpperCase()}
                                </span>
                              )}
                            </td>
                            <td className="py-2 tabular-nums">{describeSet(row, unit)}</td>
                            <td className="py-2 tabular-nums text-ink-dim">
                              {row.failure ? "F" : (row.rir ?? "—")}
                            </td>
                            <td className="py-2 text-right">
                              <button
                                onClick={() => void removeSet(row.id)}
                                aria-label={`Delete set ${row.set_number}`}
                                className="min-h-tap min-w-tap text-ink-faint hover:text-bad"
                              >
                                ×
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}

                  <SetEntry
                    metric={exercise.exercise.metric_type as never}
                    unit={unit}
                    previous={exercise.sets[exercise.sets.length - 1]}
                    busy={busy}
                    draftKey={`${session.id}:${exercise.id}`}
                    onLog={(draft) => void logSet(exercise, draft)}
                  />

                  <div className="flex gap-2">
                    <Button
                      variant="ghost"
                      onClick={() =>
                        void api
                          .patch(`/sessions/${session.id}/exercises/${exercise.id}`, {
                            skipped: !exercise.skipped,
                          })
                          .then(load)
                      }
                    >
                      {exercise.skipped ? "Un-skip" : "Skip this"}
                    </Button>
                  </div>
                </div>
              )}
            </li>
          ))}
        </ol>
      )}

      {session.exercises.length > 0 && (
        <Button variant="ghost" onClick={() => setPicking(true)}>
          + Add an exercise
        </Button>
      )}

      {picking && <Picker onPick={addExercise} onClose={() => setPicking(false)} />}

      <div className="mt-4 flex flex-col gap-2 border-t border-surface-edge pt-4">
        <Button onClick={() => void finish()}>Finish session</Button>
        <Button variant="danger" onClick={() => void cancel()}>
          Discard
        </Button>
      </div>
    </section>
  );
}

function describeSet(row: SetRecord, unit: "kg" | "lb"): string {
  if (row.duration_seconds != null && row.distance_m != null)
    return `${formatClock(row.duration_seconds)} / ${Math.round(parseFloat(row.distance_m))} m`;
  if (row.duration_seconds != null) return formatClock(row.duration_seconds);
  if (row.distance_m != null) return `${Math.round(parseFloat(row.distance_m))} m`;
  if (row.weight_kg != null) return `${formatWeight(row.weight_kg, unit)} × ${row.reps}`;
  return `${row.reps} reps`;
}

function Picker({
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
    <div className="fixed inset-0 z-20 flex items-end justify-center bg-black/60 sm:items-center sm:p-4">
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
        </ul>
      </div>
    </div>
  );
}
