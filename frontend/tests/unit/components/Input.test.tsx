import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { Input } from "@/components/ui/Input";

describe("Input component", () => {
  it("renders with label and connects htmlFor with input id", () => {
    render(<Input label="Workspace Name" placeholder="Enter name" />);
    const label = screen.getByText("Workspace Name");
    const input = screen.getByPlaceholderText("Enter name");
    expect(label).toHaveAttribute("for", input.id);
  });

  it("handles user text input correctly", () => {
    const handleChange = vi.fn();
    render(<Input label="Test" onChange={handleChange} placeholder="type here" />);
    const input = screen.getByPlaceholderText("type here");
    fireEvent.change(input, { target: { value: "Hello" } });
    expect(handleChange).toHaveBeenCalled();
  });

  it("renders error message with role='alert' and sets aria-invalid", () => {
    render(
      <Input
        label="Passkey"
        errorMessage="Invalid passkey provided"
        placeholder="Enter key"
      />
    );
    const error = screen.getByRole("alert");
    expect(error).toHaveTextContent("Invalid passkey provided");
    const input = screen.getByPlaceholderText("Enter key");
    expect(input).toHaveAttribute("aria-invalid", "true");
  });

  it("renders helper text when no error exists", () => {
    render(
      <Input
        label="Timeout"
        helperText="Timeout in seconds"
        placeholder="30"
      />
    );
    expect(screen.getByText("Timeout in seconds")).toBeInTheDocument();
  });
});
