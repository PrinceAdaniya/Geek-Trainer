"use client";

/** YOUR GYM brand pieces: the logo, the live open/closed badge, headings. */

import Link from "next/link";
import { useEffect, useState } from "react";
import { GYM, openStatus } from "@/lib/gym";

export function LogoMark({ className = "h-8 w-8" }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden>
      <defs>
        <linearGradient id="yg-grad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#ff4d8d" />
          <stop offset="0.55" stopColor="#ff8a3d" />
          <stop offset="1" stopColor="#ffd23f" />
        </linearGradient>
      </defs>
      <rect width="32" height="32" rx="9" fill="url(#yg-grad)" />
      <path d="M6.5 12h3v8h-3zM22.5 12h3v8h-3zM10.5 14.5h11v3h-11z" fill="#0e0b1f" />
    </svg>
  );
}

export function Logo({ href = "/" }: { href?: string }) {
  return (
    <Link href={href} className="flex items-center gap-2.5" aria-label={`${GYM.name} home`}>
      <LogoMark />
      <span className="whitespace-nowrap font-display text-[22px] leading-none tracking-wide">{GYM.name}</span>
    </Link>
  );
}

/** Recomputed every minute on the client; server render shows nothing, so
 *  a cached page never claims the wrong state. */
export function OpenBadge({ className = "" }: { className?: string }) {
  const [status, setStatus] = useState<ReturnType<typeof openStatus> | null>(null);
  useEffect(() => {
    const tick = () => setStatus(openStatus());
    tick();
    const timer = window.setInterval(tick, 60_000);
    return () => window.clearInterval(timer);
  }, []);
  if (!status) return <span className={`inline-block h-7 ${className}`} />;
  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-[12px] font-semibold ${
        status.open
          ? "border-brand-lime/40 bg-brand-lime/10 text-brand-lime"
          : "border-ink/20 bg-ink/5 text-ink-dim"
      } ${className}`}
    >
      <span
        className={`h-2 w-2 rounded-full ${status.open ? "animate-pulse bg-brand-lime" : "bg-ink-faint"}`}
      />
      {status.label}
    </span>
  );
}

export function SectionHeading({
  eyebrow,
  title,
  children,
  center = false,
}: {
  eyebrow?: string;
  title: React.ReactNode;
  children?: React.ReactNode;
  center?: boolean;
}) {
  return (
    <div className={`flex flex-col gap-3 ${center ? "items-center text-center" : ""}`}>
      {eyebrow && (
        <span className="text-[12px] font-bold uppercase tracking-[0.2em] text-brand-orange">
          {eyebrow}
        </span>
      )}
      <h2 className="font-display text-[40px] uppercase leading-[0.95] sm:text-[56px]">{title}</h2>
      {children && (
        <p className={`max-w-2xl text-[16px] leading-relaxed text-ink-dim ${center ? "mx-auto" : ""}`}>
          {children}
        </p>
      )}
    </div>
  );
}
