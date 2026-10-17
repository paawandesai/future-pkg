import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { MemberView, Plan } from "../types";
import { Chart } from "./Chart";
import { CopilotPage, recentTurns, withMemberDisclosure } from "./CopilotPage";
import { dose, GeneratorPage } from "./GeneratorPage";

const member: MemberView = {
  id: "m1",
  name: "Jordan Rivera",
  fictional: true,
  as_of: "2026-06-04",
  generated_inputs: ["login events"],
  profile: { age: 41, tier: "1:1 Coaching" },
  goals: [],
  preferences: { preferred_session_minutes: 50 },
  equipment_available: [],
  injuries: [{ id: "inj", region: "left knee", status: "recovering", active: true }],
  brief: { generated_for: "2026-06-04", morning_tasks: ["Congratulate Jordan."] },
  sleep: { average: 6.3 },
  labs: { labs: { blood_panel: { date: "2026-04-20", vitamin_d_ng_ml: 28 } }, note: "" },
  biomarkers: {
    resting_hr_bpm: { value: 58, unit: "bpm", date: null },
    hrv_ms: { value: 47, unit: "ms", date: null },
    weight_kg: [{ date: "2026-06-02", kg: 71.2 }],
    note: "Values as recorded, not interpreted.",
  },
  chat: [
    {
      ts: "2026-06-03T18:42:00-07:00",
      provenance: "member-said",
      quote: "<img src=x onerror=alert(1)> knee felt okay",
      attachments: [{ type: "image", caption: "Home setup photo" }],
    },
  ],
  churn: {
    score: 6,
    max_score: 11,
    level: "elevated",
    features: [{ name: "Adherence", value: "62% vs 100%", points: 2 }],
    uses_generated_data: ["logins"],
    brief_text: { level: "elevated", reasons: ["Adherence fell"] },
  },
  review_mentions: [{ ts: "2026-06-03", quote: "Knee felt okay", region: "Knee" }],
};

const plan: Plan = {
  id: "p1",
  member_id: "m1",
  status: "draft",
  created_at: "2026-06-04T09:00:00Z",
  title: "Upper body · 30 min",
  label: "Coach decision support: a draft for the coach to review and confirm.",
  minutes_requested: 30,
  minutes_planned: 28,
  blocks: [
    {
      name: "main",
      budget_minutes: 25,
      minutes: 24,
      items: [
        {
          exercise_id: "e1",
          name: "Dumbbell Neutral-Grip Bench Press",
          sets: 3,
          reps: 10,
          work_s: null,
          rest_s: 60,
          each_side: false,
          side_note: null,
          minutes: 4.3,
          equipment: ["Dumbbell"],
          picked_by: "selection",
          flags: [],
          why: [
            "uses only equipment the member has (Dumbbell)",
            "picked for the main block by the selection step",
          ],
          counted_against: [],
          path: [
            { src: "ex:E1", kind: "requires", dst: "equipment:dumbbell", role: "equipment" },
            { src: "member:mbr_1", kind: "has-equipment", dst: "equipment:dumbbell", role: "member-owns" },
            { src: "ex:E1", kind: "stresses", dst: "region:shoulder", role: "region-clear" },
            { src: "ex:E1", kind: "has-pattern", dst: "pattern:upper push - horizontal", role: "block" },
          ],
        },
      ],
    },
  ],
  trace: {
    read: [],
    restrictions: [],
    alternatives: [],
    excluded: [
      { reason: "Loads the left knee", rule: null, exercises: ["Jumping Jack"], trusted: true, sources: [] },
    ],
    unverified: ["Kneeling flag has no checked source"],
    notes: [],
    model_calls: [{ purpose: "selection", model: "claude-test", ms: 1 }],
    jsonld: { "@context": { prov: "http://www.w3.org/ns/prov#" }, "@graph": [] },
  },
  timings_ms: { total: 2500 },
};

function sse(events: unknown[]) {
  const body = events.map((e) => `event: x\ndata: ${JSON.stringify(e)}\n\n`).join("");
  return new Response(body, { status: 200 });
}

