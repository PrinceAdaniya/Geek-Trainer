"use client";

/** Staff inbox: member support requests and visitor enquiries. */

import { useCallback, useEffect, useState } from "react";
import { ApiError, api, query } from "@/lib/api";
import { useSession } from "@/lib/session";
import { LEAD_KIND, LEAD_STATUS, STATUS, categoryOf, when } from "@/lib/tickets";
import { Button, Empty, ErrorNote, Spinner } from "@/components/ui";
import type { Lead, LeadStatus, StaffTicket, TicketStatus } from "@/lib/types";

type Tab = "tickets" | "leads";

export default function StaffPage() {
  const { profile, loading } = useSession();
  const [tab, setTab] = useState<Tab>("tickets");

  if (loading) return <Spinner />;
  if (!profile?.is_staff) {
    return (
      <div className="py-16">
        <Empty title="Staff only" hint="This inbox is for gym staff. Ask the manager to grant access." />
      </div>
    );
  }

  return (
    <section className="flex flex-col gap-6 py-8">
      <div className="flex flex-col gap-2">
        <p className="label text-brand-orange">Staff</p>
        <h1 className="font-display text-[44px] uppercase leading-none">Front desk inbox</h1>
      </div>
      <div className="flex gap-2" role="tablist">
        {([["tickets", "Member requests"], ["leads", "Enquiries & sign-ups"]] as const).map(([id, label]) => (
          <button
            key={id}
            role="tab"
            aria-selected={tab === id}
            onClick={() => setTab(id)}
            className={`min-h-tap rounded-full px-5 text-[14px] font-semibold ${
              tab === id ? "bg-brand-gradient text-surface" : "border border-surface-edge bg-surface-raised text-ink-dim"
            }`}
          >
            {label}
          </button>
        ))}
      </div>
      {tab === "tickets" ? <Tickets /> : <Leads />}
    </section>
  );
}

function Filter<T extends string>({ value, options, onChange }: {
  value: T | "";
  options: [T | "", string][];
  onChange: (value: T | "") => void;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {options.map(([id, label]) => (
        <button
          key={id || "all"}
          onClick={() => onChange(id)}
          aria-pressed={value === id}
          className={`min-h-[36px] rounded-full px-3.5 text-[13px] font-semibold ${
            value === id ? "bg-ink text-surface" : "border border-surface-edge text-ink-dim"
          }`}
        >
          {label}
        </button>
      ))}
    </div>
  );
}

function Tickets() {
  const [status, setStatus] = useState<TicketStatus | "">("open");
  const [rows, setRows] = useState<StaffTicket[] | null>(null);

  const load = useCallback(() => {
    setRows(null);
    void api.get<StaffTicket[]>(`/staff/tickets${query({ status: status || undefined })}`).then(setRows);
  }, [status]);
  useEffect(load, [load]);

  return (
    <div className="flex flex-col gap-4">
      <Filter
        value={status}
        onChange={setStatus}
        options={[["open", "New"], ["in_progress", "In progress"], ["resolved", "Resolved"], ["closed", "Closed"], ["", "All"]]}
      />
      {rows === null ? (
        <Spinner />
      ) : rows.length === 0 ? (
        <Empty title="No requests" hint="There are no requests with this status." />
      ) : (
        <ul className="grid gap-3 lg:grid-cols-2">
          {rows.map((ticket) => (
            <StaffTicketCard
              key={ticket.id}
              ticket={ticket}
              onSaved={(saved) => setRows((list) => list?.map((r) => (r.id === saved.id ? saved : r)) ?? null)}
            />
          ))}
        </ul>
      )}
    </div>
  );
}

