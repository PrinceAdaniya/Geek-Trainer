"use client";

/** The public YOUR GYM site: what a visitor sees before they are a member. */

import Link from "next/link";
import { useState } from "react";
import {
  AMENITIES,
  ANNUAL_DISCOUNT,
  FACILITIES,
  FAQ,
  GYM,
  HOURS,
  PLANS,
  PROMISES,
  PT_PACKAGES,
  TIMETABLE,
  money,
} from "@/lib/gym";
import { OpenBadge, SectionHeading } from "@/components/brand";
import { Icon, type IconName } from "@/components/icons";
import { Timetable } from "@/components/timetable";

export function Landing() {
  return (
    <div className="flex flex-col">
      <Hero />
      <FactsBar />
      <div className="flex flex-col gap-28 py-20">
        <Memberships />
        <Classes />
        <Facilities />
        <PersonalTraining />
        <MemberApp />
        <Visit />
        <Faq />
      </div>
      <FinalCta />
    </div>
  );
}

function Hero() {
  return (
    <section className="full-bleed relative -mt-px overflow-hidden">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src="/gym/hero.jpg" alt="" className="absolute inset-0 h-full w-full object-cover" />
      <div className="absolute inset-0 bg-gradient-to-r from-surface via-surface/85 to-surface/30" />
      <div className="absolute inset-0 bg-gradient-to-t from-surface via-transparent to-transparent" />
      <div className="relative mx-auto flex min-h-[620px] max-w-[1400px] flex-col justify-center gap-7 px-4 py-20 sm:min-h-[700px] sm:px-6">
        <OpenBadge className="self-start" />
        <h1 className="max-w-4xl font-display text-[60px] uppercase leading-[0.92] sm:text-[100px]">
          Your first week
          <br />
          <span className="text-gradient">is free</span>
        </h1>
        <p className="max-w-xl text-[17px] leading-relaxed text-ink-dim sm:text-[19px]">
          Free weights, strength racks, cardio, daily group classes and
          personal training at {GYM.name}. {GYM.offer.detail}
        </p>
        <div className="flex flex-wrap gap-3">
          <Link href="/join" className="btn-cta !min-h-[52px] !px-8 !text-[16px]">
            Get your free pass
          </Link>
          <Link href="#memberships" className="btn-outline !min-h-[52px] !px-8 !text-[16px]">
            View memberships
          </Link>
        </div>
      </div>
    </section>
  );
}

