import { type FormEvent, useEffect, useState } from "react";
import { type AuthConfig, loadConfig, setNewPassword, signIn } from "../auth";

/** Mock sign-in locally; invite-only Cognito accounts on the deployed demo. */
export function Login({ onSignedIn }: { onSignedIn: () => void }) {
  const [cfg, setCfg] = useState<AuthConfig | null>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [newPassword, setNewPasswordValue] = useState("");
  const [challenge, setChallenge] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    void loadConfig().then(setCfg);
  }, []);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (cfg?.authMode !== "cognito") {
      onSignedIn();
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const r = challenge
        ? await setNewPassword(email, challenge, newPassword)
        : await signIn(email, password);
      if (r.ok) {
        setPassword("");
        setNewPasswordValue("");
        onSignedIn();
      } else if ("newPasswordSession" in r) {
        setChallenge(r.newPasswordSession);
      } else {
        setError(r.error);
      }
    } catch {
      setError("Couldn't reach the sign-in service. Try again.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="login">
      <form className="card" onSubmit={(e) => void submit(e)}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 600 }}>Coach workspace</h1>
          <p className="small muted" style={{ margin: "4px 0 0" }}>
            Coach decision support. Demo accounts are invite-only.
          </p>
        </div>
        {cfg === null && <p className="muted small">Loading…</p>}
        {cfg?.authMode === "mock" && (
          <p className="notice warn" style={{ margin: 0 }}>
            Local demo: sign-in is mocked and you continue as the demo coach.
          </p>
        )}
        {cfg?.authMode === "cognito" && !challenge && (
          <>
            <div className="field">
              <label htmlFor="email">Email</label>
              <input
                id="email"
                className="input"
                type="email"
                autoComplete="username"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <div className="field">
              <label htmlFor="password">Password</label>
              <input
                id="password"
                className="input"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
          </>
        )}
        {cfg?.authMode === "cognito" && challenge && (
          <div className="field">
            <label htmlFor="new-password">Choose a new password</label>
            <input
              id="new-password"
              className="input"
              type="password"
              autoComplete="new-password"
              minLength={12}
              required
              value={newPassword}
              onChange={(e) => setNewPasswordValue(e.target.value)}
            />
            <span className="small muted">
              At least 12 characters, with upper and lower case letters and a number.
            </span>
          </div>
        )}
        {error && (
          <p role="alert" className="notice alert" style={{ margin: 0 }}>
            {error}
          </p>
        )}
        {cfg && (
          <button type="submit" className="btn primary" disabled={busy}>
            {cfg.authMode === "mock"
              ? "Continue as demo coach"
              : challenge
                ? "Set password and sign in"
                : "Sign in"}
          </button>
        )}
        <p className="small muted" style={{ margin: 0 }}>
          Every member in this demo is fictional. Do not enter real personal or health information.
        </p>
      </form>
    </main>
  );
}
