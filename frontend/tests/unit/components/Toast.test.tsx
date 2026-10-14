import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { ToastProvider, useToast } from "@/components/ui/Toast";

const TestTrigger = () => {
  const { addToast } = useToast();
  return (
    <button
      onClick={() =>
        addToast({
          type: "success",
          title: "File Uploaded",
          message: "Q3_Report.pdf ready",
        })
      }
    >
      Trigger Toast
    </button>
  );
};

describe("Toast component and context", () => {
  it("renders toast when triggered by addToast", () => {
    render(
      <ToastProvider>
        <TestTrigger />
      </ToastProvider>
    );

    fireEvent.click(screen.getByText("Trigger Toast"));
    expect(screen.getByText("File Uploaded")).toBeInTheDocument();
    expect(screen.getByText("Q3_Report.pdf ready")).toBeInTheDocument();
  });

  it("removes toast when dismiss button is clicked", () => {
    render(
      <ToastProvider>
        <TestTrigger />
      </ToastProvider>
    );

    fireEvent.click(screen.getByText("Trigger Toast"));
    expect(screen.getByText("File Uploaded")).toBeInTheDocument();

    const dismissBtn = screen.getByRole("button", { name: /dismiss notification/i });
    fireEvent.click(dismissBtn);
    expect(screen.queryByText("File Uploaded")).not.toBeInTheDocument();
  });
});