function FactsBar() {
  const classCount = Object.values(TIMETABLE).reduce((n, day) => n + day.length, 0);
  const openDays = Object.values(HOURS).filter(Boolean).length;
  const facts = [
    [`${openDays} days`, "open every week"],
    [`${classCount}`, "group classes a week"],
    [money(0), "joining fee"],
    ["30 days", "notice to cancel"],
  ];
  return (
    <div className="full-bleed border-y border-surface-edge bg-surface-raised/80">
      <dl className="mx-auto grid max-w-[1400px] grid-cols-2 px-4 sm:px-6 md:grid-cols-4">
        {facts.map(([value, label]) => (
          <div key={label} className="flex flex-col gap-1 py-6">
            <dt className="order-2 text-[13px] text-ink-dim">{label}</dt>
            <dd className="font-display text-[36px] leading-none text-gradient">{value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

const TONES = {
  cyan: { text: "text-brand-cyan", ring: "border-brand-cyan/40" },
  pink: { text: "text-brand-pink", ring: "border-transparent" },
  yellow: { text: "text-brand-yellow", ring: "border-brand-yellow/40" },
} as const;

function Memberships() {
  const [annual, setAnnual] = useState(false);
  return (
    <section id="memberships" className="scroll-mt-24 flex flex-col gap-10">
      <SectionHeading title="Memberships" center>
        Every membership includes the {GYM.name} app and a free induction.
      </SectionHeading>

      <div className="mx-auto flex items-center gap-1 rounded-full border border-surface-edge bg-surface-raised p-1" role="group" aria-label="Billing">
        {[false, true].map((value) => (
          <button
            key={String(value)}
            onClick={() => setAnnual(value)}
            aria-pressed={annual === value}
            className={`min-h-[40px] rounded-full px-5 text-[14px] font-semibold transition-colors ${
              annual === value ? "bg-ink text-surface" : "text-ink-dim"
            }`}
          >
            {value ? `Annual (save ${Math.round(ANNUAL_DISCOUNT * 100)}%)` : "Monthly"}
          </button>
        ))}
      </div>

      <div className="grid gap-5 lg:grid-cols-3">
        {PLANS.map((plan) => {
          const tone = TONES[plan.tone];
          const price = annual ? plan.monthly * (1 - ANNUAL_DISCOUNT) : plan.monthly;
          const card = (
            <div className={`flex h-full flex-col gap-6 rounded-[22px] border bg-surface-raised p-7 ${tone.ring}`}>
              <div className="flex items-center justify-between">
                <span className={`font-display text-[32px] uppercase ${tone.text}`}>{plan.name}</span>
                {plan.popular && (
                  <span className="rounded-full bg-brand-gradient px-3 py-1 text-[11px] font-bold uppercase tracking-wider text-surface">
                    Most popular
                  </span>
                )}
              </div>
              <div>
                <p className="flex items-baseline gap-1">
                  <span className="font-display text-[64px] leading-none">{money(price)}</span>
                  <span className="text-[15px] text-ink-dim">/ month</span>
                </p>
                <p className="mt-1 h-5 text-[13px] text-ink-faint">
                  {annual ? `${money(price * 12)} billed annually` : "Billed monthly"}
                </p>
              </div>
              <p className="text-[15px] text-ink-dim">{plan.blurb}</p>
              <ul className="flex flex-1 flex-col gap-2.5 text-[15px]">
                {plan.features.map((feature) => (
                  <li key={feature} className="flex gap-2.5">
                    <Icon name="check" className={`mt-0.5 h-4 w-4 shrink-0 ${tone.text}`} /> {feature}
                  </li>
                ))}
              </ul>
              <Link
                href={`/join?kind=membership&plan=${plan.id}${annual ? "&billing=yearly" : ""}`}
                className={plan.popular ? "btn-cta w-full" : "btn-outline w-full"}
              >
                Choose {plan.name}
              </Link>
            </div>
          );
          return plan.popular ? (
            <div key={plan.id} className="rounded-[24px] bg-brand-gradient p-[2px] shadow-[0_20px_60px_-20px_rgba(255,77,141,0.55)] lg:-my-3">
              {card}
            </div>
          ) : (
            <div key={plan.id}>{card}</div>
          );
        })}
      </div>

      <ul className="mx-auto flex max-w-4xl flex-wrap justify-center gap-2.5">
        {PROMISES.map((promise) => (
          <li key={promise} className="flex items-center gap-2 rounded-full border border-surface-edge bg-surface-raised px-4 py-2 text-[14px]">
            <Icon name="check" className="h-4 w-4 text-brand-lime" /> {promise}
          </li>
        ))}
      </ul>
    </section>
  );
}

function Classes() {
  return (
    <section id="classes" className="scroll-mt-24 grid grid-cols-1 gap-10 lg:grid-cols-[1fr_1.4fr] [&>*]:min-w-0">
      <div className="flex flex-col gap-6">
        <SectionHeading title="Class timetable">
          Group classes run seven days a week and are included with Unlimited
          and Elite memberships. Select a day to see the schedule.
        </SectionHeading>
        <div className="grid grid-cols-2 gap-3">
          {["/gym/class-strength.jpg", "/gym/class-core.jpg"].map((src) => (
            // eslint-disable-next-line @next/next/no-img-element
            <img key={src} src={src} alt="" loading="lazy" className="aspect-[4/5] w-full rounded-2xl object-cover" />
          ))}
        </div>
      </div>
      <Timetable />
    </section>
  );
}

function Facilities() {
  return (
    <section id="facilities" className="scroll-mt-24 flex flex-col gap-10">
      <SectionHeading title="Facilities">
        Free weights, strength racks, cardio, machines, two group studios and a
        functional training area.
      </SectionHeading>
      <div className="grid auto-rows-[220px] grid-cols-2 gap-3 md:auto-rows-[240px] md:grid-cols-4">
        {FACILITIES.map((facility, i) => (
          <figure
            key={facility.title}
            className={`group relative overflow-hidden rounded-2xl ${
              i === 0 ? "col-span-2 row-span-2" : i === 3 || i === 4 ? "md:col-span-2" : i === 5 ? "col-span-2" : ""
            }`}
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={facility.image} alt="" loading="lazy" className="absolute inset-0 h-full w-full object-cover transition-transform duration-500 group-hover:scale-105" />
            <div className="absolute inset-0 bg-gradient-to-t from-surface/95 via-surface/20 to-transparent" />
            <figcaption className="absolute inset-x-0 bottom-0 flex flex-col gap-1 p-4">
              <span className="font-display text-[24px] uppercase leading-none sm:text-[28px]">{facility.title}</span>
              <span className="text-[13px] text-ink-dim">{facility.blurb}</span>
            </figcaption>
          </figure>
        ))}
      </div>
      <ul className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
        {AMENITIES.map((amenity) => (
          <li key={amenity.title} className="flex flex-col gap-2 rounded-2xl border border-surface-edge bg-surface-raised p-4">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent/10 text-accent">
              <Icon name={amenity.icon} />
            </span>
            <span className="text-[15px] font-semibold">{amenity.title}</span>
            <span className="text-[13px] leading-snug text-ink-dim">{amenity.blurb}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

function PersonalTraining() {
  return (
    <section id="training" className="scroll-mt-24 grid items-center gap-10 lg:grid-cols-2">
      <div className="relative">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/gym/personal-training.jpg" alt="" loading="lazy" className="aspect-[4/3] w-full rounded-3xl object-cover" />
      </div>
      <div className="flex flex-col gap-7">
        <SectionHeading title="Personal training">
          One-to-one sessions with a qualified coach, planned around your goals
          and training history. Your coach can see the workouts you log in the
          app. New members can book a free introductory session.
        </SectionHeading>
        <ul className="grid gap-3 sm:grid-cols-3">
          {PT_PACKAGES.map((pack) => (
            <li key={pack.name} className="flex flex-col gap-1 rounded-2xl border border-surface-edge bg-surface-raised p-4">
              <span className="text-[14px] font-semibold">{pack.name}</span>
              <span className="font-display text-[34px] leading-none">{pack.price ? money(pack.price) : "Free"}</span>
              <span className="text-[12px] text-ink-faint">
                {pack.price ? `${money(pack.price / pack.sessions)} per session. ` : ""}
                {pack.note}
              </span>
            </li>
          ))}
        </ul>
        <div>
          <Link href="/join?kind=tour&topic=pt" className="btn-cta">
            Book an intro session
          </Link>
        </div>
      </div>
    </section>
  );
}

const APP_FEATURES: [IconName, string, string][] = [
  ["dumbbell", "Workout log", "Record sets, reps and weights. Works without a signal and syncs later."],
  ["chart", "Progress", "Personal records, estimated one-rep max and training volume."],
  ["calendar", "Training plans", "Build a weekly plan, or generate one from your goals."],
  ["trophy", "Streaks", "Track consistency week to week."],
  ["message", "Support requests", "Report an issue and follow it through to resolution."],
  ["share", "Referrals", "Invite a friend to a free week pass."],
];

function MemberApp() {
  return (
    <section className="full-bleed relative overflow-hidden border-y border-surface-edge bg-surface-raised/70 py-20">
      <div className="mx-auto grid max-w-[1400px] items-center gap-12 px-4 sm:px-6 lg:grid-cols-[1.2fr_1fr]">
        <div className="flex flex-col gap-8">
          <SectionHeading title="Member app">
            Included with every membership.
          </SectionHeading>
          <ul className="grid gap-5 sm:grid-cols-2">
            {APP_FEATURES.map(([icon, title, body]) => (
              <li key={title} className="flex gap-3">
                <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-brand-cyan/10 text-brand-cyan">
                  <Icon name={icon} />
                </span>
                <span className="flex flex-col gap-0.5">
                  <span className="text-[15px] font-semibold">{title}</span>
                  <span className="text-[14px] leading-snug text-ink-dim">{body}</span>
                </span>
              </li>
            ))}
          </ul>
          <div className="flex flex-wrap gap-3">
            <Link href="/login" className="btn-cta">Member log in</Link>
            <Link href="/register" className="btn-outline">Create an account</Link>
          </div>
        </div>
        <div className="relative mx-auto w-full max-w-md">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/gym/app-member.jpg" alt="" loading="lazy" className="relative aspect-[4/5] w-full rounded-[32px] object-cover" />
        </div>
      </div>
    </section>
  );
}

function Visit() {
  return (
    <section id="visit" className="scroll-mt-24 grid gap-5 lg:grid-cols-3">
      <div className="flex flex-col gap-5 lg:col-span-1">
        <SectionHeading title="Visit us" />
        <OpenBadge className="self-start" />
        <address className="flex flex-col gap-1 text-[16px] not-italic">
          <span>{GYM.address.line1}</span>
          <span className="text-ink-dim">{GYM.address.line2}</span>
        </address>
        <div className="flex flex-wrap gap-3">
          <a href={GYM.address.mapsUrl} target="_blank" rel="noreferrer noopener" className="btn-outline">
            Get directions
          </a>
          <a href={`tel:${GYM.phone.replace(/[^\d+]/g, "")}`} className="btn-outline">
            Call {GYM.phone}
          </a>
        </div>
      </div>
      <Link href="/join?kind=tour" className="group relative flex min-h-[260px] flex-col justify-end overflow-hidden rounded-3xl p-7 lg:col-span-2">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/gym/facility-machines.jpg" alt="" loading="lazy" className="absolute inset-0 h-full w-full object-cover transition-transform duration-500 group-hover:scale-105" />
        <div className="absolute inset-0 bg-gradient-to-tr from-surface via-surface/70 to-transparent" />
        <div className="relative flex flex-col gap-3">
          <span className="font-display text-[44px] uppercase leading-none">Book a tour</span>
          <span className="max-w-md text-[15px] text-ink-dim">
            A member of our team will show you around and answer your
            questions. Choose a day and we&rsquo;ll confirm by email.
          </span>
          <span className="btn-cta self-start">Book a tour</span>
        </div>
      </Link>
    </section>
  );
}

function Faq() {
  return (
    <section id="faq" className="scroll-mt-24 mx-auto flex w-full max-w-3xl flex-col gap-8">
      <SectionHeading title="Frequently asked questions" center />
      <div className="flex flex-col gap-3">
        {FAQ.map(([question, answer]) => (
          <details key={question} className="group rounded-2xl border border-surface-edge bg-surface-raised px-5 open:border-accent/40">
            <summary className="flex min-h-[60px] cursor-pointer list-none items-center justify-between gap-4 text-[16px] font-semibold">
              {question}
              <span className="text-[22px] text-accent transition-transform group-open:rotate-45" aria-hidden>+</span>
            </summary>
            <p className="pb-5 text-[15px] leading-relaxed text-ink-dim">{answer}</p>
          </details>
        ))}
      </div>
    </section>
  );
}

function FinalCta() {
  return (
    <section className="full-bleed relative overflow-hidden">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src="/gym/join.jpg" alt="" loading="lazy" className="absolute inset-0 h-full w-full object-cover" />
      <div className="absolute inset-0 bg-gradient-to-r from-surface via-surface/80 to-surface/30" />
      <div className="relative mx-auto flex max-w-[1400px] flex-col items-start gap-6 px-4 py-24 sm:px-6">
        <h2 className="max-w-3xl font-display text-[52px] uppercase leading-[0.92] sm:text-[80px]">
          Try {GYM.name}
          <br />
          <span className="text-gradient">free for a week</span>
        </h2>
        <p className="max-w-lg text-[17px] text-ink-dim">
          Full access to the gym and all classes. {GYM.offer.detail}
        </p>
        <Link href="/join" className="btn-cta !min-h-[56px] !px-8 !text-[16px]">
          Get your free pass
        </Link>
      </div>
    </section>
  );
}
