/**
 * Everything specific to the gym lives here: name, contact, hours, prices,
 * classes, facilities, FAQ. Edit this file and the whole site follows.
 *
 * Every value below is a PLACEHOLDER - swap in the real details before launch.
 * Photos live in web/public/gym/ (see the README there).
 */

import type { IconName } from "@/components/icons";

export const GYM = {
  name: "YOUR GYM",
  shortName: "YG",
  tagline: "Gym, group classes and personal training.",
  description:
    "YOUR GYM offers free weights, strength racks, cardio, daily group classes "
    + "and personal training. Members log their workouts in the YOUR GYM app.",
  address: {
    line1: "123 Your Street",
    line2: "Your City 000000",
    mapsUrl: "https://maps.google.com/?q=123+Your+Street",
  },
  phone: "+91 00000 00000",
  email: "hello@yourgym.com",
  social: {
    instagram: "https://instagram.com/",
    facebook: "https://facebook.com/",
    tiktok: "https://tiktok.com/",
  },
  currency: "₹",
  // The headline offer, shown at the top of the home page.
  offer: {
    headline: "First week free",
    detail: "No joining fee. No payment details required.",
  },
} as const;

/** Opening hours, 24h clock. `null` means closed that day. */
export const HOURS: Record<Weekday, { open: string; close: string } | null> = {
  monday: { open: "05:00", close: "23:00" },
  tuesday: { open: "05:00", close: "23:00" },
  wednesday: { open: "05:00", close: "23:00" },
  thursday: { open: "05:00", close: "23:00" },
  friday: { open: "05:00", close: "22:00" },
  saturday: { open: "07:00", close: "20:00" },
  sunday: { open: "08:00", close: "18:00" },
};

export type Weekday =
  | "monday" | "tuesday" | "wednesday" | "thursday" | "friday" | "saturday" | "sunday";

export const WEEKDAYS: Weekday[] = [
  "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
];

export interface Plan {
  id: string;
  name: string;
  monthly: number;
  blurb: string;
  features: string[];
  popular?: boolean;
  tone: "cyan" | "pink" | "yellow";
}

export const PLANS: Plan[] = [
  {
    id: "flex",
    name: "Flex",
    monthly: 1499,
    blurb: "Full gym floor access during opening hours.",
    features: [
      "Full gym floor access",
      "YOUR GYM app with workout tracking",
      "Free induction with a coach",
      "Lockers and showers",
    ],
    tone: "cyan",
  },
  {
    id: "unlimited",
    name: "Unlimited",
    monthly: 2499,
    blurb: "Gym access plus all group classes.",
    features: [
      "Everything in Flex",
      "Unlimited group classes",
      "1 guest pass every month",
      "Recovery zone access",
      "Freeze free for up to 2 months a year",
    ],
    popular: true,
    tone: "pink",
  },
  {
    id: "elite",
    name: "Elite",
    monthly: 4999,
    blurb: "Everything in Unlimited plus monthly personal training.",
    features: [
      "Everything in Unlimited",
      "1 personal-training session a month",
      "Quarterly body-composition check-in",
      "Towel service and priority class booking",
    ],
    tone: "yellow",
  },
];

/** Pay for a year up front: this fraction off. */
export const ANNUAL_DISCOUNT = 0.15;

/** Membership terms, shown next to the prices. */
export const PROMISES = [
  "No joining fee",
  "Cancel with 30 days' notice",
  "Membership freezes available",
  "Student, senior and military rates: 20% off",
];

export interface GymClass {
  time: string; // 24h
  name: string;
  minutes: number;
  intensity: 1 | 2 | 3;
  room: string;
  coach: string;
}

