import { useRef, useState, type FormEvent } from "react";
import { api, generate } from "../api";
import type {
  Alternative,
  Blocker,
  ExcludedGroup,
  GraphEdge,
  MemberView,
  Plan,
  PlanBlock,
  PlanItem,
  ReadRow,
} from "../types";

type State =
  | { kind: "idle" }
  | { kind: "running"; stage: string }
  | { kind: "blocked"; blockers: Blocker[] }
  | { kind: "plan"; plan: Plan }
  | { kind: "error"; message: string };

const STAGE_TEXT: Record<string, string> = {
  start: "Reading the request…",
  intent: "Checking the knowledge graph for restrictions…",
  safety: "Ordering the filtered exercises…",
  selection: "Fitting the time budget…",
};
const BLOCK_TITLE: Record<PlanBlock["name"], string> = {
  warmup: "Warm-up",
  main: "Main",
  cooldown: "Cool-down",
};

export function dose(i: PlanItem): string {
  const per = i.reps != null ? `${i.reps}` : `${i.work_s} s`;
  return `${i.sets} × ${per}${i.each_side ? " / side" : ""}`;
}

export function GeneratorPage({ member }: { member: MemberView }) {
  const [prompt, setPrompt] = useState("");
  const [minutes, setMinutes] = useState<string>(String(member.preferences.preferred_session_minutes ?? 45));
  const [cleared, setCleared] = useState<Record<string, string>>({});
  const [state, setState] = useState<State>({ kind: "idle" });
  const abort = useRef<AbortController | null>(null);
  const activeInjuries = member.injuries.filter((i) => i.active && i.clearable);

  async function run(confirmedRegions: { region: string; side: string | null }[] = []) {
    abort.current?.abort();
    const ctl = new AbortController();
    abort.current = ctl;
    setState({ kind: "running", stage: "start" });
    try {
      for await (const ev of generate(
        {
          member_id: member.id,
          prompt,
          minutes: Number(minutes),
          cleared_low_impact: Object.keys(cleared),
          confirmed_regions: confirmedRegions,
        },
        ctl.signal,
      )) {
        if (ev.event === "stage") setState({ kind: "running", stage: ev.stage });
        else if (ev.event === "blocked") setState({ kind: "blocked", blockers: ev.blockers });
        else if (ev.event === "plan") setState({ kind: "plan", plan: ev.plan });
        else if (ev.event === "error") setState({ kind: "error", message: ev.message });
      }
    } catch (e) {
      if (!ctl.signal.aborted)
        setState({ kind: "error", message: e instanceof Error ? e.message : String(e) });
    }
  }

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (prompt.trim() && minutes) void run();
  };

  return (
    <div className="layout">
      <form className="card side" onSubmit={submit} aria-labelledby="draft-h">
        <h2 id="draft-h">Draft a workout</h2>
        <div className="field">
          <label htmlFor="prompt">What should the session focus on?</label>
          <textarea
            id="prompt"
            className="input"
            rows={4}
            maxLength={1000}
            value={prompt}
            placeholder="Upper body today, left knee still a bit sore. No deadlifts."
            onChange={(e) => setPrompt(e.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="minutes">Time available (minutes)</label>
          <input
            id="minutes"
            className="input"
            style={{ width: 180 }}
            type="number"
            min={10}
            max={120}
            required
            value={minutes}
            aria-describedby="minutes-hint"
            onChange={(e) => setMinutes(e.target.value)}
          />
          <div id="minutes-hint" className="xsmall muted">
            Starts at the member&apos;s preferred session length. The plan fits inside it.
          </div>
        </div>
        {activeInjuries.length > 0 && (
          <fieldset>
            <legend>Coach-entered clearance</legend>
            {activeInjuries.map((i) => (
              <label key={i.id} className="check">
                <input
                  type="checkbox"
                  checked={i.id in cleared}
                  onChange={(e) =>
                    setCleared((c) => {
                      const next = { ...c };
                      if (e.target.checked)
                        next[i.id] = new Date().toISOString().slice(0, 16).replace("T", " ");
                      else delete next[i.id];
                      return next;
                    })
                  }
                />
                <span>
                  {capitalize(i.region)} cleared for low-impact loading
                  <br />
                  <span className="small muted">
                    {i.id in cleared
                      ? `Entered by demo coach · ${cleared[i.id]}`
                      : "Low-impact exercises that load this region move from excluded to down-ranked and flagged. High-impact work and deep loaded knee bends stay excluded. Chat messages never change this."}
                  </span>
                </span>
              </label>
            ))}
          </fieldset>
        )}
        <button type="submit" className="btn primary" disabled={!prompt.trim() || state.kind === "running"}>
          {state.kind === "running" ? "Drafting…" : "Draft plan"}
        </button>
        <p className="small muted" style={{ margin: 0 }}>
          Drafts are coach decision support. Nothing reaches the member until you confirm it.
        </p>
      </form>

      <div className="wide">
        {member.review_mentions.map((m, idx) => (
          <ReviewMention key={idx} quote={m.quote} ts={m.ts} />
        ))}
        {state.kind === "idle" && (
          <div className="card muted">Describe the session and press Draft plan. The plan appears here.</div>
        )}
        {state.kind === "running" && (
          <div className="card" role="status" aria-live="polite">
            {STAGE_TEXT[state.stage] ?? "Working…"}
          </div>
        )}
        {state.kind === "error" && (
          <div className="card notice alert" role="alert">
            {state.message}
          </div>
        )}
        {state.kind === "blocked" && (
          <BlockerCard
            blockers={state.blockers}
            onContinue={(r) => void run(r)}
            onEdit={() => setState({ kind: "idle" })}
          />
        )}
        {state.kind === "plan" && (
          <>
            <PlanCard key={state.plan.id} plan={state.plan} onDiscard={() => setState({ kind: "idle" })} />
            <div className="cards">
              <FilteredCard groups={state.plan.trace.excluded} />
              {state.plan.trace.alternatives.length > 0 && (
                <AlternativesCard alts={state.plan.trace.alternatives} planned={plannedIds(state.plan)} />
              )}
              <TraceCard plan={state.plan} />
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function capitalize(s: string) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

function ReviewMention({ quote, ts }: { quote: string; ts: string | null }) {
  return (
    <div className="card">
      <div style={{ fontWeight: 600 }}>Member mentioned something to review</div>
      <blockquote className="quote" style={{ marginTop: 8 }}>
        <div className="xsmall muted">Member said{ts ? ` · ${ts.slice(0, 10)}` : ""}</div>“{quote}”
      </blockquote>
      <p className="small muted" style={{ marginBottom: 0 }}>
        Member messages can't lift a restriction. If a clinician has cleared the member, record it in the
        clearance setting.
      </p>
    </div>
  );
}

function BlockerCard({
  blockers,
  onContinue,
  onEdit,
}: {
  blockers: Blocker[];
  onContinue: (regions: { region: string; side: string | null }[]) => void;
  onEdit: () => void;
}) {
  const [choice, setChoice] = useState<Record<number, string>>({});
  const all = (b: Blocker) => b.candidates.map((c) => c.concept);
  const answer = () =>
    blockers.flatMap((b, i) => {
      const pick = choice[i] ?? "all";
      const regions = pick === "all" ? all(b) : [pick];
      return regions.filter((r) => r.startsWith("region:")).map((region) => ({ region, side: null }));
    });
  const canContinue = blockers.every((b) => b.candidates.some((c) => c.concept.startsWith("region:")));
  return (
    <section className="card" role="alert" aria-labelledby="blk-h">
      <h2 id="blk-h">Drafting paused: confirm the body region</h2>
      {blockers.map((b, i) => (
        <div key={i} style={{ marginTop: 12 }}>
          <p style={{ margin: "0 0 8px" }}>
            Your request mentions “{b.mention}”. {b.reason} No plan was drafted.
          </p>
          {b.candidates.length > 0 && (
            <div className="field">
              <span className="label">Closest matches</span>
              {b.candidates.map((c) => (
                <label key={c.concept} className="check">
                  <input
                    type="radio"
                    name={`blk-${i}`}
                    checked={choice[i] === c.concept}
                    onChange={() => setChoice((s) => ({ ...s, [i]: c.concept }))}
                  />
                  <span>
                    {c.label} {c.score != null && <span className="chip">fuzzy {c.score.toFixed(2)}</span>}
                  </span>
                </label>
              ))}
              {b.candidates.length > 1 && (
                <label className="check">
                  <input
                    type="radio"
                    name={`blk-${i}`}
                    checked={(choice[i] ?? "all") === "all"}
                    onChange={() => setChoice((s) => ({ ...s, [i]: "all" }))}
                  />
                  <span>All candidates (restrict every region listed)</span>
                </label>
              )}
            </div>
          )}
        </div>
      ))}
      <div className="row" style={{ marginTop: 16 }}>
        <button
          type="button"
          className="btn primary"
          disabled={!canContinue}
          onClick={() => onContinue(answer())}
        >
          Continue with this restriction
        </button>
        <button type="button" className="btn" onClick={onEdit}>
          Edit request
        </button>
      </div>
    </section>
  );
}

function PlanCard({ plan, onDiscard }: { plan: Plan; onDiscard: () => void }) {
  const [status, setStatus] = useState<{ status: string; at?: string; error?: string }>({
    status: plan.status,
  });
  const [showUnverified, setShowUnverified] = useState(false);
  const secs = ((plan.timings_ms.total ?? 0) / 1000).toFixed(1);
  const confirm = async () => {
    try {
      const r = await api.confirm(plan.id);
      setStatus({ status: r.status, at: r.confirmed_at });
    } catch (e) {
      setStatus({ status: "draft", error: e instanceof Error ? e.message : String(e) });
    }
  };
  const notes = plan.trace.notes;
  return (
    <section className="card" aria-labelledby="plan-h">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <div className="row">
          <h2 id="plan-h">
            {plan.title.split(" · ")[0]}, {Math.round(plan.minutes_planned)} of {plan.minutes_requested} min
          </h2>
          <span className={`tag ${status.status === "confirmed" ? "ok" : ""}`}>
            {status.status === "confirmed" ? "Confirmed" : "Draft"}
          </span>
        </div>
        <span className="small muted">Drafted with AI from the knowledge graph · {secs} s</span>
      </div>
      {plan.trace.unverified.length > 0 && (
        <div className="notice warn" role="status">
          <span>
            <strong>Unverified:</strong> {plan.trace.unverified.length} item
            {plan.trace.unverified.length === 1 ? "" : "s"} rest on rules without a checked source or a
            reviewer sign-off.{" "}
            <button type="button" className="linkish" onClick={() => setShowUnverified((v) => !v)}>
              {showUnverified ? "Hide" : "Show"}
            </button>
            {showUnverified && (
              <ul>
                {plan.trace.unverified.map((u) => (
                  <li key={u}>{u}</li>
                ))}
              </ul>
            )}
          </span>
        </div>
      )}
      {notes.length > 0 && (
        <div className="notice alert">
          <ul style={{ margin: 0 }}>
            {notes.map((n) => (
              <li key={n}>{n}</li>
            ))}
          </ul>
        </div>
      )}
      <div style={{ marginTop: 18, display: "flex", flexDirection: "column", gap: 18 }}>
        {plan.blocks.map((b) => (
          <div key={b.name}>
            <h3 className="block-title">
              {BLOCK_TITLE[b.name]} · {Math.round(b.minutes)} min
            </h3>
            {b.items.length === 0 ? (
              <p className="small muted" style={{ margin: 0 }}>
                No exercise that passed the filter fits this block.
              </p>
            ) : (
              <div className="table-wrap">
                <table className="plan">
                  <thead>
                    <tr>
                      <th>Exercise</th>
                      <th>Sets × reps</th>
                      <th>Rest</th>
                      <th>Time</th>
                    </tr>
                  </thead>
                  <tbody>
                    {b.items.map((i) => (
                      <tr key={i.exercise_id}>
                        <td>
                          {i.name}
                          {i.side_note && <div className="xsmall muted">{i.side_note}</div>}
                          <ItemReasons item={i} />
                          {i.flags.length > 0 && (
                            <div className="chips">
                              {i.flags.map((f) => (
                                <span key={f} className="chip flag">
                                  {f}
                                </span>
                              ))}
                            </div>
                          )}
                        </td>
                        <td className="num">{dose(i)}</td>
                        <td className="num">{i.rest_s ? `${i.rest_s} s` : "—"}</td>
                        <td className="num">{i.minutes.toFixed(1)} min</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        ))}
      </div>
      <div className="plan-foot">
        {status.status === "confirmed" ? (
          <div className="notice ok" role="status" style={{ margin: 0 }}>
            <strong>Confirmed by demo coach</strong>
            {status.at ? ` · ${status.at.replace("T", " ").slice(0, 16)}` : ""}
          </div>
        ) : (
          <span className="small muted" style={{ maxWidth: 520 }}>
            {plan.label} Confirming records your review. Only confirmed plans are shared with the member.
          </span>
        )}
        {status.error && (
          <span role="alert" className="small">
            {status.error}
          </span>
        )}
        {status.status !== "confirmed" && (
          <div className="row">
            <button type="button" className="btn" onClick={onDiscard}>
              Discard draft
            </button>
            <button type="button" className="btn primary" onClick={() => void confirm()}>
              Confirm plan
            </button>
          </div>
        )}
      </div>
    </section>
  );
}

function node(id: string): string {
  return id.replace(/^ex:.*/, "this exercise").replace(/^[a-z]+:/, "");
}

const PATH_GROUPS: [string, string[]][] = [
  ["Focus", ["focus"]],
  ["Equipment", ["equipment", "member-owns"]],
  ["Regions", ["region-clear", "region-cleared"]],
  ["Block", ["block"]],
];

function edgeText(e: GraphEdge): string {
  const src = e.src.startsWith("member:") ? "member" : node(e.src);
  const note =
    e.role === "region-clear" ? " (not restricted)" : e.role === "region-cleared" ? " (coach-cleared)" : "";
  return `${src} ${e.kind} ${node(e.dst)}${note}`;
}

function pathGroups(path: GraphEdge[]): [string, string][] {
  const out: [string, string][] = [];
  const seen = new Set<GraphEdge>();
  for (const [label, roles] of PATH_GROUPS) {
    const edges = path.filter((e) => e.role && roles.includes(e.role));
    edges.forEach((e) => seen.add(e));
    if (edges.length) out.push([label, edges.map(edgeText).join(" · ")]);
  }
  const rest = path.filter((e) => !seen.has(e));
  if (rest.length) out.push(["Graph", rest.map(edgeText).join(" · ")]);
  return out;
}

function ItemReasons({ item }: { item: PlanItem }) {
  if (!item.why.length && !item.counted_against.length && !item.path.length) return null;
  return (
    <details className="reasons">
      <summary className="xsmall">Why</summary>
      {item.why.length > 0 && (
        <div className="xsmall">
          <span className="muted">Chosen because: </span>
          {item.why.join("; ")}.
        </div>
      )}
      {item.counted_against.length > 0 && (
        <div className="xsmall">
          <span className="muted">Counted against: </span>
          {item.counted_against.join("; ")}.
        </div>
      )}
      {item.path.length > 0 && (
        <div className="xsmall muted" aria-label="Graph path">
          {pathGroups(item.path).map(([label, text]) => (
            <div key={label}>
              {label}: {text}
            </div>
          ))}
        </div>
      )}
    </details>
  );
}

function plannedIds(plan: Plan): Set<string> {
  return new Set(plan.blocks.flatMap((b) => b.items.map((i) => i.exercise_id)));
}

function AlternativesCard({ alts, planned }: { alts: Alternative[]; planned: Set<string> }) {
  return (
    <section className="card" aria-labelledby="alts-h">
      <h2 id="alts-h">Equivalent alternatives</h2>
      <p className="small muted" style={{ margin: "0 0 12px" }}>
        For exercises left out only for missing equipment: exercises that passed the filter and share a
        movement pattern and a target muscle in the graph.
      </p>
      <ul className="list">
        {alts.map((a) => (
          <li key={`${a.instead_of_id}|${a.use_id}`}>
            <div style={{ fontWeight: 500 }}>
              {a.use} instead of {a.instead_of}
            </div>
            <div className="small" style={{ color: "var(--ink-2)" }}>
              {a.instead_of} needs {a.needs.join(", ")}. Both train {a.shared_patterns.join(", ")} and target{" "}
              {a.shared_muscles.join(", ")}.
            </div>
            <div className="chips">
              {planned.has(a.use_id) && <span className="chip ok">in this plan</span>}
              {a.substitute && (
                <span className="chip">
                  {a.substitute.use} substitutes for {a.substitute.for} (signed)
                </span>
              )}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}

function FilteredCard({ groups }: { groups: ExcludedGroup[] }) {
  const [all, setAll] = useState(false);
  const names = new Set(groups.flatMap((g) => g.exercises));
  const shown = all ? groups : groups.slice(0, 4);
  return (
    <section className="card" aria-labelledby="filtered-h">
      <h2 id="filtered-h">Filtered out</h2>
      <p className="small muted" style={{ margin: "0 0 12px" }}>
        {names.size} exercises removed before drafting, grouped by reason.
      </p>
      <ul className="list">
        {shown.map((g) => (
          <li key={`${g.reason}|${g.rule}`}>
            <div style={{ fontWeight: 500 }}>{g.reason}</div>
            <div className="small" style={{ color: "var(--ink-2)" }}>
              {g.details
                ? g.details.map((d) => `${d.name} (${d.detail.replace(/^Needs /, "needs ")})`).join("; ")
                : g.exercises.join(", ")}
            </div>
            <div className="chips">
              {g.rule && <span className="chip">rule: {g.rule}</span>}
              {g.sources.map((s) => (
                <span key={`${s.short}${s.doi}`} className={`chip ${s.checked ? "ok" : "warn"}`}>
                  {s.short ?? s.doi}
                  {s.checked ? "" : " · unchecked"}
                </span>
              ))}
              {!g.trusted && <span className="chip warn">unverified</span>}
            </div>
          </li>
        ))}
      </ul>
      {groups.length > 4 && (
        <button type="button" className="linkish" style={{ marginTop: 12 }} onClick={() => setAll((v) => !v)}>
          {all ? "Show fewer" : `Show all ${groups.length} reasons`}
        </button>
      )}
    </section>
  );
}

function readLine(rows: ReadRow[], kind: ReadRow["kind"]): string | null {
  const r = rows.filter((x) => x.kind === kind);
  if (!r.length) return null;
  return r
    .map((x) =>
      x.status === "accepted"
        ? `“${x.said}” → ${x.understood_as} (${x.method}, ${x.confidence.toFixed(2)})`
        : `“${x.said}” → ${x.status.replace("_", " ")}`,
    )
    .join("; ");
}

function TraceCard({ plan }: { plan: Plan }) {
  const t = plan.trace;
  const excludedCount = new Set(t.excluded.flatMap((g) => g.exercises)).size;
  const picked = plan.blocks.reduce((n, b) => n + b.items.length, 0);
  const download = () => {
    // The server builds the full JSON-LD (context, @ids, one activity per stage). Older stored
    // plans only have the safety filter's records, wrapped here as before.
    const doc = t.jsonld ?? { "@context": { prov: "http://www.w3.org/ns/prov#" }, "@graph": t.prov ?? [] };
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(doc, null, 2)], { type: "application/ld+json" }),
    );
    const a = document.createElement("a");
    a.href = url;
    a.download = `trace-${plan.id}.jsonld`;
    a.click();
    URL.revokeObjectURL(url);
  };
  const lines: [string, string | null][] = [
    ["Focus", readLine(t.read, "focus")],
    ["Injury mentions", readLine(t.read, "injury")],
    ["Exclusions", readLine(t.read, "exclusion")],
    ["Missing equipment", readLine(t.read, "equipment")],
  ];
  return (
    <section className="card" aria-labelledby="trace-h">
      <h2 id="trace-h">Why this plan</h2>
      <p className="small muted" style={{ margin: "0 0 12px" }}>
        Recorded by the safety filter and scorer as they ran. No reason here is written by the model.
      </p>
      <ol className="trace">
        <li>
          <strong>Request read.</strong>{" "}
          {lines
            .filter(([, v]) => v)
            .map(([k, v]) => `${k}: ${v}`)
            .join(". ") || "Nothing specific."}
        </li>
        <li>
          <strong>Restrictions.</strong>{" "}
          {t.restrictions.length
            ? t.restrictions
                .map(
                  (r) =>
                    `${r.regions.map((x) => x.replace("region:", "")).join(", ")}${r.side ? ` (${r.side})` : ""} from ${r.from}${r.condition ? `, ${r.condition.replace("condition:", "")}` : ""}`,
                )
                .join("; ")
            : "None."}
        </li>
        <li>
          <strong>Safety filter.</strong> {excludedCount} exercises excluded for {t.excluded.length} reasons.
        </li>
        <li>
          <strong>Selection.</strong> {picked} picked from the safe candidates by{" "}
          {t.model_calls.find((c) => c.purpose === "selection")?.model ?? "the model"}, then fitted to{" "}
          {plan.minutes_requested} minutes by the server.
        </li>
      </ol>
      <button type="button" className="linkish" style={{ marginTop: 12 }} onClick={download}>
        Download trace (JSON-LD)
      </button>
    </section>
  );
}
