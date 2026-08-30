/**
 * Display-side unit handling.
 *
 * Mirrors app/core/formulas.py (PLAN.md D7). Storage is always kg; this file
 * only ever runs at the presentation boundary.
 */

export const LB_PER_KG = 0.45359237;

export function kgToLb(kg: number): number {
  return kg / LB_PER_KG;
}

export function lbToKg(lb: number): number {
  return lb * LB_PER_KG;
}

export function toDisplay(kg: number, unit: "kg" | "lb"): number {
  return unit === "kg" ? kg : kgToLb(kg);
}

export function formatWeight(kg: string | number | null, unit: "kg" | "lb"): string {
  if (kg === null) return "—";
  const value = toDisplay(typeof kg === "string" ? parseFloat(kg) : kg, unit);
  const rounded = Math.round(value * 100) / 100;
  return `${rounded % 1 === 0 ? rounded.toFixed(0) : rounded.toFixed(1)} ${unit}`;
}

export function humanize(slug: string): string {
  return slug.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}
