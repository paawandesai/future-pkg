// Sign-in for the coach workspace.
// Local runs use the API's mock auth (no config.json is served, so mode is "mock" and no token is sent).
// The deployed site serves /config.json from the stack; mode "cognito" signs in against the
// invite-only user pool with USER_PASSWORD_AUTH and sends the ID token on every API call.
// The token is kept in memory only: a reload means signing in again.

export type AuthConfig =
  { authMode: "mock" } | { authMode: "cognito"; region: string; userPoolClientId: string };

let config: AuthConfig | null = null;
let token: string | null = null;
let expiredListener: (() => void) | null = null;

export async function loadConfig(): Promise<AuthConfig> {
  if (config) return config;
  try {
    const res = await fetch("/config.json", { cache: "no-store" });
    const body = res.ok ? ((await res.json()) as Partial<AuthConfig>) : null;
    config =
      body?.authMode === "cognito" && "userPoolClientId" in body && "region" in body
        ? (body as AuthConfig)
        : { authMode: "mock" };
  } catch {
    config = { authMode: "mock" };
  }
  return config;
}

export function setToken(t: string | null): void {
  token = t;
}

export async function authHeaders(): Promise<Record<string, string>> {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/** Called by the API client on a 401, so the app returns to the sign-in screen. */
export function sessionExpired(): void {
  if (!token) return;
  token = null;
  expiredListener?.();
}

export function onSessionExpired(listener: (() => void) | null): void {
  expiredListener = listener;
}

export type SignInResult =
  { ok: true } | { ok: false; newPasswordSession: string } | { ok: false; error: string };

type CognitoAuthResponse = {
  AuthenticationResult?: { IdToken?: string };
  ChallengeName?: string;
  Session?: string;
  message?: string;
  __type?: string;
};

async function cognito(cfg: Extract<AuthConfig, { authMode: "cognito" }>, target: string, body: object) {
  const res = await fetch(`https://cognito-idp.${cfg.region}.amazonaws.com/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-amz-json-1.1",
      "X-Amz-Target": `AWSCognitoIdentityProviderService.${target}`,
    },
    body: JSON.stringify({ ClientId: cfg.userPoolClientId, ...body }),
  });
  return { ok: res.ok, body: (await res.json()) as CognitoAuthResponse };
}

function finish(r: { ok: boolean; body: CognitoAuthResponse }): SignInResult {
  const id = r.body.AuthenticationResult?.IdToken;
  if (r.ok && id) {
    token = id;
    return { ok: true };
  }
  if (r.ok && r.body.ChallengeName === "NEW_PASSWORD_REQUIRED" && r.body.Session) {
    return { ok: false, newPasswordSession: r.body.Session };
  }
  // Cognito's own messages are generic for bad credentials; never echo the password or username.
  return { ok: false, error: r.body.message ?? "Sign-in failed" };
}

export async function signIn(email: string, password: string): Promise<SignInResult> {
  const cfg = await loadConfig();
  if (cfg.authMode !== "cognito") return { ok: true };
  return finish(
    await cognito(cfg, "InitiateAuth", {
      AuthFlow: "USER_PASSWORD_AUTH",
      AuthParameters: { USERNAME: email, PASSWORD: password },
    }),
  );
}

/** First sign-in with an invite's temporary password: Cognito asks for a new one. */
export async function setNewPassword(
  email: string,
  session: string,
  newPassword: string,
): Promise<SignInResult> {
  const cfg = await loadConfig();
  if (cfg.authMode !== "cognito") return { ok: true };
  return finish(
    await cognito(cfg, "RespondToAuthChallenge", {
      ChallengeName: "NEW_PASSWORD_REQUIRED",
      Session: session,
      ChallengeResponses: { USERNAME: email, NEW_PASSWORD: newPassword },
    }),
  );
}
