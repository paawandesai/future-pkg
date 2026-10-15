import { QueryClient, QueryClientProvider, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "./api";
import { CopilotPage } from "./components/CopilotPage";
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
  const members = useQuery({ queryKey: ["members"], queryFn: api.members });
  const memberId = members.data?.[0]?.id;
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
          <span>Signed in as demo coach</span>
          <button type="button" className="linkish" onClick={onSignOut}>
            Sign out
          </button>
        </div>
      </header>
      <div className="page">
        {members.isError && <p role="alert">Couldn't load members: {String(members.error.message)}</p>}
        {members.data && members.data.length === 0 && <p>No members are assigned to you.</p>}
        {member.isError && <p role="alert">Couldn't load the member: {String(member.error.message)}</p>}
        {member.data && (
          <>
            <MemberHeader member={member.data} tab={tab} onTab={setTab} />
            {tab === "draft" ? <GeneratorPage member={member.data} /> : <CopilotPage member={member.data} />}
          </>
        )}
        {(members.isPending || member.isPending) && !members.isError && <p className="muted">Loading…</p>}
      </div>
    </>
  );
}

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
});

export function App() {
  const [signedIn, setSignedIn] = useState(false);
  return (
    <QueryClientProvider client={queryClient}>
      <DemoBanner />
      {signedIn ? (
        <Workspace onSignOut={() => setSignedIn(false)} />
      ) : (
        <Login onSignedIn={() => setSignedIn(true)} />
      )}
    </QueryClientProvider>
  );
}
