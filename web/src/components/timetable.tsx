"use client";

import { useEffect, useState } from "react";
import { TIMETABLE, WEEKDAYS, type GymClass, type Weekday, formatTime, isLive, todayKey } from "@/lib/gym";

const INTENSITY = {
  1: { label: "Easy", dot: "bg-brand-cyan", ring: "border-brand-cyan/40", text: "text-brand-cyan" },
  2: { label: "Moderate", dot: "bg-brand-yellow", ring: "border-brand-yellow/40", text: "text-brand-yellow" },
  3: { label: "Intense", dot: "bg-brand-pink", ring: "border-brand-pink/40", text: "text-brand-pink" },
} as const;

export function IntensityDots({ level }: { level: GymClass["intensity"] }) {
  const tone = INTENSITY[level];
  return (
    <span className="inline-flex items-center gap-1.5" title={`${tone.label} intensity`}>
      {[1, 2, 3].map((n) => (
        <span key={n} className={`h-1.5 w-3 rounded-full ${n <= level ? tone.dot : "bg-ink/15"}`} />
      ))}
      <span className={`text-[11px] font-semibold ${tone.text}`}>{tone.label}</span>
    </span>
  );
}

export function ClassCard({ item, live = false, past = false }: { item: GymClass; live?: boolean; past?: boolean }) {
  const tone = INTENSITY[item.intensity];
  return (
    <li
      className={`flex items-center gap-4 rounded-2xl border bg-surface-raised/80 p-4 transition-opacity ${
        live ? `${tone.ring} shadow-[0_0_0_1px_rgba(255,77,141,0.3)]` : "border-surface-edge"
      } ${past ? "opacity-45" : ""}`}
    >
      <div className="flex w-16 shrink-0 flex-col">
        <span className="font-display text-[24px] leading-none">{formatTime(item.time)}</span>
        <span className="text-[12px] text-ink-faint">{item.minutes} min</span>
      </div>
      <span className={`h-10 w-1 shrink-0 rounded-full ${tone.dot}`} aria-hidden />
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <span className="flex flex-wrap items-center gap-2">
          <span className="text-[16px] font-semibold">{item.name}</span>
          {live && (
            <span className="rounded-full bg-brand-pink px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-surface">
              Live now
            </span>
          )}
        </span>
        <span className="text-[13px] text-ink-dim">
          {item.room} · {item.coach}
        </span>
      </div>
      <div className="hidden sm:block">
        <IntensityDots level={item.intensity} />
      </div>
    </li>
  );
}

export function Timetable() {
  // Start on Monday for the server render, then jump to today on the client
  // so the markup matches during hydration.
  const [day, setDay] = useState<Weekday>("monday");
  const [now, setNow] = useState<Date | null>(null);

  useEffect(() => {
    setDay(todayKey());
    setNow(new Date());
    const timer = window.setInterval(() => setNow(new Date()), 60_000);
    return () => window.clearInterval(timer);
  }, []);

  const today = now ? todayKey(now) : null;
  const minutes = now ? now.getHours() * 60 + now.getMinutes() : 0;

  return (
    <div className="flex min-w-0 flex-col gap-4">
      <div className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1 sm:mx-0 sm:px-0" role="tablist" aria-label="Day">
        {WEEKDAYS.map((d) => (
          <button
            key={d}
            role="tab"
            aria-selected={d === day}
            onClick={() => setDay(d)}
            className={`min-h-tap shrink-0 rounded-full px-4 text-[14px] font-semibold capitalize transition-colors ${
              d === day
                ? "bg-brand-gradient text-surface"
                : "border border-surface-edge bg-surface-raised text-ink-dim hover:text-ink"
            }`}
          >
            {d === today ? "Today" : d.slice(0, 3)}
          </button>
        ))}
      </div>
      <ul className="flex flex-col gap-2.5">
        {TIMETABLE[day].map((item) => {
          const [h, m] = item.time.split(":").map(Number);
          const start = h * 60 + m;
          const isToday = day === today;
          return (
            <ClassCard
              key={`${day}-${item.time}`}
              item={item}
              live={isToday && now !== null && isLive(item, now)}
              past={isToday && minutes >= start + item.minutes}
            />
          );
        })}
      </ul>
      <p className="flex flex-wrap gap-x-5 gap-y-2 text-[12px] text-ink-faint">
        {([1, 2, 3] as const).map((level) => (
          <IntensityDots key={level} level={level} />
        ))}
        <span>Classes are included with Unlimited and Elite.</span>
      </p>
    </div>
  );
}
