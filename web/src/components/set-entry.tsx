"use client";

/**
 * Set entry. SPECIFICATIONS.MD 11.1.
 *
 * The constraints, all of which are requirements rather than taste:
 *   - prefilled from the previous set, so a repeat is one tap
 *   - +/- steppers at the user's increment, with direct entry available
 *   - inputMode="decimal" so phones show a keypad, never a keyboard
 *   - no modal, no navigation, no network wait
 * Which fields appear at all is decided by the exercise's metric type (10.2).
 */

import { useEffect, useState } from "react";
import { Button } from "@/components/ui";
import type { MetricType, SetRecord, SetType, Unit } from "@/lib/types";
import { toDisplay } from "@/lib/units";

const INCREMENT: Record<string, number> = { kg: 2.5, lb: 5 };

export interface SetDraft {
  weight: string;
  reps: string;
  duration_seconds: string;
  distance_m: string;
  rir: string;
  failure: boolean;
  set_type: SetType;
}

export function fieldsFor(metric: MetricType) {
  return {
    weight: metric === "weight_reps" || metric === "weighted_bodyweight",
    reps: metric === "weight_reps" || metric === "bodyweight_reps" || metric === "weighted_bodyweight",
    duration: metric === "time" || metric === "time_distance",
    distance: metric === "distance" || metric === "time_distance",
  };
}

export function draftFromPrevious(
  metric: MetricType,
  previous: SetRecord | undefined,
  unit: Unit,
): SetDraft {
  const weight =
    previous?.weight_kg != null
      ? String(Math.round(toDisplay(parseFloat(previous.weight_kg), unit) * 100) / 100)
      : "";
  return {
    weight,
    reps: previous?.reps != null ? String(previous.reps) : "",
    duration_seconds: previous?.duration_seconds != null ? String(previous.duration_seconds) : "",
    distance_m: previous?.distance_m != null ? String(parseFloat(previous.distance_m)) : "",
    rir: previous?.rir != null ? String(previous.rir) : "",
    failure: false,
    set_type: previous?.set_type ?? "working",
  };
}

