import { GYM } from "@/lib/gym";

/** Split layout for log-in and sign-up: photo on the left from md up. */
export function AuthShell({ children }: { children: React.ReactNode }) {
  return (
    <section className="grid min-h-[calc(100dvh-160px)] items-stretch gap-8 py-8 md:grid-cols-2 md:py-12">
      <div className="relative hidden overflow-hidden rounded-3xl md:block">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/gym/auth.jpg" alt="" className="absolute inset-0 h-full w-full object-cover" />
        <div className="absolute inset-0 bg-gradient-to-t from-surface via-surface/40 to-brand-pink/20" />
        <div className="absolute inset-x-0 bottom-0 p-8">
          <p className="font-display text-[52px] uppercase leading-[0.9]">{GYM.name}</p>
          <p className="mt-3 max-w-sm text-[15px] text-ink-dim">
            Member account: workout log, training plans, progress, class
            timetable and support requests.
          </p>
        </div>
      </div>
      <div className="flex items-center">
        <div className="mx-auto flex w-full max-w-sm flex-col gap-6">{children}</div>
      </div>
    </section>
  );
}