function StaffTicketCard({ ticket, onSaved }: { ticket: StaffTicket; onSaved: (t: StaffTicket) => void }) {
  const [reply, setReply] = useState(ticket.staff_response ?? "");
  const [nextStatus, setNextStatus] = useState<TicketStatus>(ticket.status);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const category = categoryOf(ticket.category);
  const hoursOpen = Math.floor((Date.now() - new Date(ticket.created_at).getTime()) / 3_600_000);

  async function save() {
    setBusy(true);
    setError("");
    try {
      const updated = await api.patch<StaffTicket>(`/staff/tickets/${ticket.id}`, {
        status: nextStatus !== ticket.status ? nextStatus : undefined,
        staff_response: reply.trim() !== (ticket.staff_response ?? "") ? reply : undefined,
      });
      onSaved(updated);
      setNextStatus(updated.status);
      setSaved(true);
      window.setTimeout(() => setSaved(false), 2000);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <li className={`flex flex-col gap-3 rounded-2xl border bg-surface-raised p-4 ${ticket.priority === "urgent" ? "border-bad/50" : "border-surface-edge"}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 flex-col gap-1">
          <span className="flex flex-wrap items-center gap-2 text-[12px] text-ink-faint">
            {category.label}
            {ticket.area && <>· {ticket.area}</>}
            {ticket.priority === "urgent" && <span className="rounded-full bg-bad/15 px-2 font-semibold text-bad">Urgent</span>}
          </span>
          <span className="text-[16px] font-semibold">{ticket.subject}</span>
          <span className="text-[13px] text-ink-dim">
            {ticket.member_name} · <a href={`mailto:${ticket.member_email}`} className="hover:text-ink">{ticket.member_email}</a>
          </span>
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1">
          <span className={`rounded-full px-2.5 py-1 text-[12px] font-semibold ${STATUS[ticket.status].className}`}>{STATUS[ticket.status].label}</span>
          <span className={`text-[11px] ${hoursOpen > 24 && ticket.status === "open" ? "font-semibold text-warn" : "text-ink-faint"}`}>
            {when(ticket.created_at)}
          </span>
        </div>
      </div>
      <p className="whitespace-pre-wrap rounded-xl bg-surface p-3 text-[14px] leading-relaxed text-ink-dim">{ticket.description}</p>
      <textarea
        value={reply}
        onChange={(e) => setReply(e.target.value)}
        rows={2}
        maxLength={4000}
        aria-label="Reply to member"
        placeholder="Reply to the member. They'll see it in the app."
        className="rounded-xl border border-surface-edge bg-surface px-3.5 py-2.5 text-[15px] text-ink placeholder:text-ink-faint focus:border-accent"
      />
      <div className="flex flex-wrap items-center gap-2">
        <select
          value={nextStatus}
          onChange={(e) => setNextStatus(e.target.value as TicketStatus)}
          aria-label="Status"
          className="min-h-tap rounded-xl border border-surface-edge bg-surface px-3 text-[14px] text-ink"
        >
          {(Object.keys(STATUS) as TicketStatus[]).map((s) => <option key={s} value={s}>{STATUS[s].label}</option>)}
        </select>
        <Button onClick={() => void save()} disabled={busy} className="!rounded-full">
          {busy ? "Saving…" : saved ? "Saved" : "Save"}
        </Button>
      </div>
      <ErrorNote>{error}</ErrorNote>
    </li>
  );
}

function Leads() {
  const [status, setStatus] = useState<LeadStatus | "">("new");
  const [rows, setRows] = useState<Lead[] | null>(null);

  const load = useCallback(() => {
    setRows(null);
    void api.get<Lead[]>(`/staff/leads${query({ status: status || undefined })}`).then(setRows);
  }, [status]);
  useEffect(load, [load]);

  async function move(lead: Lead, next: LeadStatus) {
    const updated = await api.patch<Lead>(`/staff/leads/${lead.id}`, { status: next });
    setRows((list) => list?.map((r) => (r.id === updated.id ? updated : r)) ?? null);
  }

  return (
    <div className="flex flex-col gap-4">
      <Filter
        value={status}
        onChange={setStatus}
        options={[["new", "New"], ["contacted", "Contacted"], ["joined", "Joined"], ["closed", "Closed"], ["", "All"]]}
      />
      {rows === null ? (
        <Spinner />
      ) : rows.length === 0 ? (
        <Empty title="No enquiries here" hint="Free-pass claims, tour requests and membership sign-ups from the website land in this list." />
      ) : (
        <div className="overflow-x-auto rounded-2xl border border-surface-edge">
          <table className="w-full min-w-[760px] text-left text-[14px]">
            <thead className="bg-surface-raised text-[12px] uppercase tracking-wider text-ink-faint">
              <tr>
                <th className="px-4 py-3 font-semibold">Received</th>
                <th className="px-4 py-3 font-semibold">Type</th>
                <th className="px-4 py-3 font-semibold">Contact</th>
                <th className="px-4 py-3 font-semibold">Details</th>
                <th className="px-4 py-3 font-semibold">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-edge">
              {rows.map((lead) => (
                <tr key={lead.id} className="align-top">
                  <td className="whitespace-nowrap px-4 py-3 text-ink-dim">{when(lead.created_at)}</td>
                  <td className="px-4 py-3">
                    <span className="font-semibold">{LEAD_KIND[lead.kind]}</span>
                    {lead.plan && <span className="block text-[13px] text-accent">{lead.plan}</span>}
                    {lead.referred_by_name && <span className="block text-[12px] text-brand-cyan">Referred by {lead.referred_by_name}</span>}
                  </td>
                  <td className="px-4 py-3">
                    <span className="block font-semibold">{lead.name}</span>
                    <a href={`mailto:${lead.email}`} className="block text-ink-dim hover:text-ink">{lead.email}</a>
                    {lead.phone && <a href={`tel:${lead.phone}`} className="block text-ink-dim hover:text-ink">{lead.phone}</a>}
                  </td>
                  <td className="max-w-xs px-4 py-3 text-ink-dim">
                    {lead.preferred_date && <span className="block">Preferred date: {lead.preferred_date}</span>}
                    {lead.message && <span className="block whitespace-pre-wrap">{lead.message}</span>}
                  </td>
                  <td className="px-4 py-3">
                    <select
                      value={lead.status}
                      onChange={(e) => void move(lead, e.target.value as LeadStatus)}
                      aria-label={`Status for ${lead.name}`}
                      className={`min-h-[36px] rounded-full border-0 px-3 text-[13px] font-semibold ${LEAD_STATUS[lead.status].className}`}
                    >
                      {(Object.keys(LEAD_STATUS) as LeadStatus[]).map((s) => (
                        <option key={s} value={s} className="bg-surface text-ink">{LEAD_STATUS[s].label}</option>
                      ))}
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
