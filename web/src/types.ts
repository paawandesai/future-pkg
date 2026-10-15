// Shapes returned by the API (api/src/coachkg/main.py). Every string from the server is shown as text.

export interface Injury {
  id: string;
  region: string;
  status: string;
  active: boolean;
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
    unverified: string[];
    notes: string[];
    model_calls: { purpose: string; model: string; ms: number }[];
    prov: Record<string, unknown>[];
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
  series: { key: string; label: string }[];
  data: Record<string, string | number>[];
  notes: string[];
}

export interface CopilotAnswer {
  answer: string;
  charts: ChartSpec[];
  tools_used: string[];
  disclosure: string;
}

export interface CongratsDraft {
  draft: string | null;
  disclosure?: string;
  reason?: string;
}
