import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  matchSnippetInPageText,
  TextHighlightLayer,
} from "@/components/pdf/TextHighlightLayer";
import { PageNavigator } from "@/components/pdf/PageNavigator";
import { ExtractedChunksDrawer } from "@/components/pdf/ExtractedChunksDrawer";
import { AuthenticatedPdfViewer } from "@/components/pdf/AuthenticatedPdfViewer";
import * as documentsApi from "@/lib/api/documents";
import { AuthProvider } from "@/lib/auth/AuthContext";
import { ToastProvider } from "@/components/ui/Toast";

vi.mock("@/lib/api/documents", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/documents")>("@/lib/api/documents");
  return {
    ...actual,
    getDocumentFile: vi.fn(),
  };
});

describe("Honest Evidence & Text Layer Matching (Zero Bounding Boxes)", () => {
  const samplePageText = `
    The patient demonstrated marked clinical improvement following the administration
    of the 50mg dosage. No adverse reactions were observed during the 48-hour monitoring period.
    Overall efficacy reached 94.2% across the cohort.
  `;

  it("identifies exact normalized text match", () => {
    const snippet = "No adverse reactions were observed during the 48-hour monitoring period.";
    const result = matchSnippetInPageText(samplePageText, snippet);
    expect(result.matchStatus).toBe("exact");
    expect(result.confidence).toBe(1.0);
  });

  it("identifies approximate match when words match with high ratio", () => {
    const snippet = "No adverse reactions observed in the 48-hour monitoring";
    const result = matchSnippetInPageText(samplePageText, snippet);
    expect(result.matchStatus).toBe("approximate");
    expect(result.confidence).toBeGreaterThanOrEqual(0.7);
  });

  it("identifies unmatched when text is not found on page", () => {
    const snippet = "A completely unrelated statement regarding quantum computing.";
    const result = matchSnippetInPageText(samplePageText, snippet);
    expect(result.matchStatus).toBe("unmatched");
    expect(result.confidence).toBe(0);
  });

  it("returns none for empty or missing snippet", () => {
    expect(matchSnippetInPageText(samplePageText, "")).toEqual({ matchStatus: "none", confidence: 0 });
    expect(matchSnippetInPageText(samplePageText, null)).toEqual({ matchStatus: "none", confidence: 0 });
  });

  it("renders verified exact match banner without claiming bounding box coordinates", () => {
    render(
      <TextHighlightLayer
        pageNumber={3}
        pageText={samplePageText}
        targetSnippet="Overall efficacy reached 94.2%"
      />
    );

    expect(screen.getByText(/Exact Text Match Verified on Page 3/i)).toBeInTheDocument();
    expect(screen.getByText(/Overall efficacy reached 94.2%/i)).toBeInTheDocument();
  });
});

describe("PageNavigator Component", () => {
  it("navigates forward and backward within total page bounds", () => {
    const onPageChange = vi.fn();
    const onScaleChange = vi.fn();

    const { rerender } = render(
      <PageNavigator
        currentPage={1}
        totalPages={5}
        scale={1.0}
        onPageChange={onPageChange}
        onScaleChange={onScaleChange}
      />
    );

    const prevBtn = screen.getByLabelText("Previous page");
    const nextBtn = screen.getByLabelText("Next page");

    expect(prevBtn).toBeDisabled();
    expect(nextBtn).not.toBeDisabled();

    fireEvent.click(nextBtn);
    expect(onPageChange).toHaveBeenCalledWith(2);

    // Rerender at last page
    rerender(
      <PageNavigator
        currentPage={5}
        totalPages={5}
        scale={1.0}
        onPageChange={onPageChange}
        onScaleChange={onScaleChange}
      />
    );

    expect(screen.getByLabelText("Next page")).toBeDisabled();
  });

  it("controls zoom scale accurately", () => {
    const onScaleChange = vi.fn();

    render(
      <PageNavigator
        currentPage={1}
        totalPages={5}
        scale={1.0}
        onPageChange={vi.fn()}
        onScaleChange={onScaleChange}
      />
    );

    fireEvent.click(screen.getByLabelText("Zoom in"));
    expect(onScaleChange).toHaveBeenCalledWith(1.25);

    fireEvent.click(screen.getByLabelText("Zoom out"));
    expect(onScaleChange).toHaveBeenCalledWith(0.75);
  });
});

