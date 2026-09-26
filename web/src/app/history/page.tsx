"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useSession } from "@/lib/session";
import { Empty, Spinner } from "@/components/ui";
import { formatClock } from "@/lib/hooks";
import type { SessionSummary } from "@/lib/types";

export default function HistoryPage() {
  const router = useRouter();
  const { profile, loading } = useSession();
  const [rows, setRows] = useState<SessionSummary[] | null>(null);

  useEffect(() => {
    if (!loading && !profile) router.replace("/login");
  }, [loading, profile, router]);

  useEffect(() => {
    if (profile) void api.get<SessionSummary[]>("/sessions").then(setRows);
  }, [profile]);

  if (loading || !profile || rows === null) return <Spinner />;

  return (
    <section className="flex flex-col gap-4 py-6">
      <h1 className="text-[22px] font-semibold">History</h1>

      {rows.length === 0 ? (
        <Empty
          title="No sessions yet."
          hint="Completed workouts will appear here."
        />
      ) : (
        <ul className="flex flex-col gap-2">
          {rows.map((row) => (
            <li key={row.id}>
              <Link
                href={`/history/${row.id}`}
                className="block rounded-2xl border border-surface-edge bg-surface-raised p-4 transition-colors hover:border-ink-faint"
              >
                <div className="flex items-baseline justify-between gap-3">
                  <span className="text-[15px] font-medium">{row.name}</span>
                  <span className="text-[13px] text-ink-faint">{row.date}</span>
                </div>
                <p className="mt-1 text-[13px] text-ink-dim">
                  {row.exercise_count} exercise{row.exercise_count === 1 ? "" : "s"} ·{" "}
                  {row.set_count} set{row.set_count === 1 ? "" : "s"}
                  {row.duration_seconds ? ` · ${formatClock(row.duration_seconds)}` : ""}
                </p>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