const STRENGTH: Omit<GymClass, "time"> = { name: "Strength Club", minutes: 50, intensity: 2, room: "Rack zone", coach: "Coach A" };
const HIIT: Omit<GymClass, "time"> = { name: "HIIT Burn", minutes: 45, intensity: 3, room: "Studio 1", coach: "Coach B" };
const SPIN: Omit<GymClass, "time"> = { name: "Rhythm Ride", minutes: 45, intensity: 3, room: "Cycle studio", coach: "Coach C" };
const YOGA: Omit<GymClass, "time"> = { name: "Flow Yoga", minutes: 60, intensity: 1, room: "Studio 2", coach: "Coach D" };
const CORE: Omit<GymClass, "time"> = { name: "Core & Mobility", minutes: 30, intensity: 1, room: "Studio 2", coach: "Coach D" };
const BOX: Omit<GymClass, "time"> = { name: "Boxing Conditioning", minutes: 45, intensity: 3, room: "Studio 1", coach: "Coach B" };
const PUMP: Omit<GymClass, "time"> = { name: "Barbell Pump", minutes: 45, intensity: 2, room: "Studio 1", coach: "Coach A" };

export const TIMETABLE: Record<Weekday, GymClass[]> = {
  monday: [
    { time: "06:15", ...HIIT }, { time: "12:15", ...CORE },
    { time: "17:30", ...STRENGTH }, { time: "18:30", ...SPIN }, { time: "19:30", ...YOGA },
  ],
  tuesday: [
    { time: "06:15", ...SPIN }, { time: "12:15", ...PUMP },
    { time: "17:30", ...BOX }, { time: "18:30", ...HIIT },
  ],
  wednesday: [
    { time: "06:15", ...STRENGTH }, { time: "12:15", ...CORE },
    { time: "17:30", ...SPIN }, { time: "18:30", ...PUMP }, { time: "19:30", ...YOGA },
  ],
  thursday: [
    { time: "06:15", ...HIIT }, { time: "12:15", ...SPIN },
    { time: "17:30", ...BOX }, { time: "18:30", ...STRENGTH },
  ],
  friday: [
    { time: "06:15", ...PUMP }, { time: "12:15", ...HIIT }, { time: "17:30", ...SPIN },
  ],
  saturday: [
    { time: "08:30", ...STRENGTH }, { time: "09:30", ...HIIT }, { time: "10:30", ...YOGA },
  ],
  sunday: [{ time: "09:00", ...SPIN }, { time: "10:30", ...YOGA }],
};

export const FACILITIES = [
  { title: "Free weights", blurb: "Dumbbells up to 50 kg and adjustable benches.", image: "/gym/facility-free-weights.jpg" },
  { title: "Strength racks", blurb: "Squat racks, platforms and calibrated plates.", image: "/gym/facility-strength.jpg" },
  { title: "Cardio deck", blurb: "Treadmills, rowers, bikes and stair climbers.", image: "/gym/facility-cardio.jpg" },
  { title: "Machines & cycle", blurb: "Selectorised machines and a full cycle studio.", image: "/gym/facility-machines.jpg" },
  { title: "Group studios", blurb: "Two studios for classes, yoga and mobility.", image: "/gym/facility-studio.jpg" },
  { title: "Functional zone", blurb: "Turf, sleds, battle ropes and kettlebells.", image: "/gym/facility-functional.jpg" },
];

export const AMENITIES: { icon: IconName; title: string; blurb: string }[] = [
  { icon: "flame", title: "Recovery zone", blurb: "Sauna, foam rollers and massage guns." },
  { icon: "shower", title: "Changing rooms", blurb: "Showers, day lockers and hair dryers." },
  { icon: "parking", title: "Free parking", blurb: "On-site parking for members." },
  { icon: "wifi", title: "Free Wi-Fi", blurb: "Available throughout the building." },
  { icon: "cup", title: "Shake bar", blurb: "Protein shakes and coffee at reception." },
  { icon: "coach", title: "Floor coaches", blurb: "Technique advice at no extra cost." },
];