describe("ExtractedChunksDrawer Component", () => {
  const mockPages = [
    {
      id: "page-1",
      document_id: "doc-1",
      page_number: 1,
      raw_text: "Introduction to corporate governance and compliance.",
      char_count: 52,
      chunks: [
        {
          id: "chunk-1",
          document_id: "doc-1",
          page_id: "page-1",
          chunk_index: 0,
          chunk_text: "Corporate governance standards require quarterly auditing.",
          token_count: 8,
          page_number: 1,
        },
      ],
    },
    {
      id: "page-2",
      document_id: "doc-1",
      page_number: 2,
      raw_text: "Financial disclosures and risk matrices.",
      char_count: 42,
      chunks: [
        {
          id: "chunk-2",
          document_id: "doc-1",
          page_id: "page-2",
          chunk_index: 1,
          chunk_text: "Risk matrices highlight supply chain vulnerability.",
          token_count: 7,
          page_number: 2,
        },
      ],
    },
  ];

  it("renders chunks and responds to chunk selection", () => {
    const onSelectChunk = vi.fn();

    render(
      <ExtractedChunksDrawer
        pages={mockPages}
        selectedChunkId="chunk-1"
        onSelectChunk={onSelectChunk}
      />
    );

    expect(screen.getByText(/Page 1/i)).toBeInTheDocument();
    expect(screen.getByText("Corporate governance standards require quarterly auditing.")).toBeInTheDocument();

    const chunk2 = screen.getByText("Risk matrices highlight supply chain vulnerability.");
    fireEvent.click(chunk2);

    expect(onSelectChunk).toHaveBeenCalledWith(mockPages[1].chunks[0]);
  });

  it("filters chunks via text search input", () => {
    render(
      <ExtractedChunksDrawer
        pages={mockPages}
        onSelectChunk={vi.fn()}
      />
    );

    const searchInput = screen.getByPlaceholderText(/filter chunk text/i);
    fireEvent.change(searchInput, { target: { value: "supply chain" } });

    expect(screen.queryByText(/Corporate governance standards/i)).not.toBeInTheDocument();
    expect(screen.getByText(/Risk matrices highlight supply chain/i)).toBeInTheDocument();
  });
});

describe("AuthenticatedPdfViewer Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("handles 401 unauthenticated response by triggering passkey error", async () => {
    vi.mocked(documentsApi.getDocumentFile).mockRejectedValue({
      error_code: "UNAUTHORIZED",
      message: "Invalid workspace passkey",
      status_code: 401,
    });

    render(
      <AuthProvider>
        <ToastProvider>
          <AuthenticatedPdfViewer
            workspaceId="ws-1"
            documentId="doc-1"
          />
        </ToastProvider>
      </AuthProvider>
    );

    expect(await screen.findByText(/Access passkey required to view protected PDF document/i)).toBeInTheDocument();
  });

  it("handles 404 missing document error", async () => {
    vi.mocked(documentsApi.getDocumentFile).mockRejectedValue({
      error_code: "RESOURCE_NOT_FOUND",
      message: "Physical PDF file was not found in storage.",
      status_code: 404,
    });

    render(
      <AuthProvider>
        <ToastProvider>
          <AuthenticatedPdfViewer
            workspaceId="ws-1"
            documentId="doc-1"
          />
        </ToastProvider>
      </AuthProvider>
    );

    expect(await screen.findByText(/Physical PDF file was not found in storage/i)).toBeInTheDocument();
  });
});
