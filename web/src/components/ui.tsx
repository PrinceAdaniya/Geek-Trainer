"use client";

/**
 * The primitives.
 *
 * Every interactive control is at least 44px tall (SPECIFICATIONS.MD 11.4) and
 * every input is labelled (Sec 26). These are the constraints that make the
 * app usable one-handed in a gym, so they live in the primitives rather than
 * being remembered per screen.
 */

import { forwardRef } from "react";

export function Button({
  variant = "primary",
  className = "",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "ghost" | "danger" }) {
  const styles = {
    primary: "bg-accent text-surface font-semibold hover:bg-accent/90 disabled:bg-accent-dim",
    ghost: "bg-surface-raised text-ink border border-surface-edge hover:border-ink-faint",
    danger: "bg-transparent text-bad border border-bad/40 hover:bg-bad/10",
  }[variant];
  return (
    <button
      className={`min-h-tap rounded-xl px-4 text-[15px] transition-colors disabled:opacity-50 ${styles} ${className}`}
      {...props}
    />
  );
}

export const Input = forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement> & { label: string }>(
  function Input({ label, id, className = "", ...props }, ref) {
    const inputId = id ?? `f-${label.toLowerCase().replace(/\W+/g, "-")}`;
    return (
      <div className="flex flex-col gap-1.5">
        <label htmlFor={inputId} className="text-[13px] text-ink-dim">
          {label}
        </label>
        <input
          ref={ref}
          id={inputId}
          className={`min-h-tap rounded-xl border border-surface-edge bg-surface-raised px-3.5 text-[16px] text-ink placeholder:text-ink-faint focus:border-accent ${className}`}
          {...props}
        />
      </div>
    );
  },
);

export function Select({
  label,
  children,
  id,
  ...props
}: React.SelectHTMLAttributes<HTMLSelectElement> & { label: string }) {
  const selectId = id ?? `s-${label.toLowerCase().replace(/\W+/g, "-")}`;
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={selectId} className="text-[13px] text-ink-dim">
        {label}
      </label>
      <select
        id={selectId}
        className="min-h-tap rounded-xl border border-surface-edge bg-surface-raised px-3 text-[15px] text-ink focus:border-accent"
        {...props}
      >
        {children}
      </select>
    </div>
  );
}

export function Chip({
  selected,
  className = "",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { selected?: boolean }) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      className={`min-h-tap rounded-full border px-4 text-[14px] transition-colors ${
        selected
          ? "border-accent bg-accent/15 text-accent"
          : "border-surface-edge bg-surface-raised text-ink-dim hover:border-ink-faint"
      } ${className}`}
      {...props}
    />
  );
}

export function ErrorNote({ children }: { children: React.ReactNode }) {
  if (!children) return null;
  return (
    <p role="alert" className="rounded-xl border border-bad/40 bg-bad/10 px-3.5 py-2.5 text-[14px] text-bad">
      {children}
    </p>
  );
}

export function Empty({ title, hint, action }: { title: string; hint?: string; action?: React.ReactNode }) {
  // Sec 27 - every empty state leads to the next action.
  return (
    <div className="flex flex-col items-center gap-3 rounded-2xl border border-dashed border-surface-edge px-6 py-12 text-center">
      <p className="text-[15px] text-ink">{title}</p>
      {hint && <p className="max-w-sm text-[14px] text-ink-dim">{hint}</p>}
      {action}
    </div>
  );
}

export function Spinner({ label = "Loading" }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 py-8 text-[14px] text-ink-dim" role="status">
      <span className="h-3 w-3 animate-pulse rounded-full bg-accent" />
      {label}…
    </div>
  );
}
