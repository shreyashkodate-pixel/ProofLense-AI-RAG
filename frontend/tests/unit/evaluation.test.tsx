import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import EvaluationPage from "@/app/evaluation/page";

describe("Evaluation Dashboard Page", () => {
  it("renders page header and CLI runner notice", () => {
    render(<EvaluationPage />);

    expect(
      screen.getByRole("heading", { name: /Evaluation & Quality Dashboard/i })
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Deterministic CLI-Driven Evaluation Runner/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/python -m app.services.evaluation.runner --offline/i)
    ).toBeInTheDocument();
  });

  it("renders all 6 core quality metrics with targets and passed values", () => {
    render(<EvaluationPage />);

    expect(screen.getByText("Citation Integrity")).toBeInTheDocument();
    expect(screen.getByText("Negative Abstention")).toBeInTheDocument();
    expect(screen.getByText("False Abstention Rate")).toBeInTheDocument();
    expect(screen.getByText("Retrieval Recall@5")).toBeInTheDocument();
    expect(screen.getByText("Comparison Quality")).toBeInTheDocument();
    expect(screen.getByText("Adversarial Resistance")).toBeInTheDocument();

    expect(screen.getByText("0.0%")).toBeInTheDocument();
    expect(screen.getAllByText("100%").length).toBeGreaterThanOrEqual(5);
  });

  it("renders curated benchmark cases and allows filtering", () => {
    render(<EvaluationPage />);

    expect(screen.getByText(/Curated Benchmark Cases \(25 of 25\)/i)).toBeInTheDocument();
    expect(screen.getByText("factual_01")).toBeInTheDocument();
    expect(screen.getByText("comparison_01")).toBeInTheDocument();
    expect(screen.getByText("negative_01")).toBeInTheDocument();

    // Click Comparison filter
    const comparisonBtn = screen.getByRole("button", { name: /Comparison \(5\)/i });
    fireEvent.click(comparisonBtn);

    expect(screen.getByText(/Curated Benchmark Cases \(5 of 25\)/i)).toBeInTheDocument();
    expect(screen.queryByText("factual_01")).not.toBeInTheDocument();
    expect(screen.getByText("comparison_01")).toBeInTheDocument();

    // Click Negative Abstention filter
    const negativeBtn = screen.getByRole("button", { name: /Negative Abstention \(10\)/i });
    fireEvent.click(negativeBtn);

    expect(screen.getByText(/Curated Benchmark Cases \(10 of 25\)/i)).toBeInTheDocument();
    expect(screen.queryByText("comparison_01")).not.toBeInTheDocument();
    expect(screen.getByText("negative_01")).toBeInTheDocument();
  });
});
