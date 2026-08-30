"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError, api } from "@/lib/api";
import { useSession } from "@/lib/session";
import { Button, Chip, ErrorNote, Input, Select, Spinner } from "@/components/ui";
import { formatWeight, humanize } from "@/lib/units";
import type { BodyweightEntry, Profile, Vocabulary } from "@/lib/types";

export default function ProfilePage() {
  const router = useRouter();
  const { profile, loading, setProfile } = useSession();
  const [vocab, setVocab] = useState<Vocabulary | null>(null);
  const [history, setHistory] = useState<BodyweightEntry[]>([]);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!loading && !profile) router.replace("/login");
  }, [loading, profile, router]);

  useEffect(() => {
    if (!profile) return;
    void api.get<Vocabulary>("/vocabulary").then(setVocab);
    void api.get<BodyweightEntry[]>("/profile/bodyweight").then(setHistory);
  }, [profile]);

  if (loading || !profile) return <Spinner />;

  const settings = profile.settings;

  async function save(patch: Record<string, unknown>) {
    setError("");
    try {
      setProfile(await api.put<Profile>("/profile", patch));
      setSaved(true);
      setTimeout(() => setSaved(false), 1500);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save.");
    }
  }

  function toggleEquipment(item: string) {
    const current = new Set(settings.available_equipment);
    if (current.has(item)) current.delete(item);
    else current.add(item);
    void save({ available_equipment: [...current] });
  }

  async function logBodyweight(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    setError("");
    try {
      await api.post("/profile/bodyweight", {
        date: data.get("date"),
        weight: Number(data.get("weight")),
      });
      setHistory(await api.get<BodyweightEntry[]>("/profile/bodyweight"));
      setProfile(await api.get<Profile>("/profile"));
      form.reset();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save.");
    }
  }

  return (
    <section className="flex flex-col gap-8 py-6">
      <header className="flex items-baseline justify-between">
        <h1 className="text-[22px] font-semibold">Profile</h1>
        {saved && <span className="text-[13px] text-accent">Saved</span>}
      </header>

      <ErrorNote>{error}</ErrorNote>

      <div className="flex flex-col gap-3">
        <h2 className="text-[15px] font-medium">Equipment</h2>
        <p className="text-[13px] text-ink-dim">
          The catalogue only offers exercises you can load with all of this. Bodyweight is
          always available.
        </p>
        <div className="flex flex-wrap gap-2">
          {vocab?.equipment.map((item) => (
            <Chip
              key={item}
              selected={settings.available_equipment.includes(item)}
              disabled={item === "bodyweight"}
              onClick={() => toggleEquipment(item)}
            >
              {humanize(item)}
            </Chip>
          ))}
        </div>
      </div>

      <div className="flex flex-col gap-3">
        <h2 className="text-[15px] font-medium">Preferences</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <Select
            label="Units"
            value={settings.unit_preference}
            onChange={(e) => void save({ unit_preference: e.target.value })}
          >
            <option value="kg">Kilograms</option>
            <option value="lb">Pounds</option>
          </Select>
          <Select
            label="Week starts on"
            value={settings.week_start}
            onChange={(e) => void save({ week_start: e.target.value })}
          >
            <option value="monday">Monday</option>
            <option value="sunday">Sunday</option>
          </Select>
          <Select
            label="Experience"
            value={profile.training_experience ?? ""}
            onChange={(e) => void save({ training_experience: e.target.value || null })}
          >
            <option value="">Not set</option>
            <option value="beginner">Beginner</option>
            <option value="intermediate">Intermediate</option>
            <option value="advanced">Advanced</option>
          </Select>
          <Input
            label="Default rest (seconds)"
            type="number"
            inputMode="numeric"
            defaultValue={settings.default_rest_seconds}
            onBlur={(e) => void save({ default_rest_seconds: Number(e.target.value) })}
          />
        </div>
        <p className="text-[13px] text-ink-faint">
          Timezone: {settings.timezone} — everything from &ldquo;this week&rdquo; onward is
          measured in it.
        </p>
      </div>

      <div className="flex flex-col gap-3">
        <h2 className="text-[15px] font-medium">Bodyweight</h2>
        <p className="text-[13px] text-ink-dim">
          Kept as a history, not one number — it is what makes a set of pull-ups count for
          anything.
        </p>
        <form onSubmit={logBodyweight} className="flex flex-wrap items-end gap-3">
          <Input
            label="Date"
            name="date"
            type="date"
            defaultValue={new Date().toISOString().slice(0, 10)}
            required
          />
          <Input
            label={`Weight (${settings.unit_preference})`}
            name="weight"
            type="number"
            inputMode="decimal"
            step="0.1"
            min="1"
            required
            className="w-32"
          />
          <Button type="submit" variant="ghost">
            Add
          </Button>
        </form>
        {history.length > 0 && (
          <ul className="flex flex-col divide-y divide-surface-edge rounded-xl border border-surface-edge">
            {history.slice(0, 8).map((entry) => (
              <li key={entry.id} className="flex justify-between px-4 py-3 text-[14px]">
                <span className="text-ink-dim">{entry.date}</span>
                <span>{formatWeight(entry.weight_kg, settings.unit_preference)}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
