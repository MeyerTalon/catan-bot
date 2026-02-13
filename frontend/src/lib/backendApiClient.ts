/**
 * Client for the Catan backend API.
 * Base URL is configurable via VITE_BACKEND_URL (e.g. Render); defaults to localhost:8000 in dev.
 */

const getBaseUrl = (): string => {
  const url = import.meta.env.VITE_BACKEND_URL;
  if (url) return url.replace(/\/$/, ""); // strip trailing slash
  return "http://localhost:8000";
};

const baseUrl = getBaseUrl();

/** Session returned by backend auth endpoints (matches Supabase Auth session shape). */
export type AuthSession = {
  access_token: string;
  refresh_token: string;
  expires_in?: number;
  token_type?: string;
  user?: { id: string; email?: string; user_metadata?: Record<string, unknown> };
};

/** Error shape from backend (e.g. 4xx). */
export type BackendError = { detail: string };

async function handleResponse<T>(res: Response): Promise<T> {
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const message =
      typeof (data as BackendError).detail === "string"
        ? (data as BackendError).detail
        : Array.isArray((data as { detail?: unknown }).detail)
          ? (data as { detail: unknown[] }).detail.map(String).join(", ")
          : res.statusText || "Request failed";
    throw new Error(message);
  }
  return data as T;
}

/**
 * Log in with email and password via the backend (which proxies to Supabase Auth).
 * Returns the session so the frontend can call supabase.auth.setSession().
 */
export async function login(email: string, password: string): Promise<AuthSession> {
  const res = await fetch(`${baseUrl}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: email.trim(), password }),
  });
  return handleResponse<AuthSession>(res);
}

/**
 * Sign up with email, optional username, and password via the backend.
 * Returns the session (or confirmation info) so the frontend can set the session if applicable.
 */
export async function signup(params: {
  email: string;
  password: string;
  username?: string;
}): Promise<AuthSession & { message?: string }> {
  const res = await fetch(`${baseUrl}/auth/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email: params.email.trim(),
      password: params.password,
      username: params.username?.trim() || undefined,
    }),
  });
  return handleResponse<AuthSession & { message?: string }>(res);
}
