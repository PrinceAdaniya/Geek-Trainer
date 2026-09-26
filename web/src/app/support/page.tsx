"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ApiError, api } from "@/lib/api";
import { useSession } from "@/lib/session";
import { GYM } from "@/lib/gym";
import { AREAS, CATEGORIES, STATUS, categoryOf, when } from "@/lib/tickets";
import { Button, Empty, ErrorNote, Input, Select, Spinner } from "@/components/ui";
import type { Ticket, TicketCategory } from "@/lib/types";

export default function SupportPage() {
  const { profile, loading } = useSession();
  const [tickets, setTickets] = useState<Ticket[] | null>(null);
  const [creating, setCreating] = useState(false);
  const [justSent, setJustSent] = useState<string | null>(null);

  useEffect(() => {
    if (profile) void api.get<Ticket[]>("/tickets").then(setTickets);
  }, [profile]);

  if (loading) return <Spinner />;
  if (!profile) {
    return (
      <div className="py-16">
        <Empty
          title="Log in to contact the team"
          hint={`Members can raise a request and follow it here. Not a member? Call ${GYM.phone} or email ${GYM.email}.`}
          action={<Link href="/login" className="btn-cta">Member log in</Link>}
        />
      </div>
    );
  }

  const open = tickets?.filter((t) => t.status === "open" || t.status === "in_progress") ?? [];
  const done = tickets?.filter((t) => t.status === "resolved" || t.status === "closed") ?? [];

  return (
    <section className="flex flex-col gap-8 py-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex flex-col gap-2">
          <p className="label text-brand-orange">Support</p>
          <h1 className="font-display text-[44px] uppercase leading-none">How can we help?</h1>
          <p className="max-w-xl text-[15px] text-ink-dim">
            Report an equipment fault, cleanliness issue or anything else, and
            follow its progress here. We reply within one working day. Urgent
            safety issues are handled first.
          </p>
        </div>
        {!creating && (
          <Button onClick={() => { setCreating(true); setJustSent(null); }} className="!rounded-full bg-brand-gradient !px-6 !font-bold">
            New request
          </Button>
        )}
      </div>

      {justSent && (
        <p role="status" className="rounded-2xl border border-brand-lime/40 bg-brand-lime/10 px-4 py-3 text-[15px] text-brand-lime">
          Request sent. Our reply will appear here.
        </p>
      )}

      {creating && (
        <NewTicket
          onCancel={() => setCreating(false)}
          onCreated={(ticket) => {
            setTickets((rows) => [ticket, ...(rows ?? [])]);
            setCreating(false);
            setJustSent(ticket.id);
          }}
        />
      )}

      {tickets === null ? (
        <Spinner label="Loading your requests" />
      ) : tickets.length === 0 && !creating ? (
        <Empty
          title="No requests yet"
          hint="Report an equipment fault, a cleanliness issue or anything else, and track it here."
          action={<Button onClick={() => setCreating(true)}>Raise a request</Button>}
        />
      ) : (
        <div className="grid gap-8 lg:grid-cols-2">
          <TicketList title="Open" tickets={open} highlight={justSent} empty="No open requests." onChange={setTickets} />
          <TicketList title="Resolved" tickets={done} empty="Resolved requests will appear here." onChange={setTickets} />
        </div>
      )}

      <aside className="flex flex-wrap items-center gap-x-6 gap-y-2 rounded-2xl border border-surface-edge bg-surface-raised p-4 text-[14px] text-ink-dim">
        <span className="font-semibold text-ink">Contact us directly</span>
        <a href={`tel:${GYM.phone.replace(/[^\d+]/g, "")}`} className="hover:text-ink">{GYM.phone}</a>
        <a href={`mailto:${GYM.email}`} className="hover:text-ink">{GYM.email}</a>
        <span>Or speak to any member of staff.</span>
      </aside>
    </section>
  );
}

