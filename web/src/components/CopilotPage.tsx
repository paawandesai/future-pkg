import { useState, type FormEvent } from "react";
import { api, MAX_HISTORY } from "../api";
import type { ChartSpec, CongratsDraft, CopilotAnswer, CopilotTurn, MemberView } from "../types";
import { Chart } from "./Chart";

const QUICK: { label: string; chart?: string; question?: string }[] = [
  { label: "Show me the brief", question: "Show me the brief" },
  { label: "How's adherence trending?", question: "How's adherence trending?" },
  { label: "Sleep this week", question: "How has sleep been this week?" },
  { label: "What changed since last week?", question: "What changed since last week?" },
  { label: "Plot adherence trend", chart: "adherence" },
  { label: "Show message pattern", chart: "messages" },
  { label: "Compare last 4 weeks", chart: "compare" },
];

const LAB_LABELS: Record<string, string> = {
  ldl_mg_dl: "LDL (mg/dL)",
  hdl_mg_dl: "HDL (mg/dL)",
  triglycerides_mg_dl: "Triglycerides (mg/dL)",
  hba1c_pct: "HbA1c (%)",
  vitamin_d_ng_ml: "Vitamin D (ng/mL)",
  ferritin_ng_ml: "Ferritin (ng/mL)",
  crp_mg_l: "CRP (mg/L)",
  body_fat_pct: "Body fat (%)",
  lean_mass_kg: "Lean mass (kg)",
  fat_mass_kg: "Fat mass (kg)",
  bone_density_z_score: "Bone density Z-score",
  visceral_fat_cm2: "Visceral fat (cm²)",
};

interface Exchange {
  question: string;
  answer: CopilotAnswer;
}

/** The last turns of the thread, oldest first, as the API expects them. */
export function recentTurns(thread: Exchange[], max = MAX_HISTORY): CopilotTurn[] {
  const turns: CopilotTurn[] = thread.flatMap((x) => [
    { role: "coach" as const, text: x.question },
    { role: "copilot" as const, text: x.answer.answer },
  ]);
  return turns.slice(-max);
}

