"use client";

import React, { use } from "react";
import { Files, RefreshCw, Loader2, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import { UploadDropzone } from "@/components/documents/UploadDropzone";
import { DocumentTable } from "@/components/documents/DocumentTable";
import { useIngestionPolling } from "@/lib/hooks/useIngestionPolling";
import { retryDocument, deleteDocument } from "@/lib/api/documents";
import { DocumentResponse, ProblemDetails, UploadBatchResponse } from "@/lib/api/types";

export default function WorkspaceDocumentsPage({
  params,
}: {
  params: Promise<{ workspaceId: string }>;
}) {
  const { workspaceId } = use(params);
  const {
    documents,
    setDocuments,
    isPolling,
    loading,
    error,
    refreshDocuments,
  } = useIngestionPolling(workspaceId);

  const { addToast } = useToast();

  const handleUploadSuccess = (batch: UploadBatchResponse) => {
    setDocuments((prev) => [...batch.uploaded, ...prev]);
    addToast({
      title: "Upload submitted",
      message: `${batch.total_uploaded} document(s) queued for ingestion.`,
      type: "success",
    });
  };

  const handleRetry = async (doc: DocumentResponse) => {
    try {
      const updated = await retryDocument(workspaceId, doc.id);
      setDocuments((prev) => prev.map((d) => (d.id === doc.id ? updated : d)));
      addToast({
        title: "Retry scheduled",
        message: `Ingestion retry queued for "${doc.filename}".`,
        type: "info",
      });
    } catch (err: unknown) {
      const problem = err as ProblemDetails;
      addToast({
        title: "Retry failed",
        message: problem.message || "Failed to schedule retry.",
        type: "error",
      });
    }
  };

  const handleDelete = async (doc: DocumentResponse) => {
    try {
      await deleteDocument(workspaceId, doc.id);
      setDocuments((prev) => prev.filter((d) => d.id !== doc.id));
      addToast({
        title: "Document deleted",
        message: `"${doc.filename}" was permanently deleted.`,
        type: "info",
      });
    } catch (err: unknown) {
      const problem = err as ProblemDetails;
      addToast({
        title: "Deletion failed",
        message: problem.message || "Failed to delete document.",
        type: "error",
      });
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-6)" }}>
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          flexWrap: "wrap",
          gap: "var(--space-4)",
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
            <Files size={24} style={{ color: "var(--color-accent)" }} />
            <h1 style={{ fontSize: "var(--font-size-3xl)", fontWeight: 700, color: "var(--color-text-primary)" }}>
              Document Library
            </h1>
          </div>
          <p style={{ fontSize: "var(--font-size-md)", color: "var(--color-text-secondary)", marginTop: "var(--space-1)" }}>
            Upload, inspect, and manage PDF documents for grounded evidence retrieval.
          </p>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
          {isPolling && (
            <div
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "var(--space-2)",
                fontSize: "var(--font-size-xs)",
                color: "var(--color-status-warning-text)",
                backgroundColor: "var(--color-status-warning-bg)",
                padding: "var(--space-1) var(--space-3)",
                borderRadius: "var(--radius-full)",
                border: "var(--border-width-thin) solid var(--color-status-warning-border)",
              }}
            >
              <Loader2 size={13} style={{ animation: "spin 1s linear infinite" }} />
              <span>Ingestion active (polling 2s)</span>
            </div>
          )}
          <Button
            variant="secondary"
            size="sm"
            onClick={refreshDocuments}
            leftIcon={<RefreshCw size={14} />}
          >
            Refresh
          </Button>
        </div>
      </div>

      {/* Error banner */}
      {error && (
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
          <span>{error}</span>
        </div>
      )}

      {/* Upload Zone */}
      <UploadDropzone
        workspaceId={workspaceId}
        onUploadSuccess={handleUploadSuccess}
      />

      {/* Document Table */}
      <DocumentTable
        workspaceId={workspaceId}
        documents={documents}
        loading={loading}
        onRetry={handleRetry}
        onDelete={handleDelete}
      />
    </div>
  );
}
