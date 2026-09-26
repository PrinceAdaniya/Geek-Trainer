import Link from "next/link";
import { GYM, HOURS, WEEKDAYS, formatTime } from "@/lib/gym";
import { LogoMark } from "@/components/brand";

const SOCIAL_LABELS: Record<string, string> = { instagram: "Instagram", facebook: "Facebook", tiktok: "TikTok" };

export function Footer() {
  return (
    <footer className="mt-auto border-t border-surface-edge bg-surface/60 pb-20 md:pb-0">
      <div className="h-1 w-full bg-brand-gradient" />
      <div className="mx-auto grid w-full max-w-[1400px] gap-10 px-4 py-12 sm:px-6 md:grid-cols-[1.3fr_1fr_1fr_1fr]">
        <div className="flex max-w-sm flex-col gap-4">
          <div className="flex items-center gap-2.5">
            <LogoMark />
            <span className="font-display text-[26px] leading-none tracking-wide">{GYM.name}</span>
          </div>
          <p className="text-[14px] leading-relaxed text-ink-dim">{GYM.tagline}</p>
          <div className="flex gap-2">
            {Object.entries(GYM.social).map(([name, url]) => (
              <a
                key={name}
                href={url}
                target="_blank"
                rel="noreferrer noopener"
                className="rounded-full border border-surface-edge px-3 py-1.5 text-[12px] font-semibold text-ink-dim hover:border-accent hover:text-ink"
              >
                {SOCIAL_LABELS[name] ?? name}
              </a>
            ))}
          </div>
        </div>

        <div className="flex flex-col gap-2 text-[14px]">
          <span className="label mb-1">Visit</span>
          <span>{GYM.address.line1}</span>
          <span className="text-ink-dim">{GYM.address.line2}</span>
          <a href={GYM.address.mapsUrl} target="_blank" rel="noreferrer noopener" className="text-brand-cyan hover:underline">
            Get directions →
          </a>
          <a href={`tel:${GYM.phone.replace(/[^\d+]/g, "")}`} className="mt-2 text-ink-dim hover:text-ink">{GYM.phone}</a>
          <a href={`mailto:${GYM.email}`} className="text-ink-dim hover:text-ink">{GYM.email}</a>
        </div>

        <div className="flex flex-col gap-1.5 text-[14px]">
          <span className="label mb-1">Opening hours</span>
          {WEEKDAYS.map((day) => {
            const hours = HOURS[day];
            return (
              <span key={day} className="flex justify-between gap-4">
                <span className="capitalize text-ink-dim">{day.slice(0, 3)}</span>
                <span className="readout">
                  {hours ? `${formatTime(hours.open)} – ${formatTime(hours.close)}` : "Closed"}
                </span>
              </span>
            );
          })}
        </div>

        <nav className="flex flex-col gap-2 text-[14px]">
          <span className="label mb-1">Members</span>
          <Link href="/login" className="text-ink-dim hover:text-ink">Member log in</Link>
          <Link href="/classes" className="text-ink-dim hover:text-ink">Class timetable</Link>
          <Link href="/support" className="text-ink-dim hover:text-ink">Report an issue</Link>
          <Link href="/join" className="text-ink-dim hover:text-ink">Claim a free pass</Link>
          <Link href="/join?kind=tour" className="text-ink-dim hover:text-ink">Book a tour</Link>
          <Link href="/#faq" className="text-ink-dim hover:text-ink">FAQ</Link>
        </nav>
      </div>

      <div className="mx-auto w-full max-w-[1400px] px-4 pb-8 sm:px-6">
        <p className="text-[12px] leading-relaxed text-ink-faint">
          © {new Date().getFullYear()} {GYM.name}. Exercise data and demonstration images from{" "}
          <a href="https://wger.de" target="_blank" rel="noreferrer noopener" className="underline underline-offset-2 hover:text-ink-dim">
            wger.de
          </a>{" "}
          under CC-BY-SA. The app is a training log, not medical advice. Speak to
          a coach or clinician about injuries.
        </p>
      </div>
    </footer>
  );
}