export function CopilotPage({ member }: { member: MemberView }) {
  const first = member.name.split(" ")[0];
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [thread, setThread] = useState<Exchange[]>([]);
  const [charts, setCharts] = useState<ChartSpec[]>([]);
  const [draft, setDraft] = useState<CongratsDraft | null>(null);
  const [draftText, setDraftText] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function guarded(label: string, fn: () => Promise<void>) {
    setBusy(label);
    setError(null);
    try {
      await fn();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(null);
    }
  }

  const ask = (q: string) =>
    guarded("ask", async () => {
      const a = await api.copilot(member.id, q, recentTurns(thread));
      setThread((t) => [...t, { question: q, answer: a }]);
      setQuestion("");
      if (a.charts.length) setCharts(a.charts);
    });

  const quick = (q: (typeof QUICK)[number]) =>
    q.chart
      ? guarded(q.label, async () => {
          const spec = await api.chart(member.id, q.chart as string);
          setCharts((cs) => [spec, ...cs.filter((c) => c.title !== spec.title)].slice(0, 4));
        })
      : ask(q.question as string);

  const congratulate = () =>
    guarded("draft", async () => {
      const d = await api.congratulate(member.id);
      setDraft(d);
      setDraftText(d.draft ?? "");
    });

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (question.trim()) void ask(question.trim());
  };

  return (
    <div className="layout">
      <div className="wide">
        <section className="card" aria-labelledby="ask-h">
          <h2 id="ask-h">Ask about {first}</h2>
          <div className="prompts">
            {QUICK.map((q) => (
              <button
                key={q.label}
                type="button"
                className="btn small"
                disabled={busy !== null}
                onClick={() => void quick(q)}
              >
                {q.label}
              </button>
            ))}
            <button
              type="button"
              className="btn small"
              disabled={busy !== null}
              onClick={() => void congratulate()}
            >
              Draft a congratulations
            </button>
          </div>
          <form className="row" style={{ marginTop: 12, alignItems: "flex-end" }} onSubmit={submit}>
            <div className="field" style={{ flex: "1 1 300px" }}>
              <label htmlFor="ask">Question</label>
              <input
                id="ask"
                className="input"
                type="text"
                maxLength={1000}
                placeholder={`Ask a question about ${first}`}
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
              />
            </div>
            <button type="submit" className="btn primary" disabled={busy !== null || !question.trim()}>
              {busy === "ask" ? "Asking…" : "Ask"}
            </button>
          </form>
          <p className="small muted" style={{ margin: "10px 0 0" }}>
            Answers only use {first}'s record. The copilot can read; it can't change or send anything.
          </p>
          {error && (
            <p role="alert" className="notice alert">
              {error}
            </p>
          )}
          {thread.length > 0 && (
            <div style={{ marginTop: 16 }}>
              <ol className="thread" aria-label="Conversation" aria-live="polite">
                {thread.map((x, i) => (
                  <li key={i} style={{ marginBottom: 14 }}>
                    <div className="xsmall muted">You asked</div>
                    <div className="small" style={{ marginBottom: 6 }}>
                      {x.question}
                    </div>
                    <div className="answer">{x.answer.answer}</div>
                    <p className="xsmall muted" style={{ margin: "8px 0 0" }}>
                      {x.answer.disclosure}{" "}
                      {x.answer.tools_used.length
                        ? `Read: ${[...new Set(x.answer.tools_used)].join(", ")}.`
                        : ""}
                    </p>
                  </li>
                ))}
              </ol>
              <div className="row" style={{ justifyContent: "space-between" }}>
                <span className="xsmall muted">
                  Follow-ups include the last {MAX_HISTORY} turns of this conversation.
                </span>
                <button
                  type="button"
                  className="btn small"
                  disabled={busy !== null}
                  onClick={() => setThread([])}
                >
                  New conversation
                </button>
              </div>
            </div>
          )}
        </section>

        {charts.length > 0 && (
          <div className="charts">
            {charts.map((c) => (
              <Chart key={c.title} spec={c} />
            ))}
          </div>
        )}

        {draft && (
          <section className="card" aria-labelledby="draft-h">
            <h2 id="draft-h">Congratulations draft, for you to edit and send</h2>
            {draft.note && (
              <p role="status" className="notice">
                {draft.note}
              </p>
            )}
            {draft.draft ? (
              <>
                <label htmlFor="draft" className="label">
                  Draft message
                </label>
                <textarea
                  id="draft"
                  className="input"
                  style={{ width: "100%", marginTop: 6 }}
                  rows={5}
                  value={draftText}
                  onChange={(e) => setDraftText(e.target.value)}
                />
                <div className="row" style={{ justifyContent: "space-between", marginTop: 8 }}>
                  <span className="small muted">
                    {draft.disclosure} Sending happens from your messaging tool, not here.
                  </span>
                  <button
                    type="button"
                    className="btn small"
                    onClick={() => void navigator.clipboard?.writeText(draftText)}
                  >
                    Copy draft
                  </button>
                </div>
              </>
            ) : (
              <p className="muted">{draft.reason}</p>
            )}
          </section>
        )}
      </div>

      <aside className="side">
        <ChurnCard member={member} />
        <section className="card" aria-labelledby="brief-h">
          <h2 id="brief-h">Morning brief</h2>
          <div className="small muted">Provided brief text, shown as written</div>
          <ul className="small" style={{ paddingLeft: 18 }}>
            {member.brief.morning_tasks.map((t) => (
              <li key={t}>{t}</li>
            ))}
          </ul>
        </section>
        <section className="card" aria-labelledby="chat-h">
          <h2 id="chat-h">Recent messages</h2>
          <div style={{ display: "flex", flexDirection: "column", gap: 10, marginTop: 8 }}>
            {member.chat.map((m, i) =>
              m.provenance === "member-said" ? (
                <blockquote key={i} className="quote">
                  <div className="xsmall muted">Member said · {m.ts?.slice(0, 10)}</div>“{m.quote}”
                  {m.attachments.map((a, j) => (
                    <div
                      key={j}
                      className="img-placeholder"
                      role="img"
                      aria-label={`Image attachment placeholder: ${a.caption ?? "no caption"}`}
                    >
                      <span aria-hidden="true">▢</span> Image not shown · “{a.caption ?? "no caption"}”
                    </div>
                  ))}
                </blockquote>
              ) : (
                <div key={i} className="coach-line">
                  <div className="xsmall muted">Coach · {m.ts?.slice(0, 10)}</div>
                  {m.quote}
                </div>
              ),
            )}
          </div>
        </section>
        {member.biomarkers && <BiomarkerCard b={member.biomarkers} sleepAvg={member.sleep.average} />}
        <section className="card" aria-labelledby="labs-h">
          <h2 id="labs-h">Labs and body composition</h2>
          <p className="small muted" style={{ marginTop: 0 }}>
            Values as recorded. No interpretation is offered here.
          </p>
          {Object.entries(member.labs.labs).map(([panel, values]) => (
            <table key={panel} className="kv" style={{ marginBottom: 8 }}>
              <tbody>
                {Object.entries(values)
                  .filter(([k]) => k !== "date")
                  .map(([k, v]) => (
                    <tr key={k}>
                      <td>{LAB_LABELS[k] ?? k}</td>
                      <td>{String(v)}</td>
                    </tr>
                  ))}
                <tr>
                  <td className="xsmall muted" colSpan={2}>
                    {panel.replace(/_/g, " ")} · {String(values.date ?? "")}
                  </td>
                </tr>
              </tbody>
            </table>
          ))}
        </section>
      </aside>
    </div>
  );
}

