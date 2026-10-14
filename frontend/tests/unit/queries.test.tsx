import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { CitationCard } from "@/components/queries/CitationCard";
import { QueryComposer } from "@/components/queries/QueryComposer";
import { AnswerDisplay } from "@/components/queries/AnswerDisplay";
import WorkspaceQueriesPage from "@/app/workspaces/[workspaceId]/queries/page";
import * as queriesApi from "@/lib/api/queries";
import * as documentsApi from "@/lib/api/documents";
import type { CitationResponse, QueryResponse, DocumentResponse } from "@/lib/api/types";

vi.mock("@/lib/api/queries", () => ({
  executeQuery: vi.fn(),
  listQueries: vi.fn(),
  getQuery: vi.fn(),
}));

vi.mock("@/lib/api/documents", () => ({
  listDocuments: vi.fn(),
}));

const mockCitation: CitationResponse = {
  id: "cite-123",
  chunk_id: "chunk-456",
  document_id: "doc-789",
  document_filename: "annual_report.pdf",
  page_number: 4,
  quoted_snippet: "Operating margin increased by 14.2% year-over-year.",
};

const mockTombstoneCitation: CitationResponse = {
  id: "cite-tombstone",
  chunk_id: null,
  document_id: null,
  document_filename: "deleted_contract.pdf",
  page_number: 12,
  quoted_snippet: "The liability shall not exceed the total fees paid.",
};

const mockGroundedQuery: QueryResponse = {
  query_run_id: "run-001",
  workspace_id: "ws-test",
  query_text: "What was the operating margin growth?",
  status: "completed",
  answer_text: "The operating margin increased by 14.2% year-over-year according to page 4.",
  is_abstention: false,
  top_score: 0.895,
  citations: [mockCitation],
  retrieved_evidence: [
    {
      chunk_id: "chunk-456",
      document_id: "doc-789",
      document_filename: "annual_report.pdf",
      page_number: 4,
      snippet: "Operating margin increased by 14.2% year-over-year.",
      similarity_score: 0.895,
      rank: 1,
    },
  ],
  created_at: new Date().toISOString(),
};

const mockAbstentionQuery: QueryResponse = {
  query_run_id: "run-002",
  workspace_id: "ws-test",
  query_text: "What is the secret formula for Acme Corp?",
  status: "completed",
  answer_text: "I cannot find sufficient evidence in the uploaded documents regarding any secret formula.",
  is_abstention: true,
  top_score: 0.312,
  citations: [],
  retrieved_evidence: [],
  created_at: new Date().toISOString(),
};

