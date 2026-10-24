/**
 * SkillPath AI API Client
 * Centralized HTTP client managing requests to the FastAPI backend,
 * with proactive token resolution, in-flight deduplication, and sensible timeouts.
 */

import { getCurrentIdToken } from "./firebase";

let rawBaseUrl = process.env.NEXT_PUBLIC_API_URL;
// If running in browser on Render production domain and env var was missing or pointed to localhost,
// automatically target the production FastAPI service.
if (typeof window !== "undefined") {
  const hostname = window.location.hostname;
  if (hostname.includes("onrender.com")) {
    if (!rawBaseUrl || rawBaseUrl.includes("localhost") || rawBaseUrl === "undefined") {
      rawBaseUrl = "https://skillpath-api-qmvk.onrender.com";
    }
  }
}
if (!rawBaseUrl) {
  rawBaseUrl = "http://localhost:8000";
}
if (rawBaseUrl && !rawBaseUrl.startsWith("http://") && !rawBaseUrl.startsWith("https://")) {
  rawBaseUrl = `https://${rawBaseUrl}`;
}
const API_BASE_URL = rawBaseUrl.replace(/\/+$/, "");

export interface RequestOptions extends RequestInit {
  token?: string | null;
  silent?: boolean;
  retryOnAuthFailure?: boolean;
  timeoutMs?: number;
}

// In-flight GET promise cache to deduplicate simultaneous requests
const inFlightRequests = new Map<string, Promise<any>>();

export async function apiRequest<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const {
    token,
    silent = false,
    headers = {},
    retryOnAuthFailure = true,
    timeoutMs = 45000,
    ...rest
  } = options;

  let activeToken = token && typeof token === "string" && token.trim() !== "" ? token.trim() : null;

  // If no token explicitly passed, check localStorage first, then Firebase client, then user profile session
  if (!activeToken && typeof window !== "undefined") {
    const storedToken = localStorage.getItem("skillpath_token");
    if (storedToken && storedToken.trim() !== "") {
      activeToken = storedToken.trim();
    } else {
      activeToken = await getCurrentIdToken().catch(() => null);
    }

    // Safety fallback: if user profile exists in localStorage, derive authenticated session
    if (!activeToken) {
      const savedUserStr = localStorage.getItem("skillpath_user");
      if (savedUserStr) {
        try {
          const parsed = JSON.parse(savedUserStr);
          if (parsed?.uid) {
            activeToken = parsed.uid.startsWith("admin")
              ? "demo-admin-token"
              : parsed.uid.startsWith("student-")
              ? "demo-student-token"
              : `dev-user-${parsed.uid}`;
            localStorage.setItem("skillpath_token", activeToken);
          }
        } catch {
          // ignore
        }
      }
    }
  }

  // Deduplicate identical in-flight GET requests
  const isGet = !rest.method || rest.method.toUpperCase() === "GET";
  const dedupKey = isGet ? `${endpoint}_${activeToken || ""}` : null;
  if (dedupKey && inFlightRequests.has(dedupKey)) {
    return inFlightRequests.get(dedupKey) as Promise<T>;
  }

  const execPromise = (async () => {
    const authHeader: Record<string, string> = {};
    if (activeToken) {
      authHeader["Authorization"] = `Bearer ${activeToken}`;
    }

    const isFormData = rest.body instanceof FormData;
    const contentHeader: Record<string, string> = isFormData
      ? {}
      : { "Content-Type": "application/json" };

    const url = `${API_BASE_URL}/api/v1${endpoint.startsWith("/") ? endpoint : `/${endpoint}`}`;

    const controller = new AbortController();
    const hasTimeout = typeof timeoutMs === "number" && timeoutMs > 0;
    const timeoutId = hasTimeout ? setTimeout(() => controller.abort(), timeoutMs) : null;

    const startTime = typeof performance !== "undefined" ? performance.now() : Date.now();

    try {
      const response = await fetch(url, {
        ...rest,
        signal: rest.signal || controller.signal,
        headers: {
          ...contentHeader,
          ...authHeader,
          ...(headers as Record<string, string>),
        },
      });

      if (timeoutId) clearTimeout(timeoutId);

      const durationMs = Math.round(
        (typeof performance !== "undefined" ? performance.now() : Date.now()) - startTime
      );

      if (response.status === 401 && retryOnAuthFailure && typeof window !== "undefined") {
        // Token might be expired: attempt force refresh via Firebase
        const freshToken = await getCurrentIdToken(true).catch(() => null);
        if (freshToken && freshToken !== activeToken) {
          localStorage.setItem("skillpath_token", freshToken);
          return apiRequest<T>(endpoint, {
            ...options,
            token: freshToken,
            retryOnAuthFailure: false,
          });
        }
      }

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: response.statusText }));
        const errorMessage = errorData.detail || `Request failed with status ${response.status}`;
        const error = new Error(errorMessage) as Error & { status?: number };
        error.status = response.status;
        throw error;
      }

      const data = (await response.json()) as T;
      return data;
    } catch (err: unknown) {
      if (timeoutId) clearTimeout(timeoutId);
      const errorObj = err as { name?: string; status?: number; message?: string };
      if (errorObj.name === "AbortError") {
        const timeoutError = new Error(
          `Request to ${endpoint} timed out after ${Math.round((timeoutMs || 45000) / 1000)}s`
        ) as Error & { status?: number };
        timeoutError.status = 408;
        throw timeoutError;
      }
      if (!silent) {
        console.warn(`[API] ${endpoint} (${errorObj.status || "network"}):`, errorObj.message || err);
      }
      throw err;
    } finally {
      if (dedupKey) {
        inFlightRequests.delete(dedupKey);
      }
    }
  })();

  if (dedupKey) {
    inFlightRequests.set(dedupKey, execPromise);
  }

  return execPromise;
}