function NewTicket({ onCancel, onCreated }: { onCancel: () => void; onCreated: (t: Ticket) => void }) {
  const [category, setCategory] = useState<TicketCategory | null>(null);
  const [urgent, setUrgent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!category) {
      setError("Select a category.");
      return;
    }
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setError("");
    try {
      const ticket = await api.post<Ticket>("/tickets", {
        category,
        area: form.get("area") || null,
        subject: form.get("subject"),
        description: form.get("description"),
        priority: urgent || category === "safety" ? "urgent" : "normal",
      });
      onCreated(ticket);
    } catch (err) {
      setError(
        err instanceof ApiError && err.code === "validation_failed"
          ? "Add a short title (3+ characters) and a few words of detail (10+ characters)."
          : err instanceof ApiError ? err.message : "Something went wrong.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="panel flex flex-col gap-5 p-5 sm:p-6">
      <div className="flex flex-col gap-3">
        <span className="text-[15px] font-semibold">Category</span>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          {CATEGORIES.map((option) => (
            <button
              key={option.id}
              type="button"
              aria-pressed={category === option.id}
              onClick={() => setCategory(option.id)}
              className={`flex min-h-[56px] flex-col items-start justify-center gap-1 rounded-2xl border px-3 text-left text-[13px] font-semibold transition-colors ${
                category === option.id
                  ? "border-accent bg-accent/10 text-ink"
                  : "border-surface-edge bg-surface text-ink-dim hover:border-ink-faint"
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-[1fr_2fr]">
        <Select label="Location (optional)" name="area" defaultValue="">
          <option value="">Not applicable</option>
          {AREAS.map((area) => <option key={area}>{area}</option>)}
        </Select>
        <Input label="Subject" name="subject" required minLength={3} maxLength={120} placeholder="e.g. Treadmill 4 belt slipping" />
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="f-description" className="text-[13px] text-ink-dim">Details</label>
        <textarea
          id="f-description"
          name="description"
          required
          minLength={10}
          maxLength={4000}
          rows={4}
          className="rounded-xl border border-surface-edge bg-surface-raised px-3.5 py-3 text-[16px] text-ink placeholder:text-ink-faint focus:border-accent"
          placeholder="Which machine or area, when it happened, and what you noticed."
        />
      </div>

      <label className="flex min-h-tap cursor-pointer items-center gap-3 text-[14px]">
        <input
          type="checkbox"
          checked={urgent || category === "safety"}
          disabled={category === "safety"}
          onChange={(e) => setUrgent(e.target.checked)}
          className="h-5 w-5 accent-[#ff4d8d]"
        />
        <span>
          <span className="font-semibold">This is urgent</span>
          <span className="text-ink-dim"> (risk of injury, or I can&rsquo;t train)</span>
        </span>
      </label>

      <ErrorNote>{error}</ErrorNote>
      <div className="flex flex-wrap gap-3">
        <Button type="submit" disabled={busy} className="!rounded-full bg-brand-gradient !px-6 !font-bold">
          {busy ? "Sending…" : "Send request"}
        </Button>
        <Button type="button" variant="ghost" onClick={onCancel} className="!rounded-full">
          Cancel
        </Button>
      </div>
    </form>
  );
}

function TicketList({
  title, tickets, empty, highlight, onChange,
}: {
  title: string;
  tickets: Ticket[];
  empty: string;
  highlight?: string | null;
  onChange: React.Dispatch<React.SetStateAction<Ticket[] | null>>;
}) {
  return (
    <div className="flex flex-col gap-3">
      <h2 className="label">{title} · {tickets.length}</h2>
      {tickets.length === 0 ? (
        <p className="rounded-2xl border border-dashed border-surface-edge p-6 text-center text-[14px] text-ink-faint">{empty}</p>
      ) : (
        <ul className="flex flex-col gap-3">
          {tickets.map((ticket) => (
            <TicketCard key={ticket.id} ticket={ticket} highlight={ticket.id === highlight} onChange={onChange} />
          ))}
        </ul>
      )}
    </div>
  );
}

function TicketCard({
  ticket, highlight, onChange,
}: {
  ticket: Ticket;
  highlight: boolean;
  onChange: React.Dispatch<React.SetStateAction<Ticket[] | null>>;
}) {
  const [busy, setBusy] = useState(false);
  const status = STATUS[ticket.status];
  const category = categoryOf(ticket.category);
  const steps = ["Received", "In progress", "Resolved"];

  async function close() {
    setBusy(true);
    const updated = await api.post<Ticket>(`/tickets/${ticket.id}/close`);
    onChange((rows) => rows?.map((row) => (row.id === updated.id ? updated : row)) ?? null);
    setBusy(false);
  }

  return (
    <li className={`flex flex-col gap-3 rounded-2xl border bg-surface-raised p-4 ${highlight ? "border-brand-lime/50" : "border-surface-edge"}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 flex-col gap-1">
          <span className="flex flex-wrap items-center gap-2 text-[12px] text-ink-faint">
            {category.label}
            {ticket.area && <>· {ticket.area}</>}
            {ticket.priority === "urgent" && <span className="rounded-full bg-bad/15 px-2 font-semibold text-bad">Urgent</span>}
          </span>
          <span className="text-[16px] font-semibold">{ticket.subject}</span>
        </div>
        <span className={`shrink-0 rounded-full px-2.5 py-1 text-[12px] font-semibold ${status.className}`}>{status.label}</span>
      </div>

      {ticket.status !== "closed" && (
        <ol className="flex gap-1.5" aria-label={`Status: ${status.label}`}>
          {steps.map((step, i) => (
            <li key={step} className="flex flex-1 flex-col gap-1">
              <span className={`h-1.5 rounded-full ${i <= status.step ? "bg-brand-gradient" : "bg-ink/10"}`} />
              <span className={`text-[11px] ${i <= status.step ? "text-ink-dim" : "text-ink-faint"}`}>{step}</span>
            </li>
          ))}
        </ol>
      )}

      <details className="group">
        <summary className="cursor-pointer list-none text-[13px] text-ink-faint hover:text-ink-dim">
          Sent {when(ticket.created_at)} · <span className="group-open:hidden">show details</span><span className="hidden group-open:inline">hide details</span>
        </summary>
        <p className="mt-2 whitespace-pre-wrap text-[14px] leading-relaxed text-ink-dim">{ticket.description}</p>
      </details>

      {ticket.staff_response && (
        <div className="rounded-xl border-l-4 border-brand-cyan bg-brand-cyan/5 px-4 py-3">
          <p className="text-[12px] font-semibold text-brand-cyan">
            Reply from the {GYM.name} team{ticket.responded_at ? ` · ${when(ticket.responded_at)}` : ""}
          </p>
          <p className="mt-1 whitespace-pre-wrap text-[14px] leading-relaxed">{ticket.staff_response}</p>
        </div>
      )}

      {(ticket.status === "open" || ticket.status === "in_progress") && (
        <button onClick={() => void close()} disabled={busy} className="self-start text-[13px] text-ink-faint underline-offset-2 hover:text-ink hover:underline">
          {busy ? "Closing…" : "No longer needed? Close this request"}
        </button>
      )}
    </li>
  );
}
