import { QueryClient, QueryClientProvider, useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api } from "./api";
import { onSessionExpired, setToken } from "./auth";
import { CopilotPage } from "./components/CopilotPage";
import { AdminPage } from "./components/AdminPage";
import { GeneratorPage } from "./components/GeneratorPage";
import { Login } from "./components/Login";
import { MemberHeader } from "./components/MemberHeader";

export type Tab = "draft" | "copilot";

export function DemoBanner() {
  return (
    <div role="banner" className="demo-banner">
      Demo — synthetic data only
    </div>
  );
}

function Workspace({ onSignOut }: { onSignOut: () => void }) {
  const [tab, setTab] = useState<Tab>("draft");
  const [picked, setPicked] = useState<string | null>(null);
  const [view, setView] = useState<"workspace" | "admin">("workspace");
  const me = useQuery({ queryKey: ["me"], queryFn: api.me });
  const members = useQuery({ queryKey: ["members"], queryFn: api.members });
  const memberId = picked ?? members.data?.[0]?.id;
  const member = useQuery({
    queryKey: ["member", memberId],
    queryFn: () => api.member(memberId as string),
    enabled: Boolean(memberId),
  });

  return (
    <>
      <header className="topbar">
        <div className="brand">
          <span className="brand-name">Coach workspace</span>
          <span className="tag">Coach decision support</span>
        </div>
        <div className="row small muted">
          {me.data?.admin && (
            <button
              type="button"
              className="btn small"
              aria-pressed={view === "admin"}
              onClick={() => setView(view === "admin" ? "workspace" : "admin")}
            >
              {view === "admin" ? "Back to members" : "Admin"}
            </button>
          )}
          {view === "workspace" && members.data && members.data.length > 1 && (
            <label className="row" style={{ gap: 6 }}>
              <span>Member</span>
              <select
                className="input"
                style={{ padding: "6px 8px" }}
                value={memberId ?? ""}
                onChange={(e) => setPicked(e.target.value)}
              >
                {members.data.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name}
                  </option>
                ))}
              </select>
            </label>
          )}
          <span>Signed in</span>
          <button type="button" className="linkish" onClick={onSignOut}>
            Sign out
          </button>
        </div>
      </header>
      <div className="page">
        {view === "admin" ? (
          <>
            <h1 style={{ fontSize: 24, fontWeight: 600 }}>Demo access</h1>
            <AdminPage />
          </>
        ) : (
          <>
            {members.isError && <p role="alert">Couldn't load members: {String(members.error.message)}</p>}
            {members.data && members.data.length === 0 && <p>No members are assigned to you.</p>}
            {member.isError && <p role="alert">Couldn't load the member: {String(member.error.message)}</p>}
            {member.data && (
              <>
                <MemberHeader member={member.data} tab={tab} onTab={setTab} />
                {tab === "draft" ? (
                  <GeneratorPage key={member.data.id} member={member.data} />
                ) : (
                  <CopilotPage key={member.data.id} member={member.data} />
                )}
              </>
            )}
            {(members.isPending || member.isPending) && !members.isError && <p className="muted">Loading…</p>}
          </>
        )}
      </div>
    </>
  );
}

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
});

export function App() {
  const [signedIn, setSignedIn] = useState(false);
  useEffect(() => {
    onSessionExpired(() => {
      queryClient.clear();
      setSignedIn(false);
    });
    return () => onSessionExpired(null);
  }, []);
  const signOut = () => {
    setToken(null);
    queryClient.clear();
    setSignedIn(false);
  };
  return (
    <QueryClientProvider client={queryClient}>
      <DemoBanner />
      {signedIn ? <Workspace onSignOut={signOut} /> : <Login onSignedIn={() => setSignedIn(true)} />}
    </QueryClientProvider>
  );
}
