import type { ChartSpec, CongratsDraft, CopilotAnswer, GenerateEvent, MemberView } from "./types";
import { authHeaders, sessionExpired } from "./auth";

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...(await authHeaders()), ...(init?.headers ?? {}) },
  });
  if (!res.ok) {
    if (res.status === 401) sessionExpired();
    let detail = `Request failed (${res.status})`;
    try {
      const body = (await res.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      // keep the generic message
    }
    throw new Error(detail);
  }
  return (await res.json()) as T;
}

export const api = {
  members: () => call<{ id: string; name: string; fictional: boolean }[]>("/api/members"),
  member: (id: string) => call<MemberView>(`/api/members/${encodeURIComponent(id)}`),
  chart: (id: string, kind: string) =>
    call<ChartSpec>(`/api/members/${encodeURIComponent(id)}/charts/${kind}`),
  copilot: (id: string, question: string) =>
    call<CopilotAnswer>(`/api/members/${encodeURIComponent(id)}/copilot`, {
      method: "POST",
      body: JSON.stringify({ question }),
    }),
  congratulate: (id: string) =>
    call<CongratsDraft>(`/api/members/${encodeURIComponent(id)}/congratulate`, { method: "POST" }),
  confirm: (planId: string) =>
    call<{ id: string; status: string; confirmed_at: string }>(
      `/api/plans/${encodeURIComponent(planId)}/confirm`,
      {
        method: "POST",
      },
    ),
};

export interface GenerateBody {
  member_id: string;
  prompt: string;
  minutes: number | null;
  cleared_low_impact: string[];
  confirmed_regions: { region: string; side: string | null }[];
}

/** POST /api/generate and yield server-sent events as they arrive. */
export async function* generate(body: GenerateBody, signal?: AbortSignal): AsyncGenerator<GenerateEvent> {
  const res = await fetch("/api/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(await authHeaders()) },
    body: JSON.stringify(body),
    signal,
  });
  if (res.status === 401) sessionExpired();
  if (!res.ok || !res.body) throw new Error(`Request failed (${res.status})`);
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let idx;
    while ((idx = buf.indexOf("\n\n")) >= 0) {
      const chunk = buf.slice(0, idx);
      buf = buf.slice(idx + 2);
      const data = chunk
        .split("\n")
        .filter((l) => l.startsWith("data: "))
        .map((l) => l.slice(6))
        .join("\n");
      if (data) yield JSON.parse(data) as GenerateEvent;
    }
  }
}
