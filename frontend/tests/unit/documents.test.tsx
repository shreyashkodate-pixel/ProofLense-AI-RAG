import React from "react";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  validateFilesForUpload,
  MAX_UPLOAD_FILE_SIZE_BYTES,
} from "@/lib/api/documents";
import * as documentsApi from "@/lib/api/documents";
import { UploadDropzone } from "@/components/documents/UploadDropzone";
import { DocumentTable } from "@/components/documents/DocumentTable";
import { useIngestionPolling } from "@/lib/hooks/useIngestionPolling";
import { DocumentResponse } from "@/lib/api/types";
import { renderHook } from "@testing-library/react";

vi.mock("@/lib/api/documents", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/documents")>("@/lib/api/documents");
  return {
    ...actual,
    listDocuments: vi.fn(),
    uploadDocuments: vi.fn(),
    deleteDocument: vi.fn(),
    retryDocument: vi.fn(),
  };
});

describe("Document Upload Validation Logic", () => {
  it("rejects empty file array", () => {
    const result = validateFilesForUpload([]);
    expect(result.valid).toBe(false);
    expect(result.error).toMatch(/select at least one PDF/i);
  });

  it("rejects more than MAX_UPLOAD_FILES_PER_BATCH (5 files)", () => {
    const files = Array.from({ length: 6 }).map(
      (_, i) => new File(["dummy"], `test${i}.pdf`, { type: "application/pdf" })
    );
    const result = validateFilesForUpload(files);
    expect(result.valid).toBe(false);
    expect(result.error).toMatch(/Maximum 5 files allowed/i);
  });

  it("rejects files exceeding 10 MB limit", () => {
    const bigFile = new File(["x".repeat(100)], "oversized.pdf", { type: "application/pdf" });
    Object.defineProperty(bigFile, "size", { value: MAX_UPLOAD_FILE_SIZE_BYTES + 1024 });

    const result = validateFilesForUpload([bigFile]);
    expect(result.valid).toBe(false);
    expect(result.error).toMatch(/exceeds the 10 MB size limit/i);
  });

  it("rejects non-PDF files", () => {
    const textFile = new File(["hello world"], "notes.txt", { type: "text/plain" });
    const result = validateFilesForUpload([textFile]);
    expect(result.valid).toBe(false);
    expect(result.error).toMatch(/Only PDF files are supported/i);
  });

  it("accepts valid PDF within constraints", () => {
    const validPdf = new File(["%PDF-1.4 sample content"], "sample.pdf", {
      type: "application/pdf",
    });
    const result = validateFilesForUpload([validPdf]);
    expect(result.valid).toBe(true);
  });
});

describe("UploadDropzone Component", () => {
  const mockWorkspaceId = "ws-test-123";

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders upload dropzone instructions", () => {
    render(<UploadDropzone workspaceId={mockWorkspaceId} onUploadSuccess={vi.fn()} />);
    expect(screen.getByText(/Click or drag PDF documents here to upload/i)).toBeInTheDocument();
    expect(screen.getByText(/Up to 5 PDFs per batch/i)).toBeInTheDocument();
  });

  it("submits valid files and calls onUploadSuccess", async () => {
    const onUploadSuccess = vi.fn();
    const mockBatch = {
      uploaded: [
        {
          id: "doc-1",
          workspace_id: mockWorkspaceId,
          filename: "report.pdf",
          content_hash: "hash123",
          file_size_bytes: 2048,
          page_count: null,
          status: "pending" as const,
          error_message: null,
          processing_attempts: 0,
          processing_started_at: null,
          created_at: "2026-03-01T12:00:00Z",
          updated_at: "2026-03-01T12:00:00Z",
        },
      ],
      total_uploaded: 1,
    };
    vi.mocked(documentsApi.uploadDocuments).mockResolvedValue(mockBatch);

    render(<UploadDropzone workspaceId={mockWorkspaceId} onUploadSuccess={onUploadSuccess} />);

    const input = screen.getByLabelText(/upload pdf documents/i).querySelector("input")!;
    const file = new File(["%PDF-content"], "report.pdf", { type: "application/pdf" });

    fireEvent.change(input, { target: { files: [file] } });

    expect(await screen.findByText("report.pdf")).toBeInTheDocument();

    const uploadBtn = screen.getByRole("button", { name: /upload 1 file/i });
    fireEvent.click(uploadBtn);

    await waitFor(() => {
      expect(documentsApi.uploadDocuments).toHaveBeenCalledWith(mockWorkspaceId, [file]);
      expect(onUploadSuccess).toHaveBeenCalledWith(mockBatch);
    });
  });
});

