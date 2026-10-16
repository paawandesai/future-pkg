import type { Tab } from "../App";
import type { MemberView } from "../types";

function initials(name: string) {
  return name
    .split(/\s+/)
    .map((p) => p[0] ?? "")
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

export function MemberHeader({
  member,
  tab,
  onTab,
}: {
  member: MemberView;
  tab: Tab;
  onTab: (t: Tab) => void;
}) {
  const p = member.profile;
  const prefs = member.preferences;
  const facts = [
    p.age,
    p.tier,
    prefs.training_days_per_week ? `${prefs.training_days_per_week} days/week` : null,
    prefs.preferred_session_minutes ? `~${prefs.preferred_session_minutes} min` : null,
  ].filter(Boolean);
  return (
    <section>
      <div className="member-head">
        <div className="row" style={{ gap: 16 }}>
          <div className="avatar" aria-hidden="true">
            {initials(member.name)}
          </div>
          <div>
            <div className="row" style={{ alignItems: "baseline", gap: 12 }}>
              <h1 style={{ fontSize: 24, fontWeight: 600 }}>{member.name}</h1>
              <span className="tag fiction">Fictional member</span>
            </div>
            <div className="small muted">{facts.join(" · ")}</div>
          </div>
        </div>
        <div className="row small">
          <span className="pill date">As of {member.as_of}</span>
          {member.injuries
            .filter((i) => i.active)
            .map((i) => (
              <span key={i.id} className="pill restriction">
                Active restriction: {i.region} ({i.status})
              </span>
            ))}
        </div>
      </div>
      <nav aria-label="Member sections" className="tabs">
        <button
          type="button"
          aria-current={tab === "draft" ? "page" : undefined}
          onClick={() => onTab("draft")}
        >
          Workout draft
        </button>
        <button
          type="button"
          aria-current={tab === "copilot" ? "page" : undefined}
          onClick={() => onTab("copilot")}
        >
          Copilot, brief and churn
        </button>
      </nav>
    </section>
  );
}
