"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { useSession } from "@/lib/session";

const MEMBER_LINKS = [
  { href: "/session", label: "Train" },
  { href: "/plan", label: "Week" },
  { href: "/classes", label: "Classes" },
  { href: "/progress", label: "Progress" },
  { href: "/history", label: "History" },
  { href: "/coach", label: "Coach" },
  { href: "/support", label: "Support" },
  { href: "/profile", label: "Profile" },
];

const PUBLIC_LINKS = [
  { href: "/#memberships", label: "Memberships" },
  { href: "/#classes", label: "Classes" },
  { href: "/#facilities", label: "Facilities" },
  { href: "/#training", label: "Personal training" },
];

export function Nav() {
  const { profile, loading } = useSession();
  const pathname = usePathname();

  if (loading) return <span className="text-[13px] text-ink-faint">…</span>;

  if (!profile) {
    return (
      <nav className="flex items-center gap-1">
        <div className="mr-2 hidden items-center gap-1 lg:flex">
          {PUBLIC_LINKS.map((link) => (
            <Link key={link.href} href={link.href} className="rounded-full px-3 py-2 text-[14px] text-ink-dim hover:text-ink">
              {link.label}
            </Link>
          ))}
        </div>
        <Link href="/login" className="whitespace-nowrap rounded-full px-3 py-2 text-[14px] font-semibold text-ink-dim hover:text-ink">
          <span className="sm:hidden">Log in</span>
          <span className="hidden sm:inline">Member log in</span>
        </Link>
        <Link href="/join" className="btn-cta !min-h-[40px] whitespace-nowrap !px-4 !text-[14px]">
          Free pass
        </Link>
      </nav>
    );
  }

  const links = profile.is_staff ? [...MEMBER_LINKS, { href: "/staff", label: "Staff" }] : MEMBER_LINKS;
  return (
    <nav className="hidden items-center gap-0.5 md:flex">
      {links.map((link) => {
        const active = pathname === link.href || pathname.startsWith(`${link.href}/`);
        return (
          <Link
            key={link.href}
            href={link.href}
            aria-current={active ? "page" : undefined}
            className={`rounded-full px-3 py-2 text-[14px] font-medium transition-colors ${
              active ? "bg-accent/15 text-accent" : "text-ink-dim hover:text-ink"
            }`}
          >
            {link.label}
          </Link>
        );
      })}
    </nav>
  );
}

const TABS = [
  { href: "/", label: "Home", icon: "M3 11 12 4l9 7v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z" },
  { href: "/session", label: "Train", icon: "M4 10h3v4H4zM17 10h3v4h-3zM7 11h10v2H7zM2 11h2v2H2zM20 11h2v2h-2z" },
  { href: "/classes", label: "Classes", icon: "M4 6h16v14H4zM4 10h16M9 3v4M15 3v4" },
  { href: "/support", label: "Support", icon: "M4 5h16v11H9l-5 4z" },
];

/** Phones: a thumb-reach tab bar instead of a header full of links. */
export function MobileTabBar() {
  const { profile, logout } = useSession();
  const pathname = usePathname();
  const [more, setMore] = useState(false);

  useEffect(() => setMore(false), [pathname]);

  if (!profile) return null;

  const extra = [
    { href: "/plan", label: "Weekly plan" },
    { href: "/progress", label: "Progress" },
    { href: "/history", label: "History" },
    { href: "/exercises", label: "Exercises" },
    { href: "/coach", label: "Workout builder" },
    { href: "/profile", label: "Profile & settings" },
    ...(profile.is_staff ? [{ href: "/staff", label: "Staff inbox" }] : []),
  ];

  return (
    <>
      {more && (
        <div className="fixed inset-0 z-30 bg-black/60 md:hidden" onClick={() => setMore(false)}>
          <div
            className="absolute inset-x-3 bottom-[84px] rounded-3xl border border-surface-edge bg-surface-raised p-2 shadow-2xl"
            onClick={(event) => event.stopPropagation()}
          >
            {extra.map((item) => (
              <Link key={item.href} href={item.href} className="flex min-h-tap items-center rounded-2xl px-4 text-[16px] hover:bg-ink/5">
                {item.label}
              </Link>
            ))}
            <button
              onClick={() => void logout()}
              className="flex min-h-tap w-full items-center rounded-2xl px-4 text-left text-[16px] text-ink-dim hover:bg-ink/5"
            >
              Log out
            </button>
          </div>
        </div>
      )}
      <nav
        className="fixed inset-x-0 bottom-0 z-30 border-t border-surface-edge bg-surface/95 pb-[env(safe-area-inset-bottom)] backdrop-blur-md md:hidden"
        aria-label="Main"
      >
        <ul className="grid grid-cols-5">
          {TABS.map((tab) => {
            const active = tab.href === "/" ? pathname === "/" : pathname.startsWith(tab.href);
            return (
              <li key={tab.href}>
                <Link
                  href={tab.href}
                  aria-current={active ? "page" : undefined}
                  className={`flex min-h-[64px] flex-col items-center justify-center gap-1 text-[11px] font-semibold ${
                    active ? "text-accent" : "text-ink-faint"
                  }`}
                >
                  <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinejoin="round" aria-hidden>
                    <path d={tab.icon} />
                  </svg>
                  {tab.label}
                </Link>
              </li>
            );
          })}
          <li>
            <button
              onClick={() => setMore((open) => !open)}
              aria-expanded={more}
              className={`flex min-h-[64px] w-full flex-col items-center justify-center gap-1 text-[11px] font-semibold ${
                more ? "text-accent" : "text-ink-faint"
              }`}
            >
              <svg viewBox="0 0 24 24" className="h-6 w-6" fill="currentColor" aria-hidden>
                <circle cx="5" cy="12" r="2" /><circle cx="12" cy="12" r="2" /><circle cx="19" cy="12" r="2" />
              </svg>
              More
            </button>
          </li>
        </ul>
      </nav>
    </>
  );
}

/** Desktop log-out, kept out of the main link row. */
export function AccountMenu() {
  const { profile, logout } = useSession();
  if (!profile) return null;
  return (
    <button
      onClick={() => void logout()}
      className="hidden rounded-full px-3 py-2 text-[13px] text-ink-faint hover:text-ink md:block"
    >
      Log out
    </button>
  );
}
