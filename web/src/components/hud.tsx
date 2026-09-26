"use client";

/**
 * HUD pieces: the readouts on the dashboard.
 *
 * Two rules from the visualization pass hold everywhere here:
 *   - The training heatmap is a MAGNITUDE encoding, so it uses one hue on a
 *     validated sequential ramp - never a rainbow.
 *   - The rank colour never carries meaning alone. The level number and rank
 *     name are always rendered beside it, because a ten-hue ladder cannot pass
 *     a colourblind-separation check and this one does not try to.
 */

import { useEffect, useMemo, useState } from "react";

export function Panel({
  title,
  right,
  className = "",
  children,
}: {
  title?: string;
  right?: React.ReactNode;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <section className={`panel p-4 ${className}`}>
      {(title || right) && (
        <div className="mb-3 flex items-baseline justify-between gap-3">
          {title && <h2 className="label">{title}</h2>}
          {right}
        </div>
      )}
      {children}
    </section>
  );
}

/** A single number that matters. No chart - the form heuristic says a lone
 *  magnitude is a stat tile, not a plot. */
export function Stat({
  label,
  value,
  unit,
  hint,
  tone = "default",
}: {
  label: string;
  value: string | number;
  unit?: string;
  hint?: string;
  tone?: "default" | "accent" | "warn";
}) {
  const color =
    tone === "accent" ? "text-accent" : tone === "warn" ? "text-warn" : "text-ink";
  return (
    <div className="panel flex flex-col justify-between gap-2 p-4">
      <span className="label">{label}</span>
      <div className="flex items-baseline gap-1.5">
        <span className={`readout text-[28px] font-semibold leading-none ${color}`}>
          {value}
        </span>
        {unit && <span className="readout text-[13px] text-ink-faint">{unit}</span>}
      </div>
      {hint && <span className="text-[12px] leading-tight text-ink-dim">{hint}</span>}
    </div>
  );
}

/** Progress toward the next rank. Labelled at both ends - never a bare bar. */
export function ChargeMeter({
  progress,
  color,
  fromLabel,
  toLabel,
}: {
  progress: number;
  color: string;
  fromLabel: string;
  toLabel: string;
}) {
  const pct = Math.round(progress * 100);
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex justify-between">
        <span className="label">{fromLabel}</span>
        <span className="label">{toLabel}</span>
      </div>
      <div
        className="relative h-2.5 overflow-hidden rounded-full bg-surface-edge"
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`Progress to ${toLabel}`}
      >
        <div
          className="h-full rounded-full transition-[width] duration-700"
          style={{ width: `${Math.max(2, pct)}%`, backgroundColor: color }}
        />
      </div>
      <span className="readout text-[11px] text-ink-faint">{pct}% of the way</span>
    </div>
  );
}

/**
 * Training-day heatmap: twelve weeks, one cell per day.
 * Sequential single hue - the cell answers "did you train", not "which kind".
 */
export function TrainingHeatmap({
  activeDays,
  ramp,
  weeks = 12,
}: {
  activeDays: string[];
  ramp: string[];
  weeks?: number;
}) {
  const cells = useMemo(() => {
    const active = new Set(activeDays);
    const today = new Date();
    const days: { date: string; active: boolean; weight: number }[] = [];
    for (let i = weeks * 7 - 1; i >= 0; i--) {
      const day = new Date(today);
      day.setDate(today.getDate() - i);
      const iso = day.toISOString().slice(0, 10);
      // Recent activity reads brighter, so the last fortnight stands out from
      // a burst three months ago.
      const recency = 1 - i / (weeks * 7);
      days.push({
        date: iso,
        active: active.has(iso),
        weight: active.has(iso) ? Math.min(4, 1 + Math.floor(recency * 4)) : 0,
      });
    }
    return days;
  }, [activeDays, weeks]);

  const trained = cells.filter((c) => c.active).length;

  return (
    <div className="flex flex-col gap-2">
      <div
        className="grid grid-flow-col gap-[3px]"
        style={{ gridTemplateRows: "repeat(7, minmax(0, 1fr))" }}
        role="img"
        aria-label={`Trained on ${trained} of the last ${cells.length} days`}
      >
        {cells.map((cell) => (
          <div
            key={cell.date}
            title={`${cell.date}${cell.active ? " — trained" : ""}`}
            className="aspect-square w-full rounded-[2px]"
            style={{ backgroundColor: cell.active ? ramp[cell.weight] : "#231e42" }}
          />
        ))}
      </div>
      <div className="flex items-center justify-between">
        <span className="readout text-[11px] text-ink-faint">
          {trained} / {cells.length} days
        </span>
        <div className="flex items-center gap-1">
          <span className="label">less</span>
          {["#231e42", ...ramp].map((color) => (
            <span
              key={color}
              className="h-2.5 w-2.5 rounded-[2px]"
              style={{ backgroundColor: color }}
            />
          ))}
          <span className="label">more</span>
        </div>
      </div>
    </div>
  );
}

