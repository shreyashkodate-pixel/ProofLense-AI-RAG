import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { DocumentSelector } from "@/components/comparison/DocumentSelector";
import { FindingCard } from "@/components/comparison/FindingCard";
import { ComparisonMatrix } from "@/components/comparison/ComparisonMatrix";
import WorkspaceComparePage from "@/app/workspaces/[workspaceId]/compare/page";
import * as comparisonsApi from "@/lib/api/comparisons";
import * as documentsApi from "@/lib/api/documents";
import type {
  ComparisonResponse,
  SavedComparisonResponse,
  DocumentResponse,
  ComparisonFindingResponse,
} from "@/lib/api/types";

vi.mock("@/lib/api/comparisons", () => ({
  executeComparison: vi.fn(),
  listComparisons: vi.fn(),
  getComparison: vi.fn(),
}));

vi.mock("@/lib/api/documents", () => ({
  listDocuments: vi.fn(),
}));

const mockDocs: DocumentResponse[] = [
  {
    id: "doc-1",
    workspace_id: "ws-test",
    filename: "contract_alpha.pdf",
    content_hash: "hash-1",
    file_size_bytes: 12000,
    page_count: 5,
    status: "ready",
    error_message: null,
    processing_attempts: 1,
    processing_started_at: new Date().toISOString(),
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: "doc-2",
    workspace_id: "ws-test",
    filename: "contract_beta.pdf",
    content_hash: "hash-2",
    file_size_bytes: 15000,
    page_count: 8,
    status: "ready",
    error_message: null,
    processing_attempts: 1,
    processing_started_at: new Date().toISOString(),
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: "doc-3",
    workspace_id: "ws-test",
    filename: "contract_gamma.pdf",
    content_hash: "hash-3",
    file_size_bytes: 8000,
    page_count: 3,
    status: "processing", // not ready
    error_message: null,
    processing_attempts: 1,
    processing_started_at: new Date().toISOString(),
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
];

const mockFindingAgreement: ComparisonFindingResponse = {
  finding_type: "agreement",
  topic: "Governing Law",
  summary: "Both contracts agree that Delaware law governs the agreement.",
  per_document_evidence: [
    {
      document_id: "doc-1",
      document_filename: "contract_alpha.pdf",
      statement: "Governed by Delaware state law.",
      citations: [
        {
          id: "cite-1",
          chunk_id: "chunk-1",
          document_id: "doc-1",
          document_filename: "contract_alpha.pdf",
          page_number: 10,
          quoted_snippet: "This Agreement shall be governed by Delaware law.",
        },
      ],
    },
    {
      document_id: "doc-2",
      document_filename: "contract_beta.pdf",
      statement: "Governed by Delaware courts.",
      citations: [
        {
          id: "cite-2",
          chunk_id: "chunk-2",
          document_id: "doc-2",
          document_filename: "contract_beta.pdf",
          page_number: 14,
          quoted_snippet: "Governed in all respects by the laws of Delaware.",
        },
      ],
    },
  ],
  citations: [],
};

const mockFindingContradiction: ComparisonFindingResponse = {
  finding_type: "contradiction",
  topic: "Termination Notice",
  summary: "Alpha requires 30 days notice while Beta requires 90 days notice.",
  per_document_evidence: [
    {
      document_id: "doc-1",
      document_filename: "contract_alpha.pdf",
      statement: "Requires 30 days prior written notice.",
      citations: [],
    },
    {
      document_id: "doc-2",
      document_filename: "contract_beta.pdf",
      statement: "Requires 90 days prior written notice.",
      citations: [],
    },
  ],
  citations: [],
};

const mockComparison: ComparisonResponse = {
  comparison_id: "comp-123",
  workspace_id: "ws-test",
  query_text: "Compare governing law and termination notice",
  document_ids: ["doc-1", "doc-2"],
  status: "completed",
  is_abstention: false,
  findings: [mockFindingAgreement, mockFindingContradiction],
  synthesis: "Alpha and Beta share Delaware governing law but diverge substantially on notice duration.",
  limitations: "Indemnity carveouts were omitted from this analysis.",
  retrieved_evidence: [
    {
      chunk_id: "chunk-1",
      document_id: "doc-1",
      document_filename: "contract_alpha.pdf",
      page_number: 10,
      snippet: "This Agreement shall be governed by Delaware law.",
      similarity_score: 0.92,
      rank: 1,
    },
  ],
  created_at: new Date().toISOString(),
};

const mockSavedComparison: SavedComparisonResponse = {
  comparison_id: "comp-123",
  workspace_id: "ws-test",
  query_text: "Compare governing law and termination notice",
  status: "completed",
  is_abstention: false,
  top_score: null,
  synthesis: "Alpha and Beta share Delaware governing law but diverge substantially on notice duration.",
  citations: [],
  retrieved_evidence: [],
  created_at: new Date().toISOString(),
};

describe("DocumentSelector Component", () => {
  it("renders only ready documents and displays selection count", () => {
    const handleChange = vi.fn();
    render(
      <DocumentSelector
        documents={mockDocs}
        selectedIds={["doc-1"]}
        onChange={handleChange}
      />
    );

    expect(screen.getByText("contract_alpha.pdf")).toBeInTheDocument();
    expect(screen.getByText("contract_beta.pdf")).toBeInTheDocument();
    expect(screen.queryByText("contract_gamma.pdf")).not.toBeInTheDocument(); // processing, should not appear
    expect(screen.getByText(/1 \/ 5 Selected \(Need 2–5\)/i)).toBeInTheDocument();
  });

  it("calls onChange when toggling document selection", () => {
    const handleChange = vi.fn();
    render(
      <DocumentSelector
        documents={mockDocs}
        selectedIds={["doc-1"]}
        onChange={handleChange}
      />
    );

    const betaCheckbox = screen.getByLabelText(/Select contract_beta.pdf/i);
    fireEvent.click(betaCheckbox);

    expect(handleChange).toHaveBeenCalledWith(["doc-1", "doc-2"]);
  });

  it("prevents selecting more than 5 documents", () => {
    const handleChange = vi.fn();
    const fiveDocs: DocumentResponse[] = Array.from({ length: 6 }).map((_, i) => ({
      id: `doc-${i}`,
      workspace_id: "ws-test",
      filename: `doc_${i}.pdf`,
      content_hash: `hash-${i}`,
      file_size_bytes: 1000,
      page_count: 2,
      status: "ready",
      error_message: null,
      processing_attempts: 1,
      processing_started_at: new Date().toISOString(),
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }));

    render(
      <DocumentSelector
        documents={fiveDocs}
        selectedIds={["doc-0", "doc-1", "doc-2", "doc-3", "doc-4"]}
        onChange={handleChange}
      />
    );

    expect(screen.getByText(/5 \/ 5 Selected \(Valid\)/i)).toBeInTheDocument();
    const unselectedCheckbox = screen.getByLabelText(/Select doc_5.pdf/i);
    expect(unselectedCheckbox).toBeDisabled();
  });
});

describe("FindingCard Component", () => {
  it("renders agreement finding with correct badge and per-document statements", () => {
    render(
      <FindingCard
        finding={mockFindingAgreement}
        workspaceId="ws-test"
      />
    );

    expect(screen.getByText("Governing Law")).toBeInTheDocument();
    expect(screen.getByText("Agreement")).toBeInTheDocument();
    expect(
      screen.getByText("Both contracts agree that Delaware law governs the agreement.")
    ).toBeInTheDocument();
    expect(screen.getAllByText("contract_alpha.pdf").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Governed by Delaware state law.")).toBeInTheDocument();
  });

  it("renders contradiction finding with contradiction badge", () => {
    render(
      <FindingCard
        finding={mockFindingContradiction}
        workspaceId="ws-test"
      />
    );

    expect(screen.getByText("Termination Notice")).toBeInTheDocument();
    expect(screen.getByText("Contradiction")).toBeInTheDocument();
  });
});

describe("ComparisonMatrix Component", () => {
  it("renders synthesis, limitations, and filter controls", () => {
    render(
      <ComparisonMatrix
        comparison={mockComparison}
        workspaceId="ws-test"
      />
    );

    expect(
      screen.getByText(/Compare governing law and termination notice/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Alpha and Beta share Delaware governing law/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Indemnity carveouts were omitted from this analysis./i)
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /All \(2\)/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Agreement \(1\)/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Contradiction \(1\)/i })).toBeInTheDocument();
  });

  it("filters findings when clicking category filter pills", () => {
    render(
      <ComparisonMatrix
        comparison={mockComparison}
        workspaceId="ws-test"
      />
    );

    expect(screen.getByText("Governing Law")).toBeInTheDocument();
    expect(screen.getByText("Termination Notice")).toBeInTheDocument();

    const contradictionBtn = screen.getByRole("button", { name: /Contradiction \(1\)/i });
    fireEvent.click(contradictionBtn);

    expect(screen.queryByText("Governing Law")).not.toBeInTheDocument();
    expect(screen.getByText("Termination Notice")).toBeInTheDocument();
  });
});

