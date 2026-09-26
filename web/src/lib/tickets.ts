/** Labels and colours for support tickets, shared by the member and staff views. */

import type { LeadKind, LeadStatus, TicketCategory, TicketStatus } from "./types";

export const CATEGORIES: { id: TicketCategory; label: string }[] = [
  { id: "equipment", label: "Broken equipment" },
  { id: "cleanliness", label: "Cleanliness" },
  { id: "facilities", label: "Showers, lockers & facilities" },
  { id: "classes", label: "Classes" },
  { id: "staff", label: "Staff & service" },
  { id: "membership", label: "Billing, freeze or cancel" },
  { id: "safety", label: "Safety concern" },
  { id: "other", label: "Something else" },
];

export const AREAS = [
  "Free weights", "Strength racks", "Machines", "Cardio deck", "Functional zone",
  "Studio 1", "Studio 2", "Cycle studio", "Changing rooms", "Recovery zone",
  "Reception", "Car park", "App / website",
];

export const STATUS: Record<TicketStatus, { label: string; className: string; step: number }> = {
  open: { label: "Received", className: "bg-brand-yellow/15 text-brand-yellow", step: 0 },
  in_progress: { label: "In progress", className: "bg-brand-cyan/15 text-brand-cyan", step: 1 },
  resolved: { label: "Resolved", className: "bg-brand-lime/15 text-brand-lime", step: 2 },
  closed: { label: "Closed", className: "bg-ink/10 text-ink-dim", step: 2 },
};

export const LEAD_KIND: Record<LeadKind, string> = {
  free_pass: "Free week pass",
  tour: "Tour request",
  membership: "Membership enquiry",
};

export const LEAD_STATUS: Record<LeadStatus, { label: string; className: string }> = {
  new: { label: "New", className: "bg-brand-pink/15 text-brand-pink" },
  contacted: { label: "Contacted", className: "bg-brand-cyan/15 text-brand-cyan" },
  joined: { label: "Joined", className: "bg-brand-lime/15 text-brand-lime" },
  closed: { label: "Closed", className: "bg-ink/10 text-ink-dim" },
};

export function categoryOf(id: TicketCategory) {
  return CATEGORIES.find((c) => c.id === id) ?? CATEGORIES[CATEGORIES.length - 1];
}

export function when(iso: string): string {
  const date = new Date(iso);
  const days = Math.floor((Date.now() - date.getTime()) / 86_400_000);
  const time = date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  if (days === 0 && new Date().getDate() === date.getDate()) return `Today ${time}`;
  if (days <= 1) return `Yesterday ${time}`;
  return date.toLocaleDateString([], { day: "numeric", month: "short" });
}
