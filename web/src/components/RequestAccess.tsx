import { type FormEvent, useState } from "react";
import { api } from "../api";

/** Public form: an admin reviews every request before any account exists. */
export function RequestAccess({ onBack }: { onBack: () => void }) {
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [reason, setReason] = useState("");
  const [state, setState] = useState<"idle" | "sending" | "sent">("idle");
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setState("sending");
    setError(null);
    try {
      await api.requestAccess({ email: email.trim(), name: name.trim(), reason: reason.trim() });
      setState("sent");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't send the request.");
      setState("idle");
    }
  };

  return (
    <main className="login">
      <form className="card" onSubmit={(e) => void submit(e)}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 600 }}>Request a demo account</h1>
          <p className="small muted" style={{ margin: "4px 0 0" }}>
            An admin reviews each request. If it's approved, you'll get an email with a temporary password.
          </p>
        </div>
        {state === "sent" ? (
          <p role="status" className="notice ok" style={{ margin: 0 }}>
            Request received. Check your email once an admin has reviewed it.
          </p>
        ) : (
          <>
            <div className="field">
              <label htmlFor="req-email">Work email</label>
              <input
                id="req-email"
                className="input"
                type="email"
                required
                maxLength={254}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <div className="field">
              <label htmlFor="req-name">Name (optional)</label>
              <input
                id="req-name"
                className="input"
                maxLength={80}
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>
            <div className="field">
              <label htmlFor="req-reason">Why you'd like access</label>
              <textarea
                id="req-reason"
                className="input"
                rows={3}
                required
                minLength={3}
                maxLength={500}
                value={reason}
                onChange={(e) => setReason(e.target.value)}
              />
            </div>
            {error && (
              <p role="alert" className="notice alert" style={{ margin: 0 }}>
                {error}
              </p>
            )}
            <button type="submit" className="btn primary" disabled={state === "sending"}>
              Send request
            </button>
          </>
        )}
        <button type="button" className="linkish" onClick={onBack}>
          Back to sign in
        </button>
        <p className="small muted" style={{ margin: 0 }}>
          The demo holds fictional members only. Don't enter real personal or health information.
        </p>
      </form>
    </main>
  );
}