function BiomarkerCard({
  b,
  sleepAvg,
}: {
  b: NonNullable<MemberView["biomarkers"]>;
  sleepAvg: number | null;
}) {
  const latest = b.weight_kg.length ? b.weight_kg[b.weight_kg.length - 1] : null;
  const rows: [string, string][] = [
    [
      "Resting heart rate",
      b.resting_hr_bpm ? `${b.resting_hr_bpm.value} ${b.resting_hr_bpm.unit}` : "Not recorded",
    ],
    ["HRV", b.hrv_ms ? `${b.hrv_ms.value} ${b.hrv_ms.unit}` : "Not recorded"],
    ["Sleep, 7-night average", sleepAvg !== null ? `${sleepAvg} h` : "Not recorded"],
    ["Weight", latest ? `${latest.kg} kg · ${latest.date}` : "Not recorded"],
  ];
  return (
    <section className="card" aria-labelledby="bio-h">
      <h2 id="bio-h">Biomarkers</h2>
      <table className="kv">
        <tbody>
          {rows.map(([k, v]) => (
            <tr key={k}>
              <td>{k}</td>
              <td>{v}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="xsmall muted" style={{ margin: "6px 0 0" }}>
        {b.note}
      </p>
    </section>
  );
}

function ChurnCard({ member }: { member: MemberView }) {
  const c = member.churn;
  return (
    <section id="churn" className="card" aria-labelledby="churn-h">
      <h2 id="churn-h">Churn risk</h2>
      <div className="split" style={{ marginTop: 8 }}>
        <div>
          <div className="small muted">Our score</div>
          <div className="score">
            {c.score}/{c.max_score}
          </div>
          <div style={{ textTransform: "capitalize" }}>{c.level}</div>
        </div>
        <div>
          <div className="small muted">Provided brief</div>
          <div className="score">—</div>
          <div style={{ textTransform: "capitalize" }}>{c.brief_text?.level ?? "Not given"}</div>
        </div>
      </div>
      <ul className="small" style={{ paddingLeft: 18 }}>
        {c.features.map((f) => (
          <li key={f.name}>
            {f.name}: {f.value} <span className="muted">(+{f.points})</span>
          </li>
        ))}
      </ul>
      {c.brief_text?.reasons && (
        <>
          <div className="small muted">The brief's reasons, as written</div>
          <ul className="small" style={{ paddingLeft: 18 }}>
            {c.brief_text.reasons.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        </>
      )}
      <p className="xsmall muted" style={{ margin: 0 }}>
        Inputs: adherence, logins, member messages, missed sessions. Health data is never used.
        {c.uses_generated_data.length > 0 && " Login events are generated demo data."}
      </p>
    </section>
  );
}
