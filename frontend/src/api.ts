// Thin fetch wrapper. Same origin, so the session cookie travels automatically; every write
// carries the CSRF token in the X-CSRFToken header.

export type Role = "admin" | "collaborator";

export interface User {
  id: number;
  email: string;
  name: string;
  role: Role;
  is_active: boolean;
  created_at: string;
}

export interface Promoter {
  id: number;
  public_id: string;
  name: string;
  email: string | null;
  archived: boolean;
  created_at: string;
}

export type CrmStatus = "pending" | "synced" | "failed";

export interface Lead {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
  phone: string | null;
  promoter: Promoter | null;
  crm_status: CrmStatus;
  crm_id: string | null;
  created_at: string;
}

export interface AppConfig {
  brand_name: string;
  brand_primary_color: string;
  brand_logo_url: string | null;
  crm_provider: string;
  demo: { enabled: boolean; email?: string; password?: string };
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public fields: Record<string, string> = {},
  ) {
    super(message);
  }
}

let csrfToken: string | null = null;

export function setCsrfToken(token: string) {
  csrfToken = token;
}

async function ensureCsrf(): Promise<string> {
  if (!csrfToken) {
    const res = await fetch("/api/auth/csrf", { credentials: "same-origin" });
    csrfToken = (await res.json()).csrf_token as string;
  }
  return csrfToken;
}

export async function api<T>(path: string, init: { method?: string; body?: unknown } = {}): Promise<T> {
  const method = init.method ?? "GET";
  const headers: Record<string, string> = { Accept: "application/json" };
  if (method !== "GET") {
    headers["Content-Type"] = "application/json";
    headers["X-CSRFToken"] = await ensureCsrf();
  }
  const res = await fetch(path, {
    method,
    headers,
    credentials: "same-origin",
    body: init.body === undefined ? undefined : JSON.stringify(init.body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    if (data.error === "csrf_failed") csrfToken = null; // token expired with the session
    throw new ApiError(res.status, data.error ?? "error", data.message ?? res.statusText, data.fields);
  }
  return data as T;
}