/** The rank badge. Number and name always present beside the colour. */
export function PowerBadge({
  level,
  name,
  color,
  streak,
  glow = true,
}: {
  level: number;
  name: string;
  color: string;
  streak: number;
  glow?: boolean;
}) {
  return (
    <div className="flex items-center gap-4">
      <div className="relative flex h-20 w-20 shrink-0 items-center justify-center">
        {glow && streak > 0 && (
          <span
            className="absolute inset-0 animate-aura rounded-full blur-xl"
            style={{ backgroundColor: color, opacity: 0.5 }}
            aria-hidden
          />
        )}
        <span
          className="relative flex h-16 w-16 items-center justify-center rounded-full border-2"
          style={{ borderColor: color }}
        >
          <span className="readout text-[24px] font-bold" style={{ color }}>
            {level}
          </span>
        </span>
      </div>
      <div className="min-w-0">
        <p className="label">Streak level</p>
        <p className="truncate text-[20px] font-semibold" style={{ color }}>
          {name}
        </p>
        <p className="readout text-[13px] text-ink-dim">
          {streak} day streak
        </p>
      </div>
    </div>
  );
}

/**
 * The power-up. Fires once, when the rank actually goes up.
 *
 * The last rank seen is remembered per browser, so the animation marks a real
 * transition rather than replaying on every visit. Reading it can throw in a
 * private window, so both sides are guarded.
 */
export function PowerUp({
  level,
  name,
  color,
  blurb,
}: {
  level: number;
  name: string;
  color: string;
  blurb: string;
}) {
  const [show, setShow] = useState(false);

  useEffect(() => {
    let previous: number | null = null;
    try {
      const stored = localStorage.getItem("gt:rank");
      previous = stored === null ? null : Number(stored);
    } catch {
      return;
    }
    if (previous !== null && level > previous) setShow(true);
    try {
      localStorage.setItem("gt:rank", String(level));
    } catch {
      /* private window - the animation simply will not repeat */
    }
  }, [level]);

  useEffect(() => {
    if (!show) return;
    const timer = setTimeout(() => setShow(false), 4200);
    return () => clearTimeout(timer);
  }, [show]);

  if (!show) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 px-6"
      role="alertdialog"
      aria-label={`Streak level increased to ${name}`}
      onClick={() => setShow(false)}
    >
      <div className="animate-chargeIn flex flex-col items-center gap-4 text-center">
        <div className="relative flex h-40 w-40 items-center justify-center">
          <span
            className="absolute inset-0 animate-aura rounded-full blur-3xl"
            style={{ backgroundColor: color, opacity: 0.7 }}
            aria-hidden
          />
          <span
            className="absolute inset-4 rounded-full border-2"
            style={{ borderColor: color }}
            aria-hidden
          />
          <span className="readout relative text-[52px] font-bold" style={{ color }}>
            {level}
          </span>
        </div>
        <p className="label" style={{ color }}>New streak level</p>
        <p className="text-[30px] font-semibold" style={{ color }}>
          {name}
        </p>
        <p className="max-w-xs text-[14px] text-ink-dim">{blurb}</p>
        <p className="label mt-2">tap to dismiss</p>
      </div>
    </div>
  );
}

/** The whole ladder, so the next rung is visible rather than a surprise. */
export function RankLadder({
  ladder,
  currentLevel,
  streak,
}: {
  ladder: { level: number; name: string; threshold: number; color: string }[];
  currentLevel: number;
  streak: number;
}) {
  return (
    <ol className="flex flex-col gap-1">
      {ladder.map((rank) => {
        const reached = rank.level <= currentLevel;
        const isCurrent = rank.level === currentLevel;
        return (
          <li
            key={rank.level}
            className={`flex items-center gap-3 rounded px-2 py-1.5 ${
              isCurrent ? "bg-surface-edge/60" : ""
            }`}
          >
            <span
              className="readout w-5 text-[12px]"
              style={{ color: reached ? rank.color : "#8580ab" }}
            >
              {rank.level}
            </span>
            <span
              className={`flex-1 text-[13px] ${reached ? "text-ink" : "text-ink-faint"}`}
            >
              {rank.name}
            </span>
            <span className="readout text-[11px] text-ink-faint">
              {rank.threshold}d
            </span>
            {isCurrent && (
              <span className="label" style={{ color: rank.color }}>
                you
              </span>
            )}
          </li>
        );
      })}
    </ol>
  );
}