const mockDocs: DocumentResponse[] = [
  {
    id: "doc-789",
    workspace_id: "ws-test",
    filename: "annual_report.pdf",
    content_hash: "hash-789",
    file_size_bytes: 10240,
    page_count: 10,
    status: "ready",
    error_message: null,
    processing_attempts: 1,
    processing_started_at: new Date().toISOString(),
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
];

describe("CitationCard Component", () => {
  it("renders document filename, 1-indexed page number, and quote snippet", () => {
    render(
      <CitationCard
        citation={mockCitation}
        workspaceId="ws-test"
      />
    );

    expect(screen.getByText("annual_report.pdf")).toBeInTheDocument();
    expect(screen.getByText("Page 4")).toBeInTheDocument();
    expect(
      screen.getByText(/Operating margin increased by 14.2% year-over-year/i)
    ).toBeInTheDocument();
  });

  it("links to the document viewer with page and snippet parameters when document_id is present", () => {
    render(
      <CitationCard
        citation={mockCitation}
        workspaceId="ws-test"
      />
    );

    const link = screen.getByRole("link");
    expect(link).toHaveAttribute(
      "href",
      `/workspaces/ws-test/documents/doc-789?page=4&snippet=${encodeURIComponent(
        mockCitation.quoted_snippet
      )}`
    );
  });

  it("renders tombstone badge and does not render a link when document_id is null", () => {
    render(
      <CitationCard
        citation={mockTombstoneCitation}
        workspaceId="ws-test"
      />
    );

    expect(screen.getByText("Preserved Snapshot")).toBeInTheDocument();
    expect(screen.getByText("deleted_contract.pdf")).toBeInTheDocument();
    expect(screen.getByText("Page 12")).toBeInTheDocument();
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });
});

describe("QueryComposer Component", () => {
  it("disables submit button when query is empty", () => {
    render(<QueryComposer onSubmit={vi.fn()} isSubmitting={false} />);
    const button = screen.getByRole("button", { name: /Ask Question/i });
    expect(button).toBeDisabled();
  });

  it("enables submit and calls onSubmit with text and top_k", async () => {
    const handleSubmit = vi.fn();
    render(<QueryComposer onSubmit={handleSubmit} isSubmitting={false} />);

    const textarea = screen.getByLabelText(/Query text/i);
    fireEvent.change(textarea, { target: { value: "What is the warranty policy?" } });

    const button = screen.getByRole("button", { name: /Ask Question/i });
    expect(button).not.toBeDisabled();

    fireEvent.click(button);
    expect(handleSubmit).toHaveBeenCalledWith("What is the warranty policy?", 5);
  });

  it("displays character count and prevents submission when exceeding 2000 chars", () => {
    const handleSubmit = vi.fn();
    render(<QueryComposer onSubmit={handleSubmit} isSubmitting={false} />);

    const textarea = screen.getByLabelText(/Query text/i);
    const longText = "a".repeat(2001);
    fireEvent.change(textarea, { target: { value: longText } });

    expect(screen.getByText(/2001 \/ 2000/)).toBeInTheDocument();
    const button = screen.getByRole("button", { name: /Ask Question/i });
    expect(button).toBeDisabled();
  });
});

describe("AnswerDisplay Component", () => {
  it("renders grounded answer, similarity score, and citations", () => {
    render(
      <AnswerDisplay
        response={mockGroundedQuery}
        workspaceId="ws-test"
      />
    );

    expect(
      screen.getByText(/The operating margin increased by 14.2%/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/Similarity: 89.5%/i)).toBeInTheDocument();
    expect(screen.getByText(/Verified Citations \(1\)/i)).toBeInTheDocument();
    expect(screen.getByText("annual_report.pdf")).toBeInTheDocument();
  });

  it("renders explicit abstention banner when is_abstention is true", () => {
    render(
      <AnswerDisplay
        response={mockAbstentionQuery}
        workspaceId="ws-test"
      />
    );

    expect(
      screen.getByText(/Explicit Abstention — Insufficient Grounded Evidence/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/cannot find sufficient evidence/i)
    ).toBeInTheDocument();
  });

  it("allows toggling retrieved evidence passages accordion", () => {
    render(
      <AnswerDisplay
        response={mockGroundedQuery}
        workspaceId="ws-test"
      />
    );

    const toggleBtn = screen.getByRole("button", {
      name: /Retrieved Evidence Passages/i,
    });
    expect(toggleBtn).toBeInTheDocument();
    expect(screen.queryByText(/Rank #1/i)).not.toBeInTheDocument();

    fireEvent.click(toggleBtn);
    expect(screen.getByText(/Rank #1/i)).toBeInTheDocument();
  });
});

describe("WorkspaceQueriesPage Integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(documentsApi.listDocuments).mockResolvedValue(mockDocs);
    vi.mocked(queriesApi.listQueries).mockResolvedValue([mockGroundedQuery]);
  });

  it("renders query history and active query result", async () => {
    render(
      <WorkspaceQueriesPage
        params={{ workspaceId: "ws-test" } as unknown as Promise<{ workspaceId: string }>}
      />
    );

    expect(await screen.findByRole("heading", { name: /Grounded Document Q&A/i })).toBeInTheDocument();
    const queryElements = await screen.findAllByText("What was the operating margin growth?");
    expect(queryElements.length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/The operating margin increased by 14.2%/i)).toBeInTheDocument();
  });

  it("executes a new query and prepends to history", async () => {
    vi.mocked(queriesApi.executeQuery).mockResolvedValue(mockAbstentionQuery);

    render(
      <WorkspaceQueriesPage
        params={{ workspaceId: "ws-test" } as unknown as Promise<{ workspaceId: string }>}
      />
    );

    const textarea = await screen.findByLabelText(/Query text/i);
    fireEvent.change(textarea, {
      target: { value: "What is the secret formula for Acme Corp?" },
    });

    const submitBtn = screen.getByRole("button", { name: /Ask Question/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(queriesApi.executeQuery).toHaveBeenCalledWith("ws-test", {
        query_text: "What is the secret formula for Acme Corp?",
        top_k: 5,
      });
      expect(
        screen.getByText(/Explicit Abstention — Insufficient Grounded Evidence/i)
      ).toBeInTheDocument();
    });
  });
});
