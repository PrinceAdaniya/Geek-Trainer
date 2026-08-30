"use client";

import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Rest timer. SPECIFICATIONS.MD 11.3.
 *
 * Runs off wall-clock timestamps rather than a counter, so it stays correct
 * when the screen sleeps or the tab is backgrounded - which, in a gym, is most
 * of the time. The interval only triggers a re-render; it never *is* the clock.
 */
export function useRestTimer() {
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const [target, setTarget] = useState(0);
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (startedAt === null) return;
    const tick = setInterval(() => setNow(Date.now()), 250);
    return () => clearInterval(tick);
  }, [startedAt]);

  const elapsed = startedAt === null ? 0 : Math.floor((now - startedAt) / 1000);
  const remaining = startedAt === null ? 0 : Math.max(0, target - elapsed);
  const done = startedAt !== null && remaining === 0;

  const start = useCallback((seconds: number) => {
    setTarget(seconds);
    setStartedAt(Date.now());
    setNow(Date.now());
  }, []);

  const stop = useCallback(() => setStartedAt(null), []);

  return { elapsed, remaining, done, running: startedAt !== null, start, stop, target };
}

/**
 * Keep the screen awake while a session is in progress. SPECIFICATIONS.MD 11.4.
 * Silently unavailable where the API is not - never a visible error.
 */
export function useWakeLock(active: boolean) {
  const lock = useRef<{ release: () => Promise<void> } | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function acquire() {
      const nav = navigator as Navigator & {
        wakeLock?: { request: (type: "screen") => Promise<{ release: () => Promise<void> }> };
      };
      if (!active || !nav.wakeLock) return;
      try {
        const sentinel = await nav.wakeLock.request("screen");
        if (cancelled) void sentinel.release();
        else lock.current = sentinel;
      } catch {
        // Denied or unsupported. Not worth telling the user about.
      }
    }

    void acquire();
    // Browsers drop the lock when the tab is hidden; take it again on return.
    const onVisible = () => {
      if (document.visibilityState === "visible") void acquire();
    };
    document.addEventListener("visibilitychange", onVisible);

    return () => {
      cancelled = true;
      document.removeEventListener("visibilitychange", onVisible);
      void lock.current?.release();
      lock.current = null;
    };
  }, [active]);
}

/** Elapsed session time, also wall-clock based. */
export function useElapsed(since: string | null) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!since) return;
    const tick = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(tick);
  }, [since]);
  if (!since) return 0;
  return Math.max(0, Math.floor((now - new Date(since).getTime()) / 1000));
}

export function formatClock(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

/** UUIDv7, matching api/app/core/ids.py - PLAN.md D3. */
export function uuid7(): string {
  const ms = Date.now();
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  for (let i = 0; i < 6; i++) {
    bytes[5 - i] = (ms / 256 ** i) & 0xff;
  }
  bytes[6] = (bytes[6] & 0x0f) | 0x70;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = [...bytes].map((b) => b.toString(16).padStart(2, "0")).join("");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}
