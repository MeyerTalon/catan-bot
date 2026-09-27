/**
 * Typed HTTP client generated from the FastAPI OpenAPI schema.
 * Do not hand-write request/response types — regenerate with `mise run api`.
 */

import createClient from "openapi-fetch";
import type { paths } from "./schema";
import {
  clearSession,
  getAccessToken,
  getSession,
  setSession,
} from "../lib/session";

// refresh this long before the access token expires, so a long game never
// sends an expired token
const REFRESH_MARGIN_MS = 60_000;

const getBaseUrl = (): string => {
  const url = import.meta.env.VITE_BACKEND_URL;
  if (url) return url.replace(/\/$/, "");
  return "http://localhost:8000";
};

export const api = createClient<paths>({
  baseUrl: getBaseUrl(),
});

function tokenExpiresAt(token: string): number | null {
  try {
    const payload = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    const exp = (JSON.parse(atob(payload)) as { exp?: unknown }).exp;
    return typeof exp === "number" ? exp * 1000 : null;
  } catch {
    return null;
  }
}

let refreshing: Promise<void> | null = null;

async function refreshSession(): Promise<void> {
  const session = getSession();
  if (!session?.refresh_token) return;
  // plain fetch: going through `api` would re-enter this middleware
  const response = await fetch(`${getBaseUrl()}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      refresh_token: session.refresh_token,
      username: session.user.email ?? undefined,
    }),
  });
  if (response.ok) {
    setSession(await response.json());
  } else {
    clearSession();
  }
}

function isAuthRoute(request: Request): boolean {
  return new URL(request.url).pathname.includes("/auth/");
}

api.use({
  async onRequest({ request }) {
    if (!isAuthRoute(request)) {
      const token = getAccessToken();
      const expiresAt = token ? tokenExpiresAt(token) : null;
      if (expiresAt !== null && expiresAt - Date.now() < REFRESH_MARGIN_MS) {
        refreshing ??= refreshSession()
          .catch(() => undefined)
          .finally(() => {
            refreshing = null;
          });
        await refreshing;
      }
    }
    const token = getAccessToken();
    if (token) {
      request.headers.set("Authorization", `Bearer ${token}`);
    }
    return request;
  },
  onResponse({ request, response }) {
    // a token the backend no longer accepts cannot be fixed by retrying
    if (response.status === 401 && !isAuthRoute(request)) clearSession();
    return response;
  },
});

export function apiErrorMessage(
  error: unknown,
  fallback = "Request failed",
): string {
  if (error && typeof error === "object" && "detail" in error) {
    const detail = (error as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((item) =>
          item && typeof item === "object" && "msg" in item
            ? String((item as { msg: unknown }).msg)
            : String(item),
        )
        .join(", ");
    }
  }
  if (error instanceof Error) return error.message;
  return fallback;
}
