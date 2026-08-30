"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, query } from "@/lib/api";
import { useSession } from "@/lib/session";
import Link from "next/link";
import { Button, Chip, Empty, Input, Select, Spinner } from "@/components/ui";
import { humanize } from "@/lib/units";
import type { Exercise, ExercisePage, Vocabulary } from "@/lib/types";

export default function ExercisesPage() {
  const router = useRouter();
  const { profile, loading } = useSession();

  const [vocab, setVocab] = useState<Vocabulary | null>(null);
  const [rows, setRows] = useState<Exercise[]>([]);
  const [total, setTotal] = useState(0);
  const [cursor, setCursor] = useState<string | null>(null);
  const [busy, setBusy] = useState(true);

  const [q, setQ] = useState("");
  const [bodyPart, setBodyPart] = useState("");
  const [difficulty, setDifficulty] = useState("");
  const [showIncompatible, setShowIncompatible] = useState(false);
  const [open, setOpen] = useState<string | null>(null);

  useEffect(() => {
    if (!loading && !profile) router.replace("/login");
  }, [loading, profile, router]);

  useEffect(() => {
    if (profile) void api.get<Vocabulary>("/vocabulary").then(setVocab);
  }, [profile]);

  const load = useCallback(
    async (nextCursor?: string) => {
      setBusy(true);
      const page = await api.get<ExercisePage>(
        `/exercises${query({
          q,
          body_part: bodyPart,
          difficulty,
          include_incompatible: showIncompatible,
          limit: 30,
          cursor: nextCursor,
        })}`,
      );
      setRows((previous) => (nextCursor ? [...previous, ...page.data] : page.data));
      setTotal(page.total);
      setCursor(page.next_cursor);
      setBusy(false);
    },
    [q, bodyPart, difficulty, showIncompatible],
  );

  useEffect(() => {
    if (!profile) return;
    // Debounced so typing does not fire a request per keystroke.
    const timer = setTimeout(() => void load(), 200);
    return () => clearTimeout(timer);
  }, [profile, load]);

  if (loading || !profile) return <Spinner />;

  const equipmentCount = profile.settings.available_equipment.length;

  return (
    <section className="flex flex-col gap-5 py-6">
      <header className="flex flex-col gap-1">
        <h1 className="text-[22px] font-semibold">Exercises</h1>
        <p className="text-[13px] text-ink-dim">
          {total} match your equipment
          {equipmentCount <= 1 && " — add equipment in your profile to see more"}.
        </p>
      </header>

      <div className="flex flex-col gap-3">
        <Input
          label="Search"
          placeholder="row, squat, plank…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <div className="grid gap-3 sm:grid-cols-2">
          <Select label="Body part" value={bodyPart} onChange={(e) => setBodyPart(e.target.value)}>
            <option value="">All</option>
            {vocab?.body_parts.map((part) => (
              <option key={part} value={part}>
                {humanize(part)}
              </option>
            ))}
          </Select>
          <Select
            label="Difficulty"
            value={difficulty}
            onChange={(e) => setDifficulty(e.target.value)}
          >
            <option value="">Any</option>
            {vocab?.difficulties.map((level) => (
              <option key={level} value={level}>
                {humanize(level)}
              </option>
            ))}
          </Select>
        </div>
        <Chip selected={showIncompatible} onClick={() => setShowIncompatible((v) => !v)}>
          Show what I&rsquo;m missing equipment for
        </Chip>
      </div>

      {busy && rows.length === 0 ? (
        <Spinner />
      ) : rows.length === 0 ? (
        <Empty
          title="Nothing matches that."
          hint="Try a broader search, or turn on “show what I'm missing equipment for” to see what you could do with more kit."
        />
      ) : (
        <ul className="flex flex-col gap-2">
          {rows.map((exercise) => (
            <li key={exercise.id}>
              <button
                onClick={() => setOpen(open === exercise.id ? null : exercise.id)}
                aria-expanded={open === exercise.id}
                className={`panel w-full p-4 text-left transition-colors ${
                  exercise.compatible
                    ? "border-surface-edge hover:border-ink-faint"
                    : "border-surface-edge/60 opacity-60"
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  {exercise.image_url && (
                    /* eslint-disable-next-line @next/next/no-img-element */
                    <img
                      src={exercise.image_url}
                      alt=""
                      loading="lazy"
                      className="h-14 w-14 shrink-0 rounded-lg bg-surface object-contain"
                    />
                  )}
                  <div className="min-w-0 flex-1">
                    <p className="text-[15px] font-medium">{exercise.name}</p>
                    <p className="mt-0.5 text-[13px] text-ink-dim">
                      {humanize(exercise.primary_muscle)} ·{" "}
                      {exercise.equipment.map(humanize).join(", ")}
                    </p>
                  </div>
                  <span className="shrink-0 rounded-full border border-surface-edge px-2.5 py-1 text-[11px] uppercase tracking-wide text-ink-faint">
                    {exercise.difficulty.slice(0, 3)}
                  </span>
                </div>

                {!exercise.compatible && (
                  /* Sec 6.1 - never silently hidden; the reason is named. */
                  <p className="mt-2 text-[13px] text-warn">
                    Needs {exercise.missing_equipment.map(humanize).join(" + ")}
                  </p>
                )}

                {open === exercise.id && (
                  <div className="mt-3 flex flex-col gap-2 border-t border-surface-edge pt-3">
                    {exercise.instructions.map((line, i) => (
                      <p key={i} className="text-[14px] leading-relaxed text-ink-dim">
                        {line}
                      </p>
                    ))}
                    <span className="text-[13px] text-accent">
                      Open the full page for the demonstration →
                    </span>
                  </div>
                )}
              </button>
              <Link
                href={`/exercises/${exercise.id}`}
                className="label mt-1 inline-block px-4 hover:text-accent"
              >
                open full page →
              </Link>
            </li>
          ))}
        </ul>
      )}

      {cursor && (
        <Button variant="ghost" onClick={() => void load(cursor)} disabled={busy}>
          {busy ? "Loading…" : "Show more"}
        </Button>
      )}
    </section>
  );
}
