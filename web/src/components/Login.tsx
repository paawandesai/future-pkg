import { type FormEvent } from "react";

/** Local runs use mocked auth; the deployed build replaces this with the Cognito sign-in. */
export function Login({ onSignedIn }: { onSignedIn: () => void }) {
  const submit = (e: FormEvent) => {
    e.preventDefault();
    onSignedIn();
  };
  return (
    <main className="login">
      <form className="card" onSubmit={submit}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 600 }}>Coach workspace</h1>
          <p className="small muted" style={{ margin: "4px 0 0" }}>
            Coach decision support. Demo accounts are invite-only.
          </p>
        </div>
        <p className="notice warn" style={{ margin: 0 }}>
          Local demo: sign-in is mocked and you continue as the demo coach.
        </p>
        <button type="submit" className="btn primary">
          Continue as demo coach
        </button>
        <p className="small muted" style={{ margin: 0 }}>
          Every member in this demo is fictional. Do not enter real personal or health information.
        </p>
      </form>
    </main>
  );
}
