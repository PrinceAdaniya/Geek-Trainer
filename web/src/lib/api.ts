/**
 * The API client.
 *
 * Everything goes through the same-origin `/api/v1` proxy (next.config.mjs),
 * so the session cookie needs no special handling. One error shape in, one
 * error shape out - matching SPECIFICATIONS.MD 23.1.
 */

export const API = "/api/v1";

export class ApiError extends Error {
  code: string;
  status: number;
  details: Record<string, unknown>;

  constructor(status: number, code: string, message: string, details: Record<string, unknown> = {}) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API}${path}`, {
      credentials: "same-origin",
      headers: { "content-type": "application/json", ...(init.headers ?? {}) },
      ...init,
    });
  } catch {
    // Sec 27 - a network failure says what happened and whether anything was lost.
    throw new ApiError(0, "offline", "Cannot reach the server. Nothing was saved.");
  }

  if (response.status === 204) return undefined as T;

  const text = await response.text();
  const body = text ? JSON.parse(text) : null;

  if (!response.ok) {
    const err = body?.error ?? {};
    throw new ApiError(
      response.status,
      err.code ?? "error",
      err.message ?? "Something went wrong.",
      err.details ?? {},
    );
  }
  return body as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: JSON.stringify(body ?? {}) }),
  put: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "PUT", body: JSON.stringify(body ?? {}) }),
  del: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};

export function query(params: Record<string, string | number | boolean | string[] | undefined>) {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === "" || value === false) continue;
    if (Array.isArray(value)) value.forEach((v) => search.append(key, v));
    else search.set(key, String(value));
  }
  const qs = search.toString();
  return qs ? `?${qs}` : "";
}
