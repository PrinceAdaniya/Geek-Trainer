"use client";

/**
 * Charts, in plain SVG.
 *
 * Rules applied throughout, from the visualization pass:
 *   - one axis, never two y-scales
 *   - a single series needs no legend; the title names it
 *   - thin marks, recessive grid, 2px lines, >=8px markers
 *   - gaps in training are drawn as gaps, never interpolated
 *   - a single data point is a point, not a trend line
 *   - a hover layer by default; values are readable without one
 */

import { useId, useState } from "react";

const GRID = "#23262d";
const AXIS_TEXT = "#5f6368";

export function BarSeries({
  data,
  unit,
  label,
  height = 160,
}: {
  data: { key: string; value: number; caption?: string }[];
  unit: string;
  label: string;
  height?: number;
}) {
  const [hover, setHover] = useState<number | null>(null);
  const max = Math.max(1, ...data.map((d) => d.value));
  const barWidth = 100 / Math.max(data.length, 1);

  if (data.every((d) => d.value === 0)) {
    return (
      <p className="py-8 text-center text-[13px] text-ink-faint">
        Nothing logged in this window yet.
      </p>
    );
  }

  return (
    <figure className="flex flex-col gap-2">
      <div className="relative" style={{ height }}>
        <svg
          viewBox={`0 0 100 ${height}`}
          preserveAspectRatio="none"
          className="h-full w-full"
          role="img"
          aria-label={`${label}, ${data.length} periods`}
        >
          {[0.25, 0.5, 0.75, 1].map((tick) => (
            <line
              key={tick}
              x1="0"
              x2="100"
              y1={height - tick * height}
              y2={height - tick * height}
              stroke={GRID}
              strokeWidth="0.5"
            />
          ))}
          {data.map((point, index) => {
            const barHeight = (point.value / max) * (height - 8);
            return (
              <rect
                key={point.key}
                x={index * barWidth + barWidth * 0.18}
                width={barWidth * 0.64}
                y={height - barHeight}
                height={Math.max(barHeight, point.value > 0 ? 2 : 0)}
                rx="1"
                fill={hover === index ? "#8ee9bd" : "#44916d"}
                onMouseEnter={() => setHover(index)}
                onMouseLeave={() => setHover(null)}
              />
            );
          })}
        </svg>
        {hover !== null && (
          <div
            className="pointer-events-none absolute -top-1 rounded-md border border-surface-edge bg-surface px-2 py-1 text-[12px]"
            style={{ left: `${Math.min(78, hover * barWidth)}%` }}
          >
            <span className="readout">
              {Math.round(data[hover].value).toLocaleString()} {unit}
            </span>
            <span className="ml-1.5 text-ink-faint">{data[hover].caption ?? data[hover].key}</span>
          </div>
        )}
      </div>
      <figcaption className="flex justify-between">
        <span className="readout text-[11px]" style={{ color: AXIS_TEXT }}>
          {data[0]?.caption ?? data[0]?.key}
        </span>
        <span className="readout text-[11px]" style={{ color: AXIS_TEXT }}>
          {data[data.length - 1]?.caption ?? data[data.length - 1]?.key}
        </span>
      </figcaption>
    </figure>
  );
}

export function LineSeries({
  points,
  unit,
  label,
  height = 180,
}: {
  points: { x: string; y: number }[];
  unit: string;
  label: string;
  height?: number;
}) {
  const clipId = useId();
  const [hover, setHover] = useState<number | null>(null);

  if (points.length === 0) {
    return (
      <p className="py-8 text-center text-[13px] text-ink-faint">
        No sessions with this exercise yet.
      </p>
    );
  }

  const values = points.map((p) => p.y);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || Math.max(max * 0.1, 1);
  const pad = span * 0.15;
  const lo = min - pad;
  const hi = max + pad;

  const x = (i: number) => (points.length === 1 ? 50 : (i / (points.length - 1)) * 100);
  const y = (v: number) => height - ((v - lo) / (hi - lo)) * height;

  // A single data point is a point, not a trend.
  const path =
    points.length > 1
      ? points.map((p, i) => `${i === 0 ? "M" : "L"} ${x(i)} ${y(p.y)}`).join(" ")
      : null;

  return (
    <figure className="flex flex-col gap-2">
      <div className="relative" style={{ height }}>
        <svg viewBox={`0 0 100 ${height}`} preserveAspectRatio="none" className="h-full w-full"
             role="img" aria-label={`${label} over ${points.length} sessions`}>
          <clipPath id={clipId}>
            <rect x="0" y="0" width="100" height={height} />
          </clipPath>
          {[0, 0.5, 1].map((tick) => (
            <line key={tick} x1="0" x2="100" y1={tick * height} y2={tick * height}
                  stroke={GRID} strokeWidth="0.5" />
          ))}
          {path && (
            <path
              d={path}
              fill="none"
              stroke="#57bb8d"
              strokeWidth="2"
              vectorEffect="non-scaling-stroke"
              clipPath={`url(#${clipId})`}
            />
          )}
          {points.map((point, index) => (
            <circle
              key={`${point.x}-${index}`}
              cx={x(index)}
              cy={y(point.y)}
              r={hover === index ? 3 : 2}
              fill={hover === index ? "#8ee9bd" : "#57bb8d"}
              vectorEffect="non-scaling-stroke"
              onMouseEnter={() => setHover(index)}
              onMouseLeave={() => setHover(null)}
            />
          ))}
        </svg>
        <span className="readout absolute right-0 top-0 text-[11px]" style={{ color: AXIS_TEXT }}>
          {Math.round(max)} {unit}
        </span>
        <span className="readout absolute bottom-0 right-0 text-[11px]" style={{ color: AXIS_TEXT }}>
          {Math.round(min)} {unit}
        </span>
        {hover !== null && (
          <div
            className="pointer-events-none absolute top-0 rounded-md border border-surface-edge bg-surface px-2 py-1 text-[12px]"
            style={{ left: `${Math.min(70, x(hover))}%` }}
          >
            <span className="readout">
              {Math.round(points[hover].y * 10) / 10} {unit}
            </span>
            <span className="ml-1.5 text-ink-faint">{points[hover].x}</span>
          </div>
        )}
      </div>
      <figcaption className="flex justify-between">
        <span className="readout text-[11px]" style={{ color: AXIS_TEXT }}>{points[0].x}</span>
        <span className="readout text-[11px]" style={{ color: AXIS_TEXT }}>
          {points[points.length - 1].x}
        </span>
      </figcaption>
    </figure>
  );
}

/** Horizontal bars for a ranked breakdown - the value is always labelled. */
export function RankedBars({
  rows,
  unit,
}: {
  rows: { label: string; value: number }[];
  unit: string;
}) {
  const max = Math.max(1, ...rows.map((r) => r.value));
  if (rows.length === 0) {
    return <p className="py-6 text-center text-[13px] text-ink-faint">Nothing yet.</p>;
  }
  return (
    <ul className="flex flex-col gap-2">
      {rows.map((row) => (
        <li key={row.label} className="flex items-center gap-3">
          <span className="w-24 shrink-0 truncate text-[13px] text-ink-dim">{row.label}</span>
          <span className="h-2.5 flex-1 overflow-hidden rounded-full bg-surface-edge">
            <span
              className="block h-full rounded-full bg-heat-3"
              style={{ width: `${Math.max(3, (row.value / max) * 100)}%` }}
            />
          </span>
          <span className="readout w-14 shrink-0 text-right text-[12px] text-ink-dim">
            {row.value} {unit}
          </span>
        </li>
      ))}
    </ul>
  );
}
