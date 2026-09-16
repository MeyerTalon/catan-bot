/**
 * Client-side session storage for Cognito tokens returned by the backend.
 * Types come from the generated OpenAPI schema so they stay aligned with the API.
 */

import type { components } from "../api/schema";

export type AuthSession = components["schemas"]["AuthSessionResponse"];

const STORAGE_KEY = "catan.session";

const listeners = new Set<() => void>();

function notify(): void {
  listeners.forEach((listener) => listener());
}

export function subscribeToSession(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function getSession(): AuthSession | null {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthSession;
  } catch {
    localStorage.removeItem(STORAGE_KEY);
    return null;
  }
}

export function setSession(session: AuthSession): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
  notify();
}

export function clearSession(): void {
  localStorage.removeItem(STORAGE_KEY);
  notify();
}

export function getAccessToken(): string | null {
  return getSession()?.access_token ?? null;
}
