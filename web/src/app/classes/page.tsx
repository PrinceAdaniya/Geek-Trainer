import type { Metadata } from "next";
import { Timetable } from "@/components/timetable";

export const metadata: Metadata = { title: "Class timetable" };

export default function ClassesPage() {
  return (
    <section className="flex flex-col gap-6 py-8">
      <div className="flex flex-col gap-2">
        <p className="label text-brand-orange">This week</p>
        <h1 className="font-display text-[44px] uppercase leading-none">Class timetable</h1>
        <p className="max-w-xl text-[15px] text-ink-dim">
          First come, first served. Arrive five minutes early. Elite members
          get priority at the door.
        </p>
      </div>
      <div className="max-w-3xl">
        <Timetable />
      </div>
    </section>
  );
}
