"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useSession } from "@/lib/session";

const LINKS = [
  { href: "/session", label: "Train" },
  { href: "/plan", label: "Week" },
  { href: "/history", label: "History" },
  { href: "/profile", label: "Profile" },
];

export function Nav() {
  const { profile, loading, logout } = useSession();
  const pathname = usePathname();

  if (loading) return <span className="text-[13px] text-ink-faint">…</span>;

  if (!profile) {
    return (
      <nav className="flex items-center gap-1">
        <Link href="/login" className="rounded-lg px-3 py-2 text-[14px] text-ink-dim hover:text-ink">
          Log in
        </Link>
        <Link
          href="/register"
          className="rounded-lg bg-accent px-3 py-2 text-[14px] font-medium text-surface"
        >
          Sign up
        </Link>
      </nav>
    );
  }

  return (
    <nav className="flex items-center gap-1">
      {LINKS.map((link) => (
        <Link
          key={link.href}
          href={link.href}
          aria-current={pathname === link.href ? "page" : undefined}
          className={`rounded-lg px-3 py-2 text-[14px] ${
            pathname === link.href ? "text-accent" : "text-ink-dim hover:text-ink"
          }`}
        >
          {link.label}
        </Link>
      ))}
      <button
        onClick={() => void logout()}
        className="rounded-lg px-3 py-2 text-[14px] text-ink-faint hover:text-ink"
      >
        Log out
      </button>
    </nav>
  );
}
