import { afterEach, describe, expect, it, vi } from "vitest";
import { api, ApiError, refreshTokens, tokenStore } from "../api";

function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
  tokenStore.clear();
});

describe("api client", () => {
  it("sends the bearer token and cookies", async () => {
    const fetchMock = vi.fn().mockResolvedValue(json(200, { ok: true }));
    vi.stubGlobal("fetch", fetchMock);
    tokenStore.set({ access_token: "abc" });

    await expect(api("/x")).resolves.toEqual({ ok: true });
    const [, init] = fetchMock.mock.calls[0];
    expect(init.headers.Authorization).toBe("Bearer abc");
    expect(init.credentials).toBe("include");
  });

  it("refreshes once on 401 and retries", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(json(401, { detail: "expired" }))
      .mockResolvedValueOnce(json(200, { access_token: "new", refresh_token: "r" }))
      .mockResolvedValueOnce(json(200, { ok: 1 }));
    vi.stubGlobal("fetch", fetchMock);
    tokenStore.set({ access_token: "old" });

    await expect(api("/x")).resolves.toEqual({ ok: 1 });
    expect(tokenStore.access).toBe("new");
    expect(fetchMock.mock.calls[2][1].headers.Authorization).toBe("Bearer new");
  });

  it("surfaces the API's detail message", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(json(409, { detail: "taken" })));
    const err = (await api("/x", { auth: false }).catch((e: unknown) => e)) as ApiError;
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(409);
    expect(err.message).toBe("taken");
  });

  it("coalesces concurrent refreshes into one request", async () => {
    const fetchMock = vi.fn().mockResolvedValue(json(200, { access_token: "t" }));
    vi.stubGlobal("fetch", fetchMock);
    const results = await Promise.all([refreshTokens(), refreshTokens(), refreshTokens()]);
    expect(results).toEqual([true, true, true]);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("clears the token when refresh fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(json(401, {})));
    tokenStore.set({ access_token: "stale" });
    await expect(refreshTokens()).resolves.toBe(false);
    expect(tokenStore.access).toBeNull();
  });
});
