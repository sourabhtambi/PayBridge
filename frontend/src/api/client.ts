import { API_BASE_URL } from "../config/env";
import { SESSION_STORAGE_KEY } from "../config/constants";
import type { Session } from "../types/domain";

export const DEFAULT_SESSION: Session = { role: "customer", customerId: "cus_001" };

export function loadSession(): Session {
  try {
    const raw = window.localStorage.getItem(SESSION_STORAGE_KEY);
    if (raw) {
      const s = JSON.parse(raw) as Session;
      if (s.role === "customer" || s.role === "ops" || s.role === "admin") return s;
    }
  } catch {
    /* corrupt or blocked storage: fall back to default */
  }
  return DEFAULT_SESSION;
}

export function saveSession(session: Session): void {
  try {
    window.localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(session));
  } catch {
    /* storage blocked */
  }
}

export function authHeaders(session: Session = loadSession()): Record<string, string> {
  const headers: Record<string, string> = { "X-Role": session.role };
  if (session.customerId) headers["X-Customer-Id"] = session.customerId;
  return headers;
}

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { ...authHeaders(), ...(init.headers as Record<string, string> | undefined) },
  });
  if (!res.ok) throw new Error(`Request failed: ${res.status}`);
  return (await res.json()) as T;
}