describe("DocumentTable Component", () => {
  const mockDocs: DocumentResponse[] = [
    {
      id: "doc-1",
      workspace_id: "ws-1",
      filename: "financial_report.pdf",
      content_hash: "hash1",
      file_size_bytes: 1024 * 500, // 500 KB
      page_count: 12,
      status: "ready",
      error_message: null,
      processing_attempts: 1,
      processing_started_at: "2026-03-01T12:00:00Z",
      created_at: "2026-03-01T12:00:00Z",
      updated_at: "2026-03-01T12:01:00Z",
    },
    {
      id: "doc-2",
      workspace_id: "ws-1",
      filename: "corrupt_scan.pdf",
      content_hash: "hash2",
      file_size_bytes: 1024 * 100,
      page_count: null,
      status: "failed",
      error_message: "Invalid PDF structure",
      processing_attempts: 1,
      processing_started_at: "2026-03-01T12:02:00Z",
      created_at: "2026-03-01T12:02:00Z",
      updated_at: "2026-03-01T12:03:00Z",
    },
  ];

  it("renders documents with appropriate status badges", () => {
    render(<DocumentTable workspaceId="ws-1" documents={mockDocs} />);

    expect(screen.getByText("financial_report.pdf")).toBeInTheDocument();
    expect(screen.getByText("500.0 KB")).toBeInTheDocument();
    expect(screen.getByText("12 pgs")).toBeInTheDocument();
    expect(screen.getByText("Ready")).toBeInTheDocument();

    expect(screen.getByText("corrupt_scan.pdf")).toBeInTheDocument();
    expect(screen.getByText("Failed")).toBeInTheDocument();
  });

  it("triggers retry callback when retry button clicked for failed doc", async () => {
    const onRetry = vi.fn().mockResolvedValue(undefined);
    render(<DocumentTable workspaceId="ws-1" documents={mockDocs} onRetry={onRetry} />);

    const retryBtn = screen.getByRole("button", { name: /retry/i });
    fireEvent.click(retryBtn);

    await waitFor(() => {
      expect(onRetry).toHaveBeenCalledWith(mockDocs[1]);
    });
  });

  it("handles document deletion confirmation dialog", async () => {
    const onDelete = vi.fn().mockResolvedValue(undefined);
    render(<DocumentTable workspaceId="ws-1" documents={mockDocs} onDelete={onDelete} />);

    const deleteButtons = screen.getAllByTitle("Delete document");
    fireEvent.click(deleteButtons[0]);

    expect(screen.getByText(/Are you sure you want to delete/i)).toBeInTheDocument();
    expect(screen.getByText(/persistent snapshot quotes/i)).toBeInTheDocument();

    const confirmBtn = screen.getByRole("button", { name: /delete permanently/i });
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(onDelete).toHaveBeenCalledWith(mockDocs[0]);
    });
  });
});

describe("useIngestionPolling Hook", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  it("polls periodically while documents are pending/processing, and stops when ready", async () => {
    const pendingDoc: DocumentResponse = {
      id: "doc-poll",
      workspace_id: "ws-poll",
      filename: "processing.pdf",
      content_hash: "hash-poll",
      file_size_bytes: 5000,
      page_count: null,
      status: "processing",
      error_message: null,
      processing_attempts: 1,
      processing_started_at: "2026-03-01T12:00:00Z",
      created_at: "2026-03-01T12:00:00Z",
      updated_at: "2026-03-01T12:00:00Z",
    };

    const readyDoc: DocumentResponse = {
      ...pendingDoc,
      status: "ready",
      page_count: 5,
    };

    // First call returns processing doc
    vi.mocked(documentsApi.listDocuments).mockResolvedValueOnce([pendingDoc]);

    const { result } = renderHook(() => useIngestionPolling("ws-poll"));

    // Flush initial fetch
    await act(async () => {
      await Promise.resolve();
    });

    expect(result.current.documents[0].status).toBe("processing");
    expect(result.current.isPolling).toBe(true);

    // Second call (after timer) returns ready doc
    vi.mocked(documentsApi.listDocuments).mockResolvedValueOnce([readyDoc]);

    await act(async () => {
      vi.advanceTimersByTime(2000);
      await Promise.resolve();
    });

    expect(result.current.documents[0].status).toBe("ready");
    expect(result.current.isPolling).toBe(false);
  });
});
