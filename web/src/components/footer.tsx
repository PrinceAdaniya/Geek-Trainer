import Link from "next/link";

export function Footer() {
  return (
    <footer className="mt-auto border-t border-surface-edge">
      <div className="mx-auto flex w-full max-w-[1400px] flex-col gap-4 px-4 py-8 sm:flex-row sm:items-start sm:justify-between sm:px-6">
        <div className="max-w-sm">
          <p className="font-mono text-[14px] font-semibold">
            GEEK<span className="text-accent">/</span>TRAINER
          </p>
          <p className="mt-1.5 text-[13px] leading-relaxed text-ink-dim">
            An equipment-aware training tracker. Your data stays yours — export
            it as CSV or JSON whenever you like.
          </p>
        </div>

        <nav className="flex flex-wrap gap-x-8 gap-y-3 text-[13px]">
          <div className="flex flex-col gap-1.5">
            <span className="label">Train</span>
            <Link href="/session" className="text-ink-dim hover:text-ink">Log a session</Link>
            <Link href="/plan" className="text-ink-dim hover:text-ink">Weekly plan</Link>
            <Link href="/exercises" className="text-ink-dim hover:text-ink">Exercises</Link>
          </div>
          <div className="flex flex-col gap-1.5">
            <span className="label">Review</span>
            <Link href="/progress" className="text-ink-dim hover:text-ink">Progress</Link>
            <Link href="/history" className="text-ink-dim hover:text-ink">History</Link>
            <Link href="/coach" className="text-ink-dim hover:text-ink">Coach</Link>
          </div>
        </nav>
      </div>

      <div className="mx-auto w-full max-w-[1400px] px-4 pb-8 sm:px-6">
        <p className="text-[12px] leading-relaxed text-ink-faint">
          Exercise data and demonstration images from{" "}
          <a
            href="https://wger.de"
            target="_blank"
            rel="noreferrer noopener"
            className="underline underline-offset-2 hover:text-ink-dim"
          >
            wger.de
          </a>{" "}
          under CC-BY-SA. Geek-Trainer is a training log, not medical advice —
          it does not diagnose injuries and does not replace a qualified coach
          or clinician.
        </p>
      </div>
    </footer>
  );
}
