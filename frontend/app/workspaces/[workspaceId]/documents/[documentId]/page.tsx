"use client";

import React, { use, useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { ArrowLeft, FileText, PanelRightClose, PanelRightOpen, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { DocumentStatusBadge } from "@/components/documents/DocumentStatusBadge";
import { AuthenticatedPdfViewer } from "@/components/pdf/AuthenticatedPdfViewer";
import { ExtractedChunksDrawer } from "@/components/pdf/ExtractedChunksDrawer";
import { getDocument, getDocumentPages } from "@/lib/api/documents";
import {
  DocumentChunkDetailResponse,
  DocumentPageDetailResponse,
  DocumentResponse,
  ProblemDetails,
} from "@/lib/api/types";

export default function DocumentInspectionPage({
  params,
}: {
  params: Promise<{ workspaceId: string; documentId: string }>;
}) {
  const { workspaceId, documentId } = use(params);
  const searchParams = useSearchParams();

  const urlPage = searchParams.get("page");
  const initialPage = urlPage ? parseInt(urlPage, 10) : 1;
  const initialSnippet = searchParams.get("snippet") || null;

  const [document, setDocument] = useState<DocumentResponse | null>(null);
  const [pages, setPages] = useState<DocumentPageDetailResponse[]>([]);
  const [loadingDoc, setLoadingDoc] = useState(true);
  const [loadingPages, setLoadingPages] = useState(true);
  const [docError, setDocError] = useState<string | null>(null);

  const [activePage, setActivePage] = useState<number>(initialPage);
  const [activeSnippet, setActiveSnippet] = useState<string | null>(initialSnippet);
  const [selectedChunkId, setSelectedChunkId] = useState<string | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(true);

  // Load Document Metadata
  const loadDocMetadata = useCallback(async () => {
    setLoadingDoc(true);
    setDocError(null);
    try {
      const doc = await getDocument(workspaceId, documentId);
      setDocument(doc);
    } catch (err: unknown) {
      const problem = err as ProblemDetails;
      setDocError(problem.message || "Failed to load document details.");
    } finally {
      setLoadingDoc(false);
    }
  }, [workspaceId, documentId]);

  // Load Extracted Pages and Chunks
  const loadDocPages = useCallback(async () => {
    setLoadingPages(true);
    try {
      const res = await getDocumentPages(workspaceId, documentId);
      setPages(res.pages);
    } catch {
      // Chunks may not exist yet if still pending/processing
      setPages([]);
    } finally {
      setLoadingPages(false);
    }
  }, [workspaceId, documentId]);

  useEffect(() => {
    loadDocMetadata();
    loadDocPages();
  }, [loadDocMetadata, loadDocPages]);

  const handleChunkSelect = (chunk: DocumentChunkDetailResponse) => {
    setSelectedChunkId(chunk.id);
    if (chunk.page_number) {
      setActivePage(chunk.page_number);
    }
    setActiveSnippet(chunk.chunk_text);

    // Update query params without full reload
    if (typeof window !== "undefined") {
      const url = new URL(window.location.href);
      if (chunk.page_number) url.searchParams.set("page", chunk.page_number.toString());
      window.history.replaceState({}, "", url.toString());
    }
  };

  const handlePageChanged = (pageNumber: number) => {
    setActivePage(pageNumber);
    if (typeof window !== "undefined") {
      const url = new URL(window.location.href);
      url.searchParams.set("page", pageNumber.toString());
      window.history.replaceState({}, "", url.toString());
    }
  };

  const handleClearSnippet = () => {
    setActiveSnippet(null);
    setSelectedChunkId(null);
    if (typeof window !== "undefined") {
      const url = new URL(window.location.href);
      url.searchParams.delete("snippet");
      window.history.replaceState({}, "", url.toString());
    }
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "calc(100vh - 56px - var(--space-12))",
        gap: "var(--space-3)",
      }}
    >
      {/* Top Document Header Bar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "var(--space-2) var(--space-4)",
          backgroundColor: "var(--color-surface)",
          border: "var(--border-width-thin) solid var(--color-border)",
          borderRadius: "var(--radius-md)",
          flexWrap: "wrap",
          gap: "var(--space-3)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
          <Link href={`/workspaces/${workspaceId}/documents`}>
            <Button variant="ghost" size="sm" leftIcon={<ArrowLeft size={16} />}>
              Back to Documents
            </Button>
          </Link>
          <div style={{ height: "20px", width: "1px", backgroundColor: "var(--color-border)" }} />
          <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
            <FileText size={18} style={{ color: "var(--color-accent)" }} />
            <span style={{ fontWeight: 600, fontSize: "var(--font-size-sm)", color: "var(--color-text-primary)" }}>
              {loadingDoc ? "Loading document..." : document ? document.filename : "Document Not Found"}
            </span>
            {document && (
              <DocumentStatusBadge status={document.status} errorMessage={document.error_message} />
            )}
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsDrawerOpen((prev) => !prev)}
            leftIcon={isDrawerOpen ? <PanelRightClose size={16} /> : <PanelRightOpen size={16} />}
            title={isDrawerOpen ? "Collapse evidence drawer" : "Open evidence drawer"}
          >
            {isDrawerOpen ? "Hide Chunks" : "Show Chunks"}
          </Button>
        </div>
      </div>

      {/* Document error banner if any */}
      {docError && (
        <div
          role="alert"
          style={{
            display: "flex",
            alignItems: "center",
            gap: "var(--space-2)",
            padding: "var(--space-3) var(--space-4)",
            backgroundColor: "var(--color-status-danger-bg)",
            border: "var(--border-width-thin) solid var(--color-status-danger-border)",
            borderRadius: "var(--radius-md)",
            color: "var(--color-status-danger-text)",
            fontSize: "var(--font-size-sm)",
          }}
        >
          <AlertCircle size={18} />
          <span>{docError}</span>
        </div>
      )}

      {/* Main Split-Pane Area */}
      <div
        style={{
          display: "flex",
          flex: 1,
          overflow: "hidden",
          borderRadius: "var(--radius-lg)",
          border: "var(--border-width-thin) solid var(--color-border)",
        }}
      >
        {/* Left: Authenticated PDF Viewer */}
        <div style={{ flex: 1, height: "100%", overflow: "hidden" }}>
          <AuthenticatedPdfViewer
            workspaceId={workspaceId}
            documentId={documentId}
            initialPage={activePage}
            targetSnippet={activeSnippet}
            onPageChanged={handlePageChanged}
            onClearSnippet={handleClearSnippet}
          />
        </div>

        {/* Right: Evidence & Extracted Chunks Drawer */}
        {isDrawerOpen && (
          <div style={{ width: "360px", height: "100%", flexShrink: 0 }}>
            <ExtractedChunksDrawer
              pages={pages}
              loading={loadingPages}
              selectedChunkId={selectedChunkId}
              onSelectChunk={handleChunkSelect}
            />
          </div>
        )}
      </div>
    </div>
  );
}
