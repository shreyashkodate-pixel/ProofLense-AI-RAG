import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { Badge } from "@/components/ui/Badge";

describe("Badge component", () => {
  it("renders with variant and children", () => {
    render(<Badge variant="success">Ready</Badge>);
    expect(screen.getByText("Ready")).toBeInTheDocument();
  });

  it("renders icon alongside text when provided", () => {
    render(
      <Badge variant="warning" icon={<span data-testid="badge-icon">!</span>}>
        Processing
      </Badge>
    );
    expect(screen.getByText("Processing")).toBeInTheDocument();
    expect(screen.getByTestId("badge-icon")).toBeInTheDocument();
  });
});
