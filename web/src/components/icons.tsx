/** Line icons (24px grid, 1.8 stroke) so the site does not rely on emoji. */

const PATHS = {
  flame: "M12 3c1 3.5 5 5.5 5 10a5 5 0 0 1-10 0c0-2.5 1.5-4 2.5-5 .3 1.7 1.2 2.7 2.5 3-1-3 0-6 0-8z",
  shower: "M4 20V8a4 4 0 0 1 4-4h1a4 4 0 0 1 4 4M9 12h8M11 15v1M14 15v1M17 15v1M11 18v1M14 18v1M17 18v1",
  parking: "M5 4h14v16H5zM10 16V8h3a2.5 2.5 0 0 1 0 5h-3",
  wifi: "M3 9.5a13 13 0 0 1 18 0M6 13a8 8 0 0 1 12 0M9 16.5a3.5 3.5 0 0 1 6 0M12 20h.01",
  cup: "M5 8h11v6a5 5 0 0 1-5 5h-1a5 5 0 0 1-5-5zM16 10h2a2 2 0 0 1 0 4h-2M8 3v2M11 3v2",
  coach: "M12 11a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7zM5 20a7 7 0 0 1 14 0",
  dumbbell: "M3 10v4M6 7v10M18 7v10M21 10v4M6 12h12",
  calendar: "M4 6h16v14H4zM4 10h16M9 3v4M15 3v4",
  wrench: "M14.5 4.5a4 4 0 0 0-5 5L4 15l5 5 5.5-5.5a4 4 0 0 0 5-5l-2.5 2.5-2.5-.5-.5-2.5z",
  chart: "M4 20V4M4 20h16M8 16v-4M12 16V8M16 16v-6",
  offline: "M3 3l18 18M8.5 16.5a5 5 0 0 1 7 0M5 13a10 10 0 0 1 5-2.7M14 10.3a10 10 0 0 1 5 2.7M12 20h.01",
  trophy: "M8 4h8v5a4 4 0 0 1-8 0zM8 6H5a3 3 0 0 0 3 4M16 6h3a3 3 0 0 1-3 4M12 13v4M8 20h8",
  message: "M4 5h16v11H9l-5 4z",
  share: "M16 8a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM8 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM16 22a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM10.6 13.5l2.8 1.8M13.4 8.7l-2.8 1.8",
  check: "M5 12.5 10 17 19 7",
} as const;

export type IconName = keyof typeof PATHS;

export function Icon({ name, className = "h-5 w-5" }: { name: IconName; className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d={PATHS[name]} />
    </svg>
  );
}
