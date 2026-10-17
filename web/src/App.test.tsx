import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { App } from "./App";

afterEach(cleanup);

describe("App", () => {
  it("shows the demo banner", () => {
    render(<App />);
    expect(screen.getByRole("banner").textContent).toContain("synthetic data only");
  });

  it("links the third-party notices", () => {
    render(<App />);
    expect(screen.getByRole("link", { name: "third-party notices" }).getAttribute("href")).toBe(
      "/third-party-notices.txt",
    );
  });
});
