import { render } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { Skeleton } from "@/components/ui/Skeleton";

describe("Skeleton component", () => {
  it("renders with aria-hidden='true' for accessibility", () => {
    const { container } = render(<Skeleton width="100px" height="20px" />);
    const skeleton = container.firstChild as HTMLElement;
    expect(skeleton).toHaveAttribute("aria-hidden", "true");
    expect(skeleton).toHaveStyle({ width: "100px", height: "20px" });
  });

  it("renders text and circle variants", () => {
    const { container: textContainer } = render(<Skeleton variant="text" />);
    expect(textContainer.firstChild).toBeInTheDocument();

    const { container: circleContainer } = render(<Skeleton variant="circle" width="40px" height="40px" />);
    expect(circleContainer.firstChild).toBeInTheDocument();
  });
});
