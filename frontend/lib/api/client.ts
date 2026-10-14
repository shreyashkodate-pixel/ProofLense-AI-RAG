/**
 * ProofLens AI — Centralized Typed API Client
 * Enforces X-Workspace-Key header injection, RFC 7807 parsing, and unauthorized event dispatching.
 */

import { getStoredPasskey } from "@/lib/auth/passkey";
import { ProblemDetails } from "./types";

const rawBaseUrl =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") || "http://localhost:8000";

// Strip trailing /api/v1 if present, since API service endpoints include /api/v1
export const API_BASE_URL = rawBaseUrl.endsWith("/api/v1")
  ? rawBaseUrl.slice(0, -"/api/v1".length)
  : rawBaseUrl;

export async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {},
  isProtected: boolean = true
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint.startsWith("/") ? endpoint : `/${endpoint}`}`;
  const headers = new Headers(options.headers || {});

  if (isProtected) {
    const passkey = getStoredPasskey();
    if (passkey) {
      headers.set("X-Workspace-Key", passkey);
    }
  }

  // Set Content-Type: application/json only when body is not FormData
  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  let response: Response;
  try {
    response = await fetch(url, {
      ...options,
      headers,
    });
  } catch (err: unknown) {
    const networkError: ProblemDetails = {
      error_code: "NETWORK_ERROR",
      message: err instanceof Error ? err.message : "Failed to connect to ProofLens API service.",
      status_code: 0,
    };
    throw networkError;
  }

  if (!response.ok) {
    let errorPayload: ProblemDetails;
    try {
      const data = await response.json();
      errorPayload = {
        error_code: data.error_code || "HTTP_ERROR",
        message: data.message || `HTTP ${response.status} ${response.statusText}`,
        details: data.details,
        status_code: response.status,
      };
    } catch {
      errorPayload = {
        error_code: "HTTP_ERROR",
        message: `HTTP ${response.status} ${response.statusText}`,
        status_code: response.status,
      };
    }

    if (response.status === 401 && typeof window !== "undefined") {
      window.dispatchEvent(new CustomEvent("prooflens:unauthorized"));
    }

    throw errorPayload;
  }

  if (response.status === 204) {
    return null as T;
  }

  return response.json() as Promise<T>;
}

export async function apiFetchBlob(
  endpoint: string,
  options: RequestInit = {},
  isProtected: boolean = true
): Promise<Blob> {
  const url = `${API_BASE_URL}${endpoint.startsWith("/") ? endpoint : `/${endpoint}`}`;
  const headers = new Headers(options.headers || {});

  if (isProtected) {
    const passkey = getStoredPasskey();
    if (passkey) {
      headers.set("X-Workspace-Key", passkey);
    }
  }

  let response: Response;
  try {
    response = await fetch(url, {
      ...options,
      headers,
    });
  } catch (err: unknown) {
    const networkError: ProblemDetails = {
      error_code: "NETWORK_ERROR",
      message: err instanceof Error ? err.message : "Failed to connect to ProofLens API service.",
      status_code: 0,
    };
    throw networkError;
  }

  if (!response.ok) {
    let errorPayload: ProblemDetails;
    try {
      const data = await response.json();
      errorPayload = {
        error_code: data.error_code || "HTTP_ERROR",
        message: data.message || `HTTP ${response.status} ${response.statusText}`,
        details: data.details,
        status_code: response.status,
      };
    } catch {
      errorPayload = {
        error_code: "HTTP_ERROR",
        message: `HTTP ${response.status} ${response.statusText}`,
        status_code: response.status,
      };
    }

    if (response.status === 401 && typeof window !== "undefined") {
      window.dispatchEvent(new CustomEvent("prooflens:unauthorized"));
    }

    throw errorPayload;
  }

  return response.blob();
}

