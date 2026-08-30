"use client";

/**
 * The offline outbox. SPECIFICATIONS.MD Sec 12, PLAN.md D2/D3.
 *
 * The rule that shapes this file: **logging a set must never await the
 * network**. So every mutation is written to IndexedDB first and the UI is
 * updated from local state; a background drain posts the queue to /sync when
 * it can. A failed drain never discards anything.
 *
 * The server is still authoritative (D2) - after a successful drain the client
 * replaces its provisional view with what /sync hands back.
 */

import Dexie, { type Table } from "dexie";
import { api } from "./api";
import type { WorkoutSession } from "./types";

export type MutationType =
  | "session.start"
  | "session.update"
  | "session.finish"
  | "session.cancel"
  | "session_exercise.add"
  | "session_exercise.update"
  | "session_exercise.delete"
  | "set.upsert"
  | "set.delete";

export interface QueuedMutation {
  id: string;
  type: MutationType;
  at: string;
  payload: Record<string, unknown>;
  attempts: number;
}

export interface CachedSession {
  key: string; // "active"
  session: WorkoutSession | null;
  cachedAt: string;
}

class GeekTrainerDB extends Dexie {
  outbox!: Table<QueuedMutation, string>;
  cache!: Table<CachedSession, string>;

  constructor() {
    super("geek-trainer");
    this.version(1).stores({
      outbox: "id, at",
      cache: "key",
    });
  }
}

let db: GeekTrainerDB | null = null;

function open(): GeekTrainerDB | null {
  // IndexedDB is unavailable in some private-browsing modes. The app must
  // still work there, just without the offline guarantee.
  if (typeof window === "undefined") return null;
  try {
    db ??= new GeekTrainerDB();
    return db;
  } catch {
    return null;
  }
}

export async function enqueue(
  type: MutationType,
  payload: Record<string, unknown>,
  id: string,
): Promise<void> {
  const handle = open();
  if (!handle) return;
  try {
    await handle.outbox.put({
      id,
      type,
      at: new Date().toISOString(),
      payload,
      attempts: 0,
    });
  } catch {
    /* storage refused - the direct API call is still the primary path */
  }
}

export async function pending(): Promise<number> {
  const handle = open();
  if (!handle) return 0;
  try {
    return await handle.outbox.count();
  } catch {
    return 0;
  }
}

export interface DrainResult {
  sent: number;
  rejected: { id: string | null; code: string; message: string }[];
  activeSession: WorkoutSession | null;
}

/** Post everything queued. Only what the server accepted is removed. */
export async function drain(): Promise<DrainResult | null> {
  const handle = open();
  if (!handle) return null;

  let queued: QueuedMutation[];
  try {
    queued = await handle.outbox.orderBy("at").limit(200).toArray();
  } catch {
    return null;
  }
  if (queued.length === 0) return { sent: 0, rejected: [], activeSession: null };

  const response = await api.post<{
    applied: string[];
    duplicates: string[];
    rejected: { id: string | null; code: string; message: string }[];
    active_session: WorkoutSession | null;
  }>("/sync", {
    mutations: queued.map(({ id, type, at, payload }) => ({ id, type, at, payload })),
  });

  // Applied, duplicated and rejected are all settled - retrying a rejection
  // would loop forever. Anything the server did not mention stays queued.
  const settled = [
    ...response.applied,
    ...response.duplicates,
    ...response.rejected.map((r) => r.id).filter((id): id is string => Boolean(id)),
  ];
  try {
    await handle.outbox.bulkDelete(settled);
  } catch {
    /* the next drain will settle them again - duplicates are no-ops */
  }

  return {
    sent: response.applied.length,
    rejected: response.rejected,
    activeSession: response.active_session,
  };
}

export async function cacheActiveSession(session: WorkoutSession | null): Promise<void> {
  const handle = open();
  if (!handle) return;
  try {
    await handle.cache.put({
      key: "active",
      session,
      cachedAt: new Date().toISOString(),
    });
  } catch {
    /* nothing to do */
  }
}

export async function readCachedSession(): Promise<WorkoutSession | null> {
  const handle = open();
  if (!handle) return null;
  try {
    return (await handle.cache.get("active"))?.session ?? null;
  } catch {
    return null;
  }
}
