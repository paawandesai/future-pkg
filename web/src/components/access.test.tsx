import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AdminPage } from "./AdminPage";
import { RequestAccess } from "./RequestAccess";

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("RequestAccess", () => {
  it("sends the request and says what happens next", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(json({ status: "received" }, 202));
    render(<RequestAccess onBack={() => {}} />);
    fireEvent.change(screen.getByLabelText("Work email"), { target: { value: "r@example.com" } });
    fireEvent.change(screen.getByLabelText("Why you'd like access"), { target: { value: "Grading" } });
    fireEvent.click(screen.getByRole("button", { name: "Send request" }));
    await screen.findByText(/Request received/);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/access-requests");
    expect(JSON.parse(String(init?.body))).toEqual({ email: "r@example.com", name: "", reason: "Grading" });
  });
});

describe("AdminPage", () => {
  it("lists pending requests and approves one", async () => {
    const pending = {
      id: "r1",
      email: "r@example.com",
      name: "",
      reason: "Grading",
      status: "pending",
      created_at: "2026-10-15T19:00:00+00:00",
      decided_by: null,
      decided_at: null,
    };
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith("/approve")) return json({ ...pending, status: "approved" });
      if (url === "/api/admin/requests") return json(init?.method === "POST" ? {} : [pending]);
      return json([]);
    });
    render(
      <QueryClientProvider client={new QueryClient()}>
        <AdminPage />
      </QueryClientProvider>,
    );
    await screen.findByText("r@example.com");
    fireEvent.click(screen.getByRole("button", { name: "Approve and invite" }));
    await waitFor(() =>
      expect(fetchMock.mock.calls.some(([u]) => String(u) === "/api/admin/requests/r1/approve")).toBe(true),
    );
  });

  it("rejects every pending request after a confirm", async () => {
    const req = (id: string) => ({
      id,
      email: `${id}@example.com`,
      name: "",
      reason: "Grading",
      status: "pending",
      created_at: "2026-10-15T19:00:00+00:00",
      decided_by: null,
      decided_at: null,
    });
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith("/reject-pending")) return json({ rejected: 2 });
      if (url === "/api/admin/requests") return json([req("a"), req("b")]);
      return json([]);
    });
    vi.spyOn(window, "confirm").mockReturnValue(true);
    render(
      <QueryClientProvider client={new QueryClient()}>
        <AdminPage />
      </QueryClientProvider>,
    );
    fireEvent.click(await screen.findByRole("button", { name: "Reject all pending (2)" }));
    await screen.findByText("Rejected 2 requests.");
    const call = fetchMock.mock.calls.find(([u]) => String(u) === "/api/admin/requests/reject-pending");
    expect(call?.[1]?.method).toBe("POST");
  });
});
