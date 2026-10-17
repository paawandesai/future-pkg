// Shapes returned by the API (api/src/coachkg/main.py). Every string from the server is shown as text.

export interface Injury {
  id: string;
  region: string;
  status: string;
  active: boolean;
  /** Only knee injuries can be cleared for low-impact loading. */
  clearable?: boolean;
  notes?: string | null;
}

export interface ChatMessage {
  ts: string | null;
  provenance: "member-said" | "coach-said";
  quote: string;
  attachments: { type: string | null; caption: string | null }[];
}

export interface ChurnFeature {
  name: string;
  value: string;
  points: number;
}

export interface Churn {
  score: number;
  max_score: number;
  level: "low" | "elevated" | "high";
  features: ChurnFeature[];
  uses_generated_data: string[];
  brief_text: { level?: string; reasons?: string[] } | null;
}

export interface BiomarkerValue {
  value: number;
  unit: string;
  date: string | null;
}

export interface Biomarkers {
  resting_hr_bpm: BiomarkerValue | null;
  hrv_ms: BiomarkerValue | null;
  weight_kg: { date: string; kg: number }[];
  note: string;
}

export interface MemberView {
  id: string;
  name: string;
  fictional: boolean;
  as_of: string;
  generated_inputs: string[];
  profile: Record<string, string | number | null>;
  goals: { text: string; priority: number }[];
  preferences: { preferred_session_minutes?: number; training_days_per_week?: number; notes?: string };
  equipment_available: string[];
  injuries: Injury[];
  brief: { generated_for: string | null; morning_tasks: string[] };
  sleep: { average: number | null };
  labs: { labs: Record<string, Record<string, string | number>>; note: string };
  biomarkers?: Biomarkers;
  chat: ChatMessage[];
  churn: Churn;
  review_mentions: { ts: string | null; quote: string; region: string }[];
}

export interface PlanItem {
  exercise_id: string;
  name: string;
  sets: number;
  reps: number | null;
  work_s: number | null;
  rest_s: number;
  each_side: boolean;
  side_note: string | null;
  minutes: number;
  equipment: string[];
  picked_by: "selection" | "fill";
  flags: string[];
  why: string[];
  counted_against: string[];
  path: GraphEdge[];
}

export interface GraphEdge {
  src: string;
  kind: string;
  dst: string;
  /** focus | equipment | member-owns | region-clear | region-cleared | block (absent on older plans) */
  role?: string;
}

export interface Alternative {
  instead_of: string;
  instead_of_id: string;
  needs: string[];
  use: string;
  use_id: string;
  shared_patterns: string[];
  shared_muscles: string[];
  substitute: { use: string; for: string; source: string } | null;
  path: GraphEdge[];
}

export interface PlanBlock {
  name: "warmup" | "main" | "cooldown";
  budget_minutes: number;
  minutes: number;
  items: PlanItem[];
}

export interface ReadRow {
  kind: "injury" | "exclusion" | "equipment" | "focus";
  said: string;
  understood_as: string;
  status: string;
  method: string;
  confidence: number;
}

export interface ExcludedGroup {
  reason: string;
  rule: string | null;
  exercises: string[];
  details?: { name: string; detail: string }[];
  trusted: boolean;
  sources: { short: string | null; doi: string | null; checked: boolean }[];
}

export interface Plan {
  id: string;
  member_id: string;
  status: "draft" | "confirmed";
  created_at: string;
  confirmed_at?: string;
  title: string;
  label: string;
  minutes_requested: number;
  minutes_planned: number;
  blocks: PlanBlock[];
  trace: {
    read: ReadRow[];
    restrictions: {
      regions: string[];
      side: string | null;
      condition: string | null;
      from: string;
      confidence: number;
    }[];
    excluded: ExcludedGroup[];
    alternatives: Alternative[];
    unverified: string[];
    notes: string[];
    model_calls: { purpose: string; model: string; ms: number }[];
    /** PROV-O JSON-LD for the whole run, built server-side (docs/provenance.md). */
    jsonld?: Record<string, unknown>;
    /** Older plans: the safety filter's PROV records only. */
    prov?: Record<string, unknown>[];
  };
  timings_ms: Record<string, number>;
}

export interface Blocker {
  mention: string;
  reason: string;
  candidates: { concept: string; label: string; score?: number }[];
}

export type GenerateEvent =
  | { event: "stage"; stage: string; ms: number }
  | { event: "read"; rows: ReadRow[] }
  | { event: "blocked"; blockers: Blocker[]; read: ReadRow[] }
  | { event: "plan"; plan: Plan }
  | { event: "error"; message: string };

export interface ChartSpec {
  type: "line" | "bar";
  title: string;
  x_key: string;
  series: { key: string; label: string; axis?: "left" | "right" }[];
  // null marks a week before the record starts: no data, not zero.
  data: Record<string, string | number | null>[];
  notes: string[];
}

export interface CopilotAnswer {
  answer: string;
  charts: ChartSpec[];
  tools_used: string[];
  guarded?: boolean;
  disclosure: string;
}

export interface CongratsDraft {
  draft: string | null;
  disclosure?: string;
  member_disclosure?: string;
  reason?: string;
  session_date?: string;
  is_yesterday?: boolean;
  note?: string | null;
}

export interface CopilotTurn {
  role: "coach" | "copilot";
  text: string;
}
