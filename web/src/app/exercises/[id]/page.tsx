"use client";

/**
 * One exercise, in full. SPECIFICATIONS.MD 6.2, 5.2.
 *
 * The media rule from 5.2 holds here: it is lazy, it never blocks the page,
 * and the exercise stays completely usable with no media at all - which is the
 * common case, since only part of the catalogue carries an image.
 */

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useSession } from "@/lib/session";
import { Button, Spinner } from "@/components/ui";
import { Panel } from "@/components/hud";
import { humanize } from "@/lib/units";
import type { Exercise, Plan, ExerciseProgress } from "@/lib/types";

export default function ExerciseDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { profile, loading } = useSession();

  const [exercise, setExercise] = useState<Exercise | null>(null);
  const [progress, setProgress] = useState<ExerciseProgress | null>(null);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [added, setAdded] = useState<string | null>(null);
  const [mediaFailed, setMediaFailed] = useState(false);
  const [shot, setShot] = useState(0);

  useEffect(() => {
    if (!loading && !profile) router.replace("/login");
  }, [loading, profile, router]);

  useEffect(() => {
    if (!profile) return;
    api
      .get<Exercise>(`/exercises/${id}`)
      .then(setExercise)
      .catch(() => router.replace("/exercises"));
    void api.get<ExerciseProgress>(`/progress/exercises/${id}`).then(setProgress);
    void api.get<Plan[]>("/workouts").then(setPlans);
  }, [profile, id, router]);

  if (loading || !profile || !exercise) return <Spinner />;

  const gallery = exercise.image_urls?.length
    ? exercise.image_urls
    : exercise.image_url
      ? [exercise.image_url]
      : [];
  const media = exercise.gif_url ?? gallery[shot] ?? exercise.image_url;
  const showMedia = Boolean(media) && !mediaFailed;
  const video = exercise.video_url;
  const youtube = `https://www.youtube.com/results?search_query=${encodeURIComponent(
    `${exercise.name} exercise form`,
  )}`;

  return (
    <section className="flex flex-col gap-4 py-5">
      <Link href="/exercises" className="label hover:text-accent">
        ← Exercises
      </Link>

      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="label">{humanize(exercise.body_part)}</p>
          <h1 className="text-[26px] font-semibold leading-tight">{exercise.name}</h1>
        </div>
        {!exercise.compatible && (
          <p className="text-[13px] text-warn">
            You are missing {exercise.missing_equipment.map(humanize).join(" + ")}
          </p>
        )}
      </header>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <Panel title="Demonstration">
          {video && (
            /* A clip answers "am I doing this right" in a way a still cannot. */
            <video
              src={video}
              controls
              loop
              muted
              playsInline
              preload="metadata"
              aria-label={`${exercise.name} demonstration video`}
              className="mb-3 max-h-[380px] w-full rounded-lg bg-surface"
            />
          )}
          {showMedia ? (
            /* eslint-disable-next-line @next/next/no-img-element */
            <img
              src={media!}
              alt={`${exercise.name} demonstration`}
              loading="lazy"
              onError={() => setMediaFailed(true)}
              className="max-h-[380px] w-full rounded-lg bg-surface object-contain"
            />
          ) : video ? null : (
            <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed border-surface-edge px-6 py-12 text-center">
              <p className="text-[14px] text-ink-dim">
                No image for this movement in the catalogue.
              </p>
              <p className="text-[12px] text-ink-faint">
                The written cues are the whole instruction — or watch someone do it.
              </p>
            </div>
          )}

          {gallery.length > 1 && (
            <div className="mt-3 flex flex-wrap gap-2">
              {gallery.map((url, index) => (
                <button
                  key={url}
                  onClick={() => {
                    setShot(index);
                    setMediaFailed(false);
                  }}
                  aria-label={`View angle ${index + 1} of ${gallery.length}`}
                  aria-pressed={shot === index}
                  className={`h-14 w-14 overflow-hidden rounded-lg border ${
                    shot === index ? "border-accent" : "border-surface-edge"
                  }`}
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={url} alt="" loading="lazy" className="h-full w-full object-contain" />
                </button>
              ))}
            </div>
          )}

          <div className="mt-3 flex flex-wrap gap-2">
            {exercise.video_url && (
              <a
                href={exercise.video_url}
                target="_blank"
                rel="noreferrer noopener"
                className="flex min-h-tap items-center rounded-lg border border-surface-edge px-4 text-[14px] hover:border-accent"
              >
                Watch the video
              </a>
            )}
            <a
              href={youtube}
              target="_blank"
              rel="noreferrer noopener"
              className="flex min-h-tap items-center rounded-lg border border-surface-edge px-4 text-[14px] hover:border-accent"
            >
              Find a demo on YouTube ↗
            </a>
          </div>
          {exercise.media_licence && (
            <p className="mt-2 text-[11px] text-ink-faint">
              Media: {exercise.media_licence}
            </p>
          )}
        </Panel>

        <div className="flex flex-col gap-4">
          <Panel title="How to do it">
            {exercise.instructions.length > 0 ? (
              <ol className="flex flex-col gap-2">
                {exercise.instructions.map((line, i) => (
                  <li key={i} className="flex gap-2 text-[14px] leading-relaxed">
                    {exercise.instructions.length > 1 && (
                      <span className="readout shrink-0 text-ink-faint">{i + 1}.</span>
                    )}
                    <span className="text-ink-dim">{line}</span>
                  </li>
                ))}
              </ol>
            ) : (
              <p className="text-[13px] text-ink-faint">
                No written instructions for this one yet.
              </p>
            )}
          </Panel>

          <Panel title="Details">
            <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-[13px]">
              <Fact label="Primary muscle" value={humanize(exercise.primary_muscle)} />
              <Fact
                label="Also works"
                value={
                  exercise.secondary_muscles.length
                    ? exercise.secondary_muscles.map(humanize).join(", ")
                    : "—"
                }
              />
              <Fact label="Equipment" value={exercise.equipment.map(humanize).join(", ")} />
              <Fact label="Difficulty" value={humanize(exercise.difficulty)} />
              <Fact label="Type" value={humanize(exercise.type)} />
              <Fact label="Recorded as" value={humanize(exercise.metric_type)} />
              <Fact label="Suggested rest" value={`${exercise.default_rest_seconds}s`} />
              {exercise.bodyweight_load_factor && (
                <Fact
                  label="Bodyweight load"
                  value={`${Math.round(parseFloat(exercise.bodyweight_load_factor) * 100)}%`}
                />
              )}
            </dl>
          </Panel>
        </div>
      </div>

      {progress && progress.points.length > 0 && (
        <Panel title="Your history with this">
          <div className="flex flex-wrap gap-4">
            <span className="readout text-[13px]">
              {progress.points.length} session
              {progress.points.length === 1 ? "" : "s"}
            </span>
            {progress.records
              .filter((r) => r.record_type === "heaviest_weight")
              .map((r) => (
                <span key={r.record_type} className="readout text-[13px] text-accent">
                  Best {parseFloat(r.value)} kg × {r.reps}
                </span>
              ))}
            <Link href="/progress" className="label hover:text-accent">
              full progress →
            </Link>
          </div>
        </Panel>
      )}

      {plans.length > 0 && (
        <Panel title="Add to a workout">
          <div className="flex flex-wrap gap-2">
            {plans.map((plan) => (
              <Button
                key={plan.id}
                variant="ghost"
                disabled={added === plan.id}
                onClick={async () => {
                  await api.post(`/workouts/${plan.id}/exercises`, {
                    exercise_id: exercise.id,
                    planned_sets: 3,
                    planned_reps_min: 8,
                    planned_reps_max: 12,
                  });
                  setAdded(plan.id);
                }}
              >
                {added === plan.id ? `Added to ${plan.name} ✓` : plan.name}
              </Button>
            ))}
          </div>
        </Panel>
      )}
    </section>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <dt className="label">{label}</dt>
      <dd className="mt-0.5 text-ink-dim">{value}</dd>
    </div>
  );
}