export function SetEntry({
  metric,
  unit,
  previous,
  busy,
  draftKey,
  onLog,
}: {
  metric: MetricType;
  unit: Unit;
  previous: SetRecord | undefined;
  busy: boolean;
  /** Identifies this exercise-in-this-session, so a half-typed set is kept. */
  draftKey: string;
  onLog: (draft: SetDraft) => void;
}) {
  const [draft, setDraft] = useState<SetDraft>(() => draftFromPrevious(metric, previous, unit));
  const fields = fieldsFor(metric);
  const step = INCREMENT[unit] ?? 2.5;
  const storageKey = `gt:draft:${draftKey}`;

  // A set typed but not yet logged survives a refresh, a phone locking, or a
  // stray back-swipe mid-workout. Storage can throw in a private window, so
  // both the read and the write are guarded and the UI works without it.
  useEffect(() => {
    let saved: SetDraft | null = null;
    try {
      const raw = localStorage.getItem(storageKey);
      if (raw) saved = JSON.parse(raw) as SetDraft;
    } catch {
      saved = null;
    }
    setDraft(saved ?? draftFromPrevious(metric, previous, unit));
  }, [metric, previous, unit, storageKey]);

  useEffect(() => {
    try {
      localStorage.setItem(storageKey, JSON.stringify(draft));
    } catch {
      /* nothing to do - the draft simply will not survive a reload */
    }
  }, [draft, storageKey]);

  function set<K extends keyof SetDraft>(key: K, value: SetDraft[K]) {
    setDraft((d) => ({ ...d, [key]: value }));
  }

  function nudge(key: "weight" | "reps", by: number) {
    const current = parseFloat(draft[key] || "0");
    const next = Math.max(key === "reps" ? 0 : -500, current + by);
    set(key, String(Math.round(next * 100) / 100));
  }

  return (
    <div className="flex flex-col gap-3 rounded-xl border border-surface-edge bg-surface p-3">
      <div className="flex flex-wrap gap-3">
        {fields.weight && (
          <Stepper
            label={`Weight (${unit})`}
            value={draft.weight}
            onChange={(v) => set("weight", v)}
            onNudge={(by) => nudge("weight", by * step)}
          />
        )}
        {fields.reps && (
          <Stepper
            label="Reps"
            value={draft.reps}
            onChange={(v) => set("reps", v)}
            onNudge={(by) => nudge("reps", by)}
            integer
          />
        )}
        {fields.duration && (
          <Field
            label="Seconds"
            value={draft.duration_seconds}
            onChange={(v) => set("duration_seconds", v)}
          />
        )}
        {fields.distance && (
          <Field
            label="Metres"
            value={draft.distance_m}
            onChange={(v) => set("distance_m", v)}
          />
        )}
        <Field
          label="RIR"
          value={draft.rir}
          onChange={(v) => set("rir", v)}
          width="w-20"
          hint="reps left"
        />
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <select
          aria-label="Set type"
          value={draft.set_type}
          onChange={(e) => set("set_type", e.target.value as SetType)}
          className="min-h-tap rounded-lg border border-surface-edge bg-surface-raised px-3 text-[14px]"
        >
          <option value="working">Working</option>
          <option value="warmup">Warm-up</option>
          <option value="drop_set">Drop set</option>
          <option value="rest_pause">Rest-pause</option>
          <option value="amrap">AMRAP</option>
          <option value="backoff">Back-off</option>
          <option value="other">Other</option>
        </select>

        <label className="flex min-h-tap items-center gap-2 rounded-lg border border-surface-edge bg-surface-raised px-3 text-[14px]">
          <input
            type="checkbox"
            checked={draft.failure}
            onChange={(e) => set("failure", e.target.checked)}
            className="h-4 w-4 accent-accent"
          />
          To failure
        </label>

        <Button
          className="ml-auto px-6"
          disabled={busy}
          onClick={() => {
            onLog(draft);
            try {
              localStorage.removeItem(storageKey);
            } catch {
              /* nothing to clear */
            }
          }}
        >
          {busy ? "Saving…" : "Log set"}
        </Button>
      </div>

      {draft.set_type === "warmup" && (
        /* Sec 10.3 - the exclusion is stated wherever it applies. */
        <p className="text-[12px] text-ink-faint">
          Warm-ups are kept in the log but left out of volume, charts and records.
        </p>
      )}
    </div>
  );
}

function Stepper({
  label,
  value,
  onChange,
  onNudge,
  integer,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  onNudge: (by: number) => void;
  integer?: boolean;
}) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-[12px] text-ink-faint">{label}</span>
      <div className="flex items-stretch">
        <button
          aria-label={`Decrease ${label}`}
          onClick={() => onNudge(-1)}
          className="min-h-tap min-w-tap rounded-l-lg border border-surface-edge bg-surface-raised text-[18px] text-ink-dim"
        >
          −
        </button>
        <input
          aria-label={label}
          inputMode={integer ? "numeric" : "decimal"}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="min-h-tap w-20 border-y border-surface-edge bg-surface-raised text-center text-[18px] tabular-nums"
        />
        <button
          aria-label={`Increase ${label}`}
          onClick={() => onNudge(1)}
          className="min-h-tap min-w-tap rounded-r-lg border border-surface-edge bg-surface-raised text-[18px] text-ink-dim"
        >
          +
        </button>
      </div>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  width = "w-24",
  hint,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  width?: string;
  hint?: string;
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-[12px] text-ink-faint">
        {label}
        {hint && <span className="ml-1 opacity-60">({hint})</span>}
      </span>
      <input
        inputMode="decimal"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={`min-h-tap rounded-lg border border-surface-edge bg-surface-raised px-2 text-center text-[18px] tabular-nums ${width}`}
      />
    </label>
  );
}
