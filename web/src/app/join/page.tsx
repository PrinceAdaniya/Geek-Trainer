"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { ApiError, api } from "@/lib/api";
import { GYM, PLANS, money } from "@/lib/gym";
import { Button, ErrorNote, Input, Select } from "@/components/ui";
import type { LeadKind } from "@/lib/types";

const KINDS: { id: LeadKind; label: string; title: string; blurb: string }[] = [
  { id: "free_pass", label: "Free week pass", title: "Free week pass", blurb: "Seven days of full access, including group classes. No payment details required." },
  { id: "tour", label: "Book a tour", title: "Book a tour", blurb: "A member of our team will show you around and answer your questions. Tours take about 15 minutes." },
  { id: "membership", label: "Join", title: "Join " + GYM.name, blurb: "Choose a plan and we will contact you within one working day to complete your membership. No joining fee." },
];

export default function JoinPage() {
  return (
    <Suspense>
      <JoinForm />
    </Suspense>
  );
}

function JoinForm() {
  const params = useSearchParams();
  const initialKind = (KINDS.find((k) => k.id === params.get("kind"))?.id ?? "free_pass") as LeadKind;
  const [kind, setKind] = useState<LeadKind>(initialKind);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  const referral = params.get("ref") ?? undefined;
  const topic = params.get("topic");
  const initialPlan = PLANS.find((p) => p.id === params.get("plan"))?.id ?? "unlimited";
  const yearly = params.get("billing") === "yearly";
  const current = KINDS.find((k) => k.id === kind)!;

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setError("");
    const plan = PLANS.find((p) => p.id === form.get("plan"));
    try {
      await api.post("/leads", {
        kind,
        name: form.get("name"),
        email: form.get("email"),
        phone: form.get("phone") || null,
        preferred_date: form.get("preferred_date") || null,
        plan: kind === "membership" && plan ? `${plan.name}${form.get("billing") === "yearly" ? " (yearly)" : ""}` : null,
        message: form.get("message") || null,
        referral_code: referral,
        website: form.get("website") || null,
      });
      setDone(true);
    } catch (err) {
      setError(err instanceof ApiError ? friendly(err) : "Something went wrong. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="grid gap-10 py-10 lg:grid-cols-[1fr_1.1fr] lg:py-16">
      <div className="relative hidden overflow-hidden rounded-3xl lg:block">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/gym/join.jpg" alt="" className="absolute inset-0 h-full w-full object-cover" />
        <div className="absolute inset-0 bg-gradient-to-t from-surface via-surface/30 to-transparent" />
        <div className="absolute inset-x-0 bottom-0 flex flex-col gap-3 p-8">
          <p className="font-display text-[56px] uppercase leading-[0.9]">{GYM.name}</p>
          <ul className="flex flex-col gap-1.5 text-[15px] text-ink-dim">
            <li>No joining fee</li>
            <li>Group classes included with your pass</li>
            <li>Free induction with a coach</li>
          </ul>
        </div>
      </div>

      <div className="flex flex-col gap-6">
        {done ? (
          <div className="flex flex-col gap-5 rounded-3xl border border-brand-lime/40 bg-brand-lime/5 p-8">
            <h1 className="font-display text-[44px] uppercase leading-none">Request received</h1>
            <p className="text-[16px] leading-relaxed text-ink-dim">
              {kind === "free_pass" && "Your free week pass is reserved. Give your name at reception on your first visit and we will activate it."}
              {kind === "tour" && "A member of our team will email you to confirm a time for your tour."}
              {kind === "membership" && "We will contact you within one working day to complete your membership."}
            </p>
            <p className="text-[14px] text-ink-dim">
              Questions? Call <a className="text-accent" href={`tel:${GYM.phone.replace(/[^\d+]/g, "")}`}>{GYM.phone}</a>.
            </p>
            <Link href="/" className="btn-outline self-start">Back to {GYM.name}</Link>
          </div>
        ) : (
          <>
            <div className="flex flex-wrap gap-2" role="tablist" aria-label="What would you like?">
              {KINDS.map((option) => (
                <button
                  key={option.id}
                  role="tab"
                  aria-selected={kind === option.id}
                  onClick={() => setKind(option.id)}
                  className={`min-h-tap rounded-full px-5 text-[14px] font-semibold transition-colors ${
                    kind === option.id ? "bg-brand-gradient text-surface" : "border border-surface-edge bg-surface-raised text-ink-dim"
                  }`}
                >
                  {option.label}
                </button>
              ))}
            </div>
            <div className="flex flex-col gap-2">
              <h1 className="font-display text-[48px] uppercase leading-none sm:text-[60px]">{current.title}</h1>
              <p className="text-[16px] text-ink-dim">{current.blurb}</p>
              {referral && (
                <p className="self-start rounded-full bg-brand-cyan/15 px-3 py-1 text-[13px] font-semibold text-brand-cyan">
                  Referred by a member
                </p>
              )}
            </div>

            <form onSubmit={submit} className="flex flex-col gap-4">
              {kind === "membership" && (
                <fieldset className="grid gap-3 sm:grid-cols-3">
                  <legend className="mb-2 text-[13px] text-ink-dim">Plan</legend>
                  {PLANS.map((plan) => (
                    <label key={plan.id} className="relative flex cursor-pointer flex-col gap-0.5 rounded-2xl border border-surface-edge bg-surface-raised p-4 has-[:checked]:border-accent has-[:checked]:bg-accent/10">
                      <input type="radio" name="plan" value={plan.id} defaultChecked={plan.id === initialPlan} className="sr-only" />
                      <span className="text-[15px] font-semibold">{plan.name}</span>
                      <span className="text-[13px] text-ink-dim">{money(plan.monthly)}/month</span>
                      {plan.popular && <span className="absolute right-3 top-3 text-[10px] font-bold uppercase text-accent">Popular</span>}
                    </label>
                  ))}
                </fieldset>
              )}
              {kind === "membership" && (
                <Select label="Billing" name="billing" defaultValue={yearly ? "yearly" : "monthly"}>
                  <option value="monthly">Monthly (30 days&rsquo; notice to cancel)</option>
                  <option value="yearly">Annual (paid upfront, save 15%)</option>
                </Select>
              )}
              <div className="grid gap-4 sm:grid-cols-2">
                <Input label="Full name" name="name" autoComplete="name" required />
                <Input label="Email" name="email" type="email" autoComplete="email" required />
                <Input label="Phone (optional)" name="phone" type="tel" autoComplete="tel" />
                {kind !== "membership" && (
                  <Input
                    label={kind === "tour" ? "Preferred day" : "When do you want to start?"}
                    name="preferred_date"
                    type="date"
                    min={new Date().toISOString().slice(0, 10)}
                  />
                )}
              </div>
              <div className="flex flex-col gap-1.5">
                <label htmlFor="f-message" className="text-[13px] text-ink-dim">Anything we should know? (optional)</label>
                <textarea
                  id="f-message"
                  name="message"
                  rows={3}
                  maxLength={2000}
                  defaultValue={topic === "pt" ? "I'm interested in personal training." : ""}
                  className="rounded-xl border border-surface-edge bg-surface-raised px-3.5 py-3 text-[16px] text-ink placeholder:text-ink-faint focus:border-accent"
                  placeholder="For example: goals, injuries or the best time to call"
                />
              </div>
              {/* Honeypot: hidden from people, irresistible to bots. */}
              <input type="text" name="website" tabIndex={-1} autoComplete="off" className="hidden" aria-hidden />
              <ErrorNote>{error}</ErrorNote>
              <Button type="submit" disabled={busy} className="!rounded-full bg-brand-gradient !min-h-[52px] !text-[16px] !font-bold">
                {busy ? "Sending…" : kind === "free_pass" ? "Request free pass" : kind === "tour" ? "Request a tour" : "Submit"}
              </Button>
              <p className="text-[12px] text-ink-faint">
                We only use your details to contact you about your visit or membership.
              </p>
            </form>
          </>
        )}
      </div>
    </section>
  );
}

function friendly(error: ApiError): string {
  if (error.code === "validation_failed") return "Please check your name and email address.";
  return error.message;
}
