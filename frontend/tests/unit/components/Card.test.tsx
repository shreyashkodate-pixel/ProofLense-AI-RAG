import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { Card } from "@/components/ui/Card";

describe("Card component", () => {
  it("renders children content cleanly", () => {
    render(<Card>Card body text</Card>);
    expect(screen.getByText("Card body text")).toBeInTheDocument();
  });

  it("renders title and subtitle when provided", () => {
    render(
      <Card title="Workspace Summary" subtitle="4 documents uploaded">
        Body
      </Card>
    );
    expect(screen.getByText("Workspace Summary")).toBeInTheDocument();
    expect(screen.getByText("4 documents uploaded")).toBeInTheDocument();
  });
});
