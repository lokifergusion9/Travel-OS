/** Tiny typed fetch client with bearer-token + auto refresh.
 *
 * The access token lives in memory only; the refresh token is an httpOnly
 * cookie set by the API, so no long-lived credential is readable from JS.
 * On page load `refreshTokens()` restores the session from that cookie.
 */
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

let accessToken: string | null = null;

export const tokenStore = {
  get access() {
    return accessToken;
  },
  set({ access_token }: { access_token: string }) {
    accessToken = access_token;
  },
  clear() {
    accessToken = null;
  },
};

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

// Coalesce concurrent refreshes (several requests 401-ing at once).
let refreshing: Promise<boolean> | null = null;

export function refreshTokens(): Promise<boolean> {
  refreshing ??= (async () => {
    try {
      const resp = await fetch(`${BASE_URL}/api/v1/auth/refresh`, {
        method: "POST",
        credentials: "include",
      });
      if (!resp.ok) {
        tokenStore.clear();
        return false;
      }
      tokenStore.set(await resp.json());
      return true;
    } catch {
      return false;
    } finally {
      refreshing = null;
    }
  })();
  return refreshing;
}

export async function api<T = unknown>(
  path: string,
  options: RequestInit & { auth?: boolean; retry?: boolean } = {},
): Promise<T> {
  const { auth = true, retry = true, headers, ...rest } = options;
  const finalHeaders: Record<string, string> = {
    "Content-Type": "application/json",
    ...(headers as Record<string, string>),
  };
  if (auth && tokenStore.access) {
    finalHeaders.Authorization = `Bearer ${tokenStore.access}`;
  }

  // credentials: the auth endpoints set/clear the refresh cookie.
  const resp = await fetch(`${BASE_URL}${path}`, {
    credentials: "include",
    ...rest,
    headers: finalHeaders,
  });

  if (resp.status === 401 && auth && retry && (await refreshTokens())) {
    return api<T>(path, { ...options, retry: false });
  }

  if (!resp.ok) {
    let detail = resp.statusText;
    try {
      const body = await resp.json();
      detail = body.detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(resp.status, detail);
  }

  if (resp.status === 204) return undefined as T;
  return resp.json();
}