export const PT_PACKAGES = [
  { name: "Intro session", price: 0, note: "Free for new members", sessions: 1 },
  { name: "5-session pack", price: 5000, note: "Save on the single rate", sessions: 5 },
  { name: "10-session pack", price: 9000, note: "Best value", sessions: 10 },
];

export const FAQ = [
  ["Can I try the gym before I join?", "Yes. Request a free week pass online and give your name at reception on your first visit. No payment details are required."],
  ["Is there a joining fee or a contract?", "No joining fee. Memberships roll month to month; cancel with 30 days' notice."],
  ["Can I freeze my membership?", "Unlimited and Elite members can freeze free for up to two months a year. Flex members can freeze for a small monthly fee. Ask in the app under Support."],
  ["Do I need to book classes?", "Classes are first come, first served. Arrive 5 minutes early; Elite members get priority at the door."],
  ["What is included in the member app?", "A workout log, weekly training plans, progress and personal records, the class timetable and support requests. Workouts can be logged without a signal and sync later."],
  ["How do I report a problem?", "Log in and open Support. You can raise a request, follow its status and read the reply from our team."],
] as const;

/** Equipment the gym has, using the app's canonical ids. New members start
 *  with this, so the exercise library only shows what the gym can load. */
export const GYM_EQUIPMENT = [
  "dumbbell", "barbell", "bench", "cable", "machine", "smith-machine",
  "pull-up-bar", "dip-bars", "kettlebell", "resistance-band", "ez-bar",
  "medicine-ball", "stability-ball", "bodyweight",
];

// --- helpers ----------------------------------------------------------------

/** Whole rupees with Indian digit grouping: ₹1,499, ₹1,02,000. */
export function money(amount: number): string {
  return `${GYM.currency}${Math.round(amount).toLocaleString("en-IN")}`;
}

export function todayKey(now = new Date()): Weekday {
  return WEEKDAYS[(now.getDay() + 6) % 7];
}

function minutesOf(hhmm: string): number {
  const [h, m] = hhmm.split(":").map(Number);
  return h * 60 + m;
}

export function formatTime(hhmm: string): string {
  const [h, m] = hhmm.split(":").map(Number);
  const suffix = h >= 12 ? "pm" : "am";
  const hour = h % 12 || 12;
  return m ? `${hour}:${String(m).padStart(2, "0")}${suffix}` : `${hour}${suffix}`;
}

/** "Open now, closes 11pm" / "Closed, opens 7am Saturday". */
export function openStatus(now = new Date()): { open: boolean; label: string } {
  const day = todayKey(now);
  const minutes = now.getHours() * 60 + now.getMinutes();
  const today = HOURS[day];
  if (today && minutes >= minutesOf(today.open) && minutes < minutesOf(today.close)) {
    return { open: true, label: `Open now · closes ${formatTime(today.close)}` };
  }
  if (today && minutes < minutesOf(today.open)) {
    return { open: false, label: `Closed · opens ${formatTime(today.open)}` };
  }
  for (let i = 1; i <= 7; i++) {
    const next = WEEKDAYS[(WEEKDAYS.indexOf(day) + i) % 7];
    const hours = HOURS[next];
    if (hours) {
      const when = i === 1 ? "tomorrow" : next[0].toUpperCase() + next.slice(1);
      return { open: false, label: `Closed · opens ${formatTime(hours.open)} ${when}` };
    }
  }
  return { open: false, label: "Closed" };
}

/** Classes still to come today, soonest first. */
export function upcomingClasses(now = new Date()): GymClass[] {
  const minutes = now.getHours() * 60 + now.getMinutes();
  return TIMETABLE[todayKey(now)].filter((c) => minutesOf(c.time) + c.minutes > minutes);
}

export function isLive(c: GymClass, now = new Date()): boolean {
  const minutes = now.getHours() * 60 + now.getMinutes();
  return minutes >= minutesOf(c.time) && minutes < minutesOf(c.time) + c.minutes;
}