describe("WorkspaceComparePage Integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(documentsApi.listDocuments).mockResolvedValue(mockDocs);
    vi.mocked(comparisonsApi.listComparisons).mockResolvedValue([mockSavedComparison]);
    vi.mocked(comparisonsApi.getComparison).mockResolvedValue(mockSavedComparison);
  });

  it("loads documents and historical comparison", async () => {
    render(
      <WorkspaceComparePage
        params={{ workspaceId: "ws-test" } as unknown as Promise<{ workspaceId: string }>}
      />
    );

    expect(
      await screen.findByRole("heading", { name: /Cross-Document Comparison/i })
    ).toBeInTheDocument();
    expect(
      await screen.findByText(/Alpha and Beta share Delaware governing law/i)
    ).toBeInTheDocument();
  });

  it("executes comparison and renders new matrix", async () => {
    vi.mocked(comparisonsApi.executeComparison).mockResolvedValue(mockComparison);

    render(
      <WorkspaceComparePage
        params={{ workspaceId: "ws-test" } as unknown as Promise<{ workspaceId: string }>}
      />
    );

    const textarea = await screen.findByLabelText(/Comparison topic or question/i);
    fireEvent.change(textarea, {
      target: { value: "Compare liability caps between alpha and beta" },
    });

    const submitBtn = screen.getByRole("button", { name: /Run Comparison/i });
    expect(submitBtn).not.toBeDisabled();

    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(comparisonsApi.executeComparison).toHaveBeenCalledWith("ws-test", {
        query_text: "Compare liability caps between alpha and beta",
        document_ids: ["doc-1", "doc-2"],
      });
    });
  });
});
