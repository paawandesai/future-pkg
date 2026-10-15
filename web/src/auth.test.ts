import { afterEach, describe, expect, it, vi } from "vitest";

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

afterEach(() => {
  vi.restoreAllMocks();
  vi.resetModules();
});

describe("auth", () => {
  it("falls back to mock mode when no config.json is served", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(new Response("not found", { status: 404 }));
    const auth = await import("./auth");
    expect(await auth.loadConfig()).toEqual({ authMode: "mock" });
    expect(await auth.authHeaders()).toEqual({});
  });

  it("signs in through the new-password challenge and sends the ID token", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(json({ authMode: "cognito", region: "us-east-1", userPoolClientId: "client" }))
      .mockResolvedValueOnce(json({ ChallengeName: "NEW_PASSWORD_REQUIRED", Session: "s1" }))
      .mockResolvedValueOnce(json({ AuthenticationResult: { IdToken: "id-tok" } }));
    const auth = await import("./auth");
    const first = await auth.signIn("coach@example.com", "temporary-Pass1");
    expect(first).toEqual({ ok: false, newPasswordSession: "s1" });
    expect(await auth.authHeaders()).toEqual({});
    expect(await auth.setNewPassword("coach@example.com", "s1", "a-New-Password-9")).toEqual({ ok: true });
    expect(await auth.authHeaders()).toEqual({ Authorization: "Bearer id-tok" });
    const [url, init] = fetchMock.mock.calls[2];
    expect(url).toBe("https://cognito-idp.us-east-1.amazonaws.com/");
    expect((init?.headers as Record<string, string>)["X-Amz-Target"]).toContain("RespondToAuthChallenge");
  });

  it("drops the token and notifies the app when the API answers 401", async () => {
    const auth = await import("./auth");
    const expired = vi.fn();
    auth.setToken("t");
    auth.onSessionExpired(expired);
    auth.sessionExpired();
    expect(expired).toHaveBeenCalledOnce();
    expect(await auth.authHeaders()).toEqual({});
  });
});