function wrap(node: React.ReactNode) {
  return <QueryClientProvider client={new QueryClient()}>{node}</QueryClientProvider>;
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("dose", () => {
  it("formats reps, timed work and sides", () => {
    expect(dose({ ...plan.blocks[0].items[0] })).toBe("3 × 10");
    expect(dose({ ...plan.blocks[0].items[0], reps: null, work_s: 40, each_side: true })).toBe(
      "3 × 40 s / side",
    );
  });
});

describe("GeneratorPage", () => {
  it("streams a draft plan and confirms it", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        sse([
          { event: "stage", stage: "intent", ms: 1 },
          { event: "plan", plan },
        ]),
      )
      .mockResolvedValueOnce(
        Response.json({ id: "p1", status: "confirmed", confirmed_at: "2026-06-04T09:20:00Z" }),
      );
    render(wrap(<GeneratorPage member={member} />));
    fireEvent.change(screen.getByLabelText(/focus on/i), { target: { value: "upper body" } });
    fireEvent.click(screen.getByRole("button", { name: "Draft plan" }));
    expect(await screen.findByText("Dumbbell Neutral-Grip Bench Press")).toBeTruthy();
    expect(screen.getByText("Draft")).toBeTruthy();
    expect(screen.getByText(/Unverified:/)).toBeTruthy();
    expect(screen.getByText("Chosen because:", { exact: false }).parentElement?.textContent).toContain(
      "uses only equipment the member has (Dumbbell)",
    );
    const path = screen.getByLabelText("Graph path");
    expect(path.textContent).toContain(
      "Equipment: this exercise requires dumbbell · member has-equipment dumbbell",
    );
    expect(path.textContent).toContain("Regions: this exercise stresses shoulder (not restricted)");
    expect(path.textContent).toContain("Block: this exercise has-pattern upper push - horizontal");
    fireEvent.click(screen.getByRole("button", { name: "Confirm plan" }));
    await waitFor(() => expect(screen.getByText("Confirmed by demo coach")).toBeTruthy());
    expect(fetchMock).toHaveBeenLastCalledWith(
      "/api/plans/p1/confirm",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("stops at a blocker and offers the candidate regions", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      sse([
        {
          event: "blocked",
          read: [],
          blockers: [
            {
              mention: "her leg",
              reason: "The body region in the request is unclear.",
              candidates: [
                { concept: "region:knee", label: "Knee", score: 0.8 },
                { concept: "region:hip", label: "Hip", score: 0.77 },
              ],
            },
          ],
        },
      ]),
    );
    render(wrap(<GeneratorPage member={member} />));
    fireEvent.change(screen.getByLabelText(/focus on/i), { target: { value: "her leg hurts" } });
    fireEvent.click(screen.getByRole("button", { name: "Draft plan" }));
    expect(await screen.findByText("Drafting paused: confirm the body region")).toBeTruthy();
    expect(screen.getByLabelText(/All candidates/)).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Confirm plan" })).toBeNull();
  });

  it("shows member text as a quote that can't lift the restriction", () => {
    render(wrap(<GeneratorPage member={member} />));
    expect(screen.getByText(/can't lift a restriction/)).toBeTruthy();
  });
});

describe("CopilotPage", () => {
  it("renders member text as text, images as captioned placeholders, labs without interpretation", () => {
    const { container } = render(wrap(<CopilotPage member={member} />));
    expect(container.querySelector("img")).toBeNull();
    expect(screen.getByText(/<img src=x/)).toBeTruthy();
    expect(screen.getByRole("img", { name: /Home setup photo/ })).toBeTruthy();
    expect(screen.getByText("Vitamin D (ng/mL)")).toBeTruthy();
    expect(screen.queryByRole("button", { name: /send/i })).toBeNull();
  });

  it("shows resting HR and HRV as values only", () => {
    render(wrap(<CopilotPage member={member} />));
    expect(screen.getByText("Resting heart rate")).toBeTruthy();
    expect(screen.getByText("58 bpm")).toBeTruthy();
    expect(screen.getByText("47 ms")).toBeTruthy();
    expect(screen.getByText(/not interpreted/)).toBeTruthy();
  });

  it("keeps the thread and sends earlier turns with a follow-up", async () => {
    const answer = (text: string) =>
      Response.json({ answer: text, charts: [], tools_used: ["get_adherence"], disclosure: "AI-generated." });
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(answer("Adherence fell to 50%."))
      .mockResolvedValueOnce(answer("The week before it was 75%."));
    render(wrap(<CopilotPage member={member} />));
    const input = screen.getByLabelText("Question");
    fireEvent.change(input, { target: { value: "How's adherence?" } });
    fireEvent.click(screen.getByRole("button", { name: "Ask" }));
    expect(await screen.findByText("Adherence fell to 50%.")).toBeTruthy();
    fireEvent.change(input, { target: { value: "And the week before?" } });
    fireEvent.click(screen.getByRole("button", { name: "Ask" }));
    expect(await screen.findByText("The week before it was 75%.")).toBeTruthy();
    expect(screen.getByText("Adherence fell to 50%.")).toBeTruthy(); // not replaced
    const body = JSON.parse(String((fetchMock.mock.calls[1][1] as RequestInit).body));
    expect(body.question).toBe("And the week before?");
    expect(body.history).toEqual([
      { role: "coach", text: "How's adherence?" },
      { role: "copilot", text: "Adherence fell to 50%." },
    ]);
  });

  it("shows a note when the session to congratulate wasn't yesterday", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      Response.json({
        draft: "Nice work on the session.",
        disclosure: "Drafted by AI.",
        is_yesterday: false,
        note: "The latest completed session is from 2026-05-27, not yesterday (2026-06-03).",
      }),
    );
    render(wrap(<CopilotPage member={member} />));
    fireEvent.click(screen.getByRole("button", { name: "Draft a congratulations" }));
    expect(await screen.findByText(/not yesterday/)).toBeTruthy();
  });
});

