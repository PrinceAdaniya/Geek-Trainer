"use client";

/** Member dashboard pieces that are about the gym rather than the log. */

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { GYM, type GymClass, formatTime, isLive, upcomingClasses } from "@/lib/gym";
import { OpenBadge } from "@/components/brand";
import { Icon, type IconName } from "@/components/icons";

const ACTIONS: { href: string; label: string; tone: string; text: string; icon: IconName }[] = [
  { href: "/session", label: "Log a workout", tone: "from-brand-pink to-brand-orange", text: "text-brand-pink", icon: "dumbbell" },
  { href: "/classes", label: "Class timetable", tone: "from-brand-cyan to-brand-violet", text: "text-brand-cyan", icon: "calendar" },
  { href: "/support", label: "Report an issue", tone: "from-brand-orange to-brand-yellow", text: "text-brand-orange", icon: "wrench" },
  { href: "/progress", label: "My progress", tone: "from-brand-violet to-brand-pink", text: "text-brand-violet", icon: "chart" },
];

export function GymToday() {
  const [classes, setClasses] = useState<GymClass[] | null>(null);
  const [now, setNow] = useState<Date | null>(null);

  useEffect(() => {
    const tick = () => {
      const current = new Date();
      setNow(current);
      setClasses(upcomingClasses(current).slice(0, 3));
    };
    tick();
    const timer = window.setInterval(tick, 60_000);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
      <section className="panel flex flex-col gap-4 p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="font-display text-[22px] uppercase leading-none">Today at {GYM.name}</h2>
          <OpenBadge />
        </div>
        {classes === null ? (
          <div className="h-16" />
        ) : classes.length === 0 ? (
          <p className="text-[14px] text-ink-dim">
            No more classes today.{" "}
            <Link href="/classes" className="text-accent">See tomorrow →</Link>
          </p>
        ) : (
          <ul className="grid gap-2 sm:grid-cols-3">
            {classes.map((item) => {
              const live = now !== null && isLive(item, now);
              return (
                <li key={item.time} className={`rounded-xl border p-3 ${live ? "border-brand-pink/60 bg-brand-pink/10" : "border-surface-edge bg-surface"}`}>
                  <p className="flex items-center justify-between text-[12px] font-semibold text-ink-faint">
                    {formatTime(item.time)}
                    {live && <span className="rounded-full bg-brand-pink px-1.5 text-[10px] uppercase text-surface">Live</span>}
                  </p>
                  <p className="mt-0.5 text-[15px] font-semibold leading-tight">{item.name}</p>
                  <p className="text-[12px] text-ink-dim">{item.room}</p>
                </li>
              );
            })}
          </ul>
        )}
      </section>

      <nav className="grid grid-cols-2 gap-3" aria-label="Quick actions">
        {ACTIONS.map((action) => (
          <Link
            key={action.href}
            href={action.href}
            className={`group flex min-h-[84px] flex-col justify-between rounded-2xl bg-gradient-to-br p-[1.5px] ${action.tone}`}
          >
            <span className="flex h-full flex-col justify-between rounded-[15px] bg-surface-raised p-3.5 transition-colors group-hover:bg-surface-raised/70">
              <span className={action.text}><Icon name={action.icon} className="h-6 w-6" /></span>
              <span className="text-[14px] font-semibold">{action.label}</span>
            </span>
          </Link>
        ))}
      </nav>
    </div>
  );
}

/** Members invite friends to a free week; the enquiry credits them. */
export function InviteCard() {
  const [code, setCode] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    void api.get<{ code: string }>("/referral").then((r) => setCode(r.code)).catch(() => setCode(null));
  }, []);

  if (!code) return null;
  const link = typeof window !== "undefined" ? `${window.location.origin}/join?ref=${code}` : `/join?ref=${code}`;

  async function share() {
    const text = `Try ${GYM.name} free for a week:`;
    if (navigator.share) {
      try {
        await navigator.share({ title: GYM.name, text, url: link });
        return;
      } catch {
        // Cancelled share sheet - fall through to copying.
      }
    }
    await navigator.clipboard.writeText(link);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 2000);
  }

  return (
    <section className="relative overflow-hidden rounded-2xl bg-brand-gradient p-[1.5px]">
      <div className="flex flex-col gap-4 rounded-[15px] bg-surface-raised p-5 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-col gap-1">
          <p className="font-display text-[24px] uppercase leading-none">
            Invite a friend
          </p>
          <p className="text-[14px] text-ink-dim">
            Friends you invite get a free week pass. Your referral code is{" "}
            <span className="readout rounded bg-surface px-1.5 py-0.5 text-ink">{code}</span>
          </p>
        </div>
        <button onClick={() => void share()} className="btn-cta shrink-0">
          {copied ? "Link copied" : "Share invite link"}
        </button>
      </div>
    </section>
  );
}
