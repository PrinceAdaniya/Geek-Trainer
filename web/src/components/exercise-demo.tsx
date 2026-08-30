"use client";

/**
 * The "how do I do this" panel, inside the logging screen.
 *
 * SPECIFICATIONS.MD 9 requires that instructions and media be viewable during
 * a session - looking up a movement is exactly when you are mid-workout, not
 * when you are browsing. 5.2 requires the media be lazy and never block, and
 * that every exercise stay usable with no media at all.
 */

import { useState } from "react";
import { humanize } from "@/lib/units";
import type { Exercise } from "@/lib/types";

export function ExerciseDemo({ exercise }: { exercise: Exercise }) {
  const [open, setOpen] = useState(false);
  const [mediaFailed, setMediaFailed] = useState(false);

  const media = exercise.gif_url ?? exercise.image_url;
  const hasMedia = Boolean(media) && !mediaFailed;

  return (
    <div className="rounded-xl border border-surface-edge bg-surface">
      <button
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex min-h-tap w-full items-center justify-between gap-2 px-3 text-left"
      >
        <span className="label">How to · {humanize(exercise.primary_muscle)}</span>
        <span className="text-ink-faint">{open ? "▾" : "▸"}</span>
      </button>

      {open && (
        <div className="flex flex-col gap-3 border-t border-surface-edge p-3">
          {exercise.video_url && (
            <video
              src={exercise.video_url}
              controls
              loop
              muted
              playsInline
              preload="none"
              aria-label={`${exercise.name} demonstration video`}
              className="max-h-64 w-full rounded-lg bg-surface-raised"
            />
          )}
          {hasMedia ? (
            /* eslint-disable-next-line @next/next/no-img-element */
            <img
              src={media!}
              alt={`${exercise.name} demonstration`}
              loading="lazy"
              onError={() => setMediaFailed(true)}
              className="max-h-64 w-full rounded-lg bg-surface-raised object-contain"
            />
          ) : exercise.video_url ? null : (
            <div className="flex items-center justify-center rounded-lg border border-dashed border-surface-edge px-4 py-6 text-center">
              <p className="text-[12px] leading-relaxed text-ink-faint">
                No demonstration for this movement yet.
                <br />
                The written cue below is the whole instruction.
              </p>
            </div>
          )}

          {exercise.instructions.length > 0 ? (
            <ol className="flex flex-col gap-1.5">
              {exercise.instructions.map((line, i) => (
                <li key={i} className="flex gap-2 text-[14px] leading-relaxed text-ink-dim">
                  {exercise.instructions.length > 1 && (
                    <span className="readout shrink-0 text-ink-faint">{i + 1}.</span>
                  )}
                  <span>{line}</span>
                </li>
              ))}
            </ol>
          ) : (
            <p className="text-[13px] text-ink-faint">No instructions recorded.</p>
          )}

          <dl className="grid grid-cols-2 gap-x-4 gap-y-2 border-t border-surface-edge pt-3 text-[13px] sm:grid-cols-4">
            <Fact label="Equipment" value={exercise.equipment.map(humanize).join(", ")} />
            <Fact
              label="Also works"
              value={
                exercise.secondary_muscles.length
                  ? exercise.secondary_muscles.map(humanize).join(", ")
                  : "—"
              }
            />
            <Fact label="Difficulty" value={humanize(exercise.difficulty)} />
            <Fact label="Recorded as" value={humanize(exercise.metric_type)} />
          </dl>

          {exercise.video_url && (
            <a
              href={exercise.video_url}
              target="_blank"
              rel="noreferrer noopener"
              className="min-h-tap text-[13px] text-accent underline underline-offset-2"
            >
              Watch a full video →
            </a>
          )}
        </div>
      )}
    </div>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <dt className="label">{label}</dt>
      <dd className="mt-0.5 truncate text-ink-dim" title={value}>
        {value}
      </dd>
    </div>
  );
}
