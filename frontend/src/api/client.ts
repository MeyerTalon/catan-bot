/**
 * Typed HTTP client generated from the FastAPI OpenAPI schema.
 * Do not hand-write request/response types — regenerate with `npm run generate:api`.
 */

import createClient from "openapi-fetch";
import type { paths } from "./schema";
import { getAccessToken } from "../lib/session";

const getBaseUrl = (): string => {
  const url = import.meta.env.VITE_BACKEND_URL;
  if (url) return url.replace(/\/$/, "");
  return "http://localhost:8000";
};

export const api = createClient<paths>({
  baseUrl: getBaseUrl(),
});

api.use({
  onRequest({ request }) {
    const token = getAccessToken();
    if (token) {
      request.headers.set("Authorization", `Bearer ${token}`);
    }
    return request;
  },
});

export function apiErrorMessage(error: unknown, fallback = "Request failed"): string {
  if (error && typeof error === "object" && "detail" in error) {
    const detail = (error as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((item) =>
          item && typeof item === "object" && "msg" in item
            ? String((item as { msg: unknown }).msg)
            : String(item)
        )
        .join(", ");
    }
  }
  if (error instanceof Error) return error.message;
  return fallback;
}
