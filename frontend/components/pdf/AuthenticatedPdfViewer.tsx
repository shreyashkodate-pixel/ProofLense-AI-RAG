"use client";

import React, { useEffect, useRef, useState, useCallback } from "react";
import { Loader2, AlertCircle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { PageNavigator } from "./PageNavigator";
import { TextHighlightLayer } from "./TextHighlightLayer";
import { getDocumentFile } from "@/lib/api/documents";
import { ProblemDetails } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthContext";
import styles from "./AuthenticatedPdfViewer.module.css";

// Interface for PDF.js document and page types
interface PDFDocumentProxy {
  numPages: number;
  getPage: (pageNumber: number) => Promise<PDFPageProxy>;
  destroy: () => Promise<void>;
}

interface PDFPageProxy {
  getViewport: (options: { scale: number }) => { width: number; height: number };
  render: (params: {
    canvasContext: CanvasRenderingContext2D;
    viewport: { width: number; height: number };
  }) => { promise: Promise<void>; cancel: () => void };
  getTextContent: () => Promise<{ items: Array<{ str?: string }> }>;
}

export interface AuthenticatedPdfViewerProps {
  workspaceId: string;
  documentId: string;
  initialPage?: number;
  targetSnippet?: string | null;
  onPageChanged?: (pageNumber: number) => void;
  onClearSnippet?: () => void;
}

export const AuthenticatedPdfViewer: React.FC<AuthenticatedPdfViewerProps> = ({
  workspaceId,
  documentId,
  initialPage = 1,
  targetSnippet,
  onPageChanged,
  onClearSnippet,
}) => {
  const [currentPage, setCurrentPage] = useState<number>(initialPage);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [scale, setScale] = useState<number>(1.0);
  const [loading, setLoading] = useState<boolean>(true);
  const [pageRendering, setPageRendering] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [pageText, setPageText] = useState<string>("");

  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const pdfDocRef = useRef<PDFDocumentProxy | null>(null);
  const renderTaskRef = useRef<{ cancel: () => void } | null>(null);

  const { openPasskeyModal } = useAuth();

  // Update currentPage if initialPage changes from deep-link or chunk click
  useEffect(() => {
    setCurrentPage(initialPage);
  }, [initialPage]);

  // Load PDF Binary and initialize PDF.js
  const loadPdfDocument = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      // 1. Fetch authenticated PDF binary blob
      const blob = await getDocumentFile(workspaceId, documentId);
      const arrayBuffer = await blob.arrayBuffer();

      // 2. Dynamically import PDF.js client-side
      const pdfjs = await import("pdfjs-dist");
      if (!pdfjs.GlobalWorkerOptions.workerSrc) {
        pdfjs.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.mjs";
      }

      // 3. Destroy previous PDF document if any
      if (pdfDocRef.current) {
        await pdfDocRef.current.destroy();
        pdfDocRef.current = null;
      }

      // 4. Load document from raw bytes
      const loadingTask = pdfjs.getDocument({ data: arrayBuffer });
      const doc = (await loadingTask.promise) as unknown as PDFDocumentProxy;
      pdfDocRef.current = doc;
      setTotalPages(doc.numPages);
      setCurrentPage((prev) => Math.min(prev, doc.numPages));
    } catch (err: unknown) {
      const problem = err as ProblemDetails;
      if (problem.status_code === 401) {
        setError("Access passkey required to view protected PDF document.");
        openPasskeyModal();
      } else {
        setError(problem.message || "Failed to load authenticated PDF document.");
      }
    } finally {
      setLoading(false);
    }
  }, [workspaceId, documentId, openPasskeyModal]);

  useEffect(() => {
    loadPdfDocument();

    return () => {
      if (renderTaskRef.current) {
        renderTaskRef.current.cancel();
      }
      if (pdfDocRef.current) {
        pdfDocRef.current.destroy();
        pdfDocRef.current = null;
      }
    };
  }, [loadPdfDocument]);

  // Render current page onto Canvas
  const renderCurrentPage = useCallback(async () => {
    if (!pdfDocRef.current || !canvasRef.current) return;

    // Cancel in-flight render task if any
    if (renderTaskRef.current) {
      renderTaskRef.current.cancel();
      renderTaskRef.current = null;
    }

    setPageRendering(true);

    try {
      const page = await pdfDocRef.current.getPage(currentPage);
      const canvas = canvasRef.current;
      if (!canvas) return;

      const context = canvas.getContext("2d");
      if (!context) return;

      const viewport = page.getViewport({ scale });
      canvas.width = viewport.width;
      canvas.height = viewport.height;

      const renderContext = {
        canvasContext: context,
        viewport,
      };

      const renderTask = page.render(renderContext);
      renderTaskRef.current = renderTask;

      await renderTask.promise;
      renderTaskRef.current = null;

      // Extract text content from this page for honest citation snippet matching
      const textContent = await page.getTextContent();
      const extractedStr = textContent.items
        .map((item) => item.str || "")
        .join(" ");
      setPageText(extractedStr);
    } catch (err: unknown) {
      // Ignore rendering cancelation exceptions; report other rendering failures cleanly
      if ((err as { name?: string })?.name !== "RenderingCancelledException") {
        setError("Page rendering encountered an issue. Try adjusting zoom or reloading.");
      }
    } finally {
      setPageRendering(false);
    }
  }, [currentPage, scale]);

  useEffect(() => {
    if (!loading && pdfDocRef.current) {
      renderCurrentPage();
    }
  }, [loading, currentPage, scale, renderCurrentPage]);

  const handlePageChange = (newPage: number) => {
    setCurrentPage(newPage);
    if (onPageChanged) {
      onPageChanged(newPage);
    }
  };

  return (
    <div className={styles.viewerContainer}>
      {/* Top Controls Bar */}
      <div className={styles.topBar}>
        <PageNavigator
          currentPage={currentPage}
          totalPages={totalPages}
          scale={scale}
          onPageChange={handlePageChange}
          onScaleChange={setScale}
          disabled={loading || Boolean(error)}
        />

        {/* Evidence Highlight & Inspection Banner */}
        <TextHighlightLayer
          pageNumber={currentPage}
          pageText={pageText}
          targetSnippet={targetSnippet}
          onClearSnippet={onClearSnippet}
        />
      </div>

      {/* Main PDF Scrollable Viewing Canvas */}
      <div className={styles.canvasScrollArea}>
        {loading && (
          <div className={styles.loadingOverlay}>
            <Loader2 size={36} style={{ animation: "spin 1s linear infinite", color: "var(--color-accent)" }} />
            <span>Retrieving authenticated PDF bytes...</span>
          </div>
        )}

        {error && !loading && (
          <div className={styles.errorOverlay} role="alert">
            <AlertCircle size={36} />
            <div style={{ fontWeight: 600, fontSize: "var(--font-size-md)" }}>
              Unable to Display PDF
            </div>
            <p style={{ fontSize: "var(--font-size-xs)" }}>{error}</p>
            <Button
              variant="secondary"
              size="sm"
              onClick={loadPdfDocument}
              leftIcon={<RefreshCw size={14} />}
            >
              Retry Loading PDF
            </Button>
          </div>
        )}

        {!loading && !error && (
          <div className={styles.canvasWrapper}>
            <canvas ref={canvasRef} className={styles.pdfCanvas} />
            {pageRendering && (
              <div
                style={{
                  position: "absolute",
                  top: "var(--space-2)",
                  right: "var(--space-2)",
                  backgroundColor: "rgba(0, 0, 0, 0.6)",
                  color: "#ffffff",
                  fontSize: "11px",
                  padding: "var(--space-1) var(--space-2)",
                  borderRadius: "var(--radius-sm)",
                  display: "flex",
                  alignItems: "center",
                  gap: "var(--space-1)",
                }}
              >
                <Loader2 size={12} style={{ animation: "spin 1s linear infinite" }} />
                <span>Rendering...</span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
