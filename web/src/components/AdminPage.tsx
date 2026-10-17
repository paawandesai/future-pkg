import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { api } from "../api";

const when = (iso: string | null) => (iso ? iso.replace("T", " ").slice(0, 16) : "");

/** Demo access for admins: approve requests, invite reviewers, turn accounts off after grading. */
export function AdminPage() {
  const qc = useQueryClient();
  const requests = useQuery({ queryKey: ["admin", "requests"], queryFn: api.admin.requests });
  const users = useQuery({ queryKey: ["admin", "users"], queryFn: api.admin.users });
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const refresh = () => void qc.invalidateQueries({ queryKey: ["admin"] });
  const act = useMutation({
    mutationFn: (fn: () => Promise<unknown>) => fn(),
    onSuccess: refresh,
    onError: (e: Error) => setMessage(e.message),
  });

  const invite = (e: FormEvent) => {
    e.preventDefault();
    setMessage(null);
    act.mutate(() => api.admin.invite(email.trim()).then(() => setMessage(`Invited ${email.trim()}.`)));
    setEmail("");
  };
  const disableAll = () => {
    if (!window.confirm("Turn off every reviewer account? Admin accounts stay on.")) return;
    act.mutate(() => api.admin.disableAll().then((r) => setMessage(`Turned off ${r.disabled} accounts.`)));
  };

  const rejectAll = () => {
    if (!window.confirm("Reject every pending request? Nobody is invited.")) return;
    act.mutate(() => api.admin.rejectPending().then((r) => setMessage(`Rejected ${r.rejected} requests.`)));
  };

  const pending = (requests.data ?? []).filter((r) => r.status === "pending");
  const decided = (requests.data ?? []).filter((r) => r.status !== "pending");

  return (
    <div className="layout">
      <div className="wide">
        <section className="card" aria-labelledby="req-h">
          <h2 id="req-h">Access requests</h2>
          <p className="small muted" style={{ marginTop: 0 }}>
            Approving sends a Cognito invite with a temporary password to the requester. Requests are deleted
            after 7 days.
          </p>
          {requests.isError && <p role="alert">Couldn't load requests: {requests.error.message}</p>}
          {requests.data && pending.length === 0 && <p className="muted">No pending requests.</p>}
          {pending.length > 1 && (
            <button type="button" className="btn small" disabled={act.isPending} onClick={rejectAll}>
              Reject all pending ({pending.length})
            </button>
          )}
          <ul className="list">
            {pending.map((r) => (
              <li key={r.id}>
                <div className="row" style={{ justifyContent: "space-between" }}>
                  <div>
                    <strong>{r.email}</strong> {r.name && <span className="muted">· {r.name}</span>}
                    <div className="small">{r.reason}</div>
                    <div className="xsmall muted">{when(r.created_at)}</div>
                  </div>
                  <div className="row">
                    <button
                      type="button"
                      className="btn small primary"
                      disabled={act.isPending}
                      onClick={() => act.mutate(() => api.admin.approve(r.id))}
                    >
                      Approve and invite
                    </button>
                    <button
                      type="button"
                      className="btn small"
                      disabled={act.isPending}
                      onClick={() => act.mutate(() => api.admin.reject(r.id))}
                    >
                      Reject
                    </button>
                  </div>
                </div>
              </li>
            ))}
          </ul>
          {decided.length > 0 && (
            <details style={{ marginTop: 12 }}>
              <summary className="small">Decided ({decided.length})</summary>
              <ul className="list small">
                {decided.map((r) => (
                  <li key={r.id}>
                    {r.email}: {r.status} by {r.decided_by} on {when(r.decided_at)}
                  </li>
                ))}
              </ul>
            </details>
          )}
        </section>

        <section className="card" aria-labelledby="users-h">
          <h2 id="users-h">Accounts</h2>
          {users.isError && <p role="alert">Couldn't load accounts: {users.error.message}</p>}
          <div className="table-wrap">
            <table className="plan">
              <thead>
                <tr>
                  <th>Email</th>
                  <th>Status</th>
                  <th>Created</th>
                  <th>Access</th>
                </tr>
              </thead>
              <tbody>
                {(users.data ?? []).map((u) => (
                  <tr key={u.email}>
                    <td>
                      {u.email} {u.admin && <span className="chip">Admin</span>}
                    </td>
                    <td className="small">{u.status}</td>
                    <td className="num small">{when(u.created_at)}</td>
                    <td>
                      {u.admin ? (
                        <span className="small muted">Always on</span>
                      ) : (
                        <button
                          type="button"
                          className="btn small"
                          disabled={act.isPending}
                          onClick={() => act.mutate(() => api.admin.setEnabled(u.email, !u.enabled))}
                        >
                          {u.enabled ? "Turn off" : "Turn on"}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>

      <aside className="side">
        <form className="card" onSubmit={invite}>
          <h2>Invite a reviewer</h2>
          <div className="field" style={{ marginTop: 8 }}>
            <label htmlFor="invite-email">Email</label>
            <input
              id="invite-email"
              className="input"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <button type="submit" className="btn primary" style={{ marginTop: 12 }} disabled={act.isPending}>
            Send invite
          </button>
          <p className="small muted" style={{ marginBottom: 0 }}>
            Reviewers sign in as the demo coach and see the same fictional members.
          </p>
        </form>
        <section className="card">
          <h2>After grading</h2>
          <p className="small muted" style={{ marginTop: 0 }}>
            Turns off every reviewer account. Admin accounts stay on.
          </p>
          <button type="button" className="btn" disabled={act.isPending} onClick={disableAll}>
            Turn off all reviewer accounts
          </button>
        </section>
        {message && (
          <p role="status" className="notice ok">
            {message}
          </p>
        )}
      </aside>
    </div>
  );
}
