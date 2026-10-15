import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { App } from "./App";

describe("App", () => {
  it("shows the demo banner", () => {
    render(<App />);
    expect(screen.getByRole("banner").textContent).toContain("synthetic data only");
  });
});