describe("withMemberDisclosure", () => {
  it("adds the member-facing AI line once", () => {
    const line = "(Written with help from AI and reviewed by your coach.)";
    expect(withMemberDisclosure(" Great job. ", line)).toBe(`Great job.\n\n${line}`);
    expect(withMemberDisclosure(`Great job.\n\n${line}`, line)).toBe(`Great job.\n\n${line}`);
    expect(withMemberDisclosure("Great job.")).toBe("Great job.");
  });
});

describe("recentTurns", () => {
  it("keeps only the last turns, oldest first", () => {
    const thread = Array.from({ length: 5 }, (_, i) => ({
      question: `q${i}`,
      answer: { answer: `a${i}`, charts: [], tools_used: [], disclosure: "" },
    }));
    const turns = recentTurns(thread);
    expect(turns).toHaveLength(6);
    expect(turns[0]).toEqual({ role: "coach", text: "q2" });
    expect(turns[5]).toEqual({ role: "copilot", text: "a4" });
  });
});

describe("Chart", () => {
  it("reads weeks before the record as no data, not zero", () => {
    render(
      <Chart
        spec={{
          type: "bar",
          title: "Last 4 weeks vs the 4 before",
          x_key: "week_of",
          series: [
            { key: "sessions_completed", label: "Sessions completed" },
            { key: "adherence_pct", label: "Weekly completion (%)", axis: "right" },
          ],
          data: [
            { week_of: "2026-05-04", sessions_completed: null, adherence_pct: null },
            { week_of: "2026-06-01", sessions_completed: 2, adherence_pct: 50 },
          ],
          notes: ["Weeks before the record starts are shown as no data, not zero."],
        }}
      />,
    );
    expect(
      screen.getByText(/2026-05-04: Sessions completed no data, Weekly completion \(%\) no data/),
    ).toBeTruthy();
    expect(screen.getByText(/2026-06-01: Sessions completed 2, Weekly completion \(%\) 50/)).toBeTruthy();
  });
});
