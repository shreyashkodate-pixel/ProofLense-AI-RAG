"use client";

import React, { useState } from "react";
import Link from "next/link";
import { FileText, RotateCcw, Trash2, Eye, FolderOpen } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Skeleton } from "@/components/ui/Skeleton";
import { DocumentStatusBadge } from "./DocumentStatusBadge";
import { DocumentResponse } from "@/lib/api/types";
import styles from "./DocumentTable.module.css";

export interface DocumentTableProps {
  workspaceId: string;
  documents: DocumentResponse[];
  loading?: boolean;
  onRetry?: (doc: DocumentResponse) => Promise<void>;
  onDelete?: (doc: DocumentResponse) => Promise<void>;
}

export const DocumentTable: React.FC<DocumentTableProps> = ({
  workspaceId,
  documents,
  loading = false,
  onRetry,
  onDelete,
}) => {
  const [deletingDoc, setDeletingDoc] = useState<DocumentResponse | null>(null);
  const [retryingDocId, setRetryingDocId] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const handleRetry = async (doc: DocumentResponse) => {
    if (!onRetry) return;
    setRetryingDocId(doc.id);
    try {
      await onRetry(doc);
    } finally {
      setRetryingDocId(null);
    }
  };

  const handleDeleteConfirm = async () => {
    if (!deletingDoc || !onDelete) return;
    setIsDeleting(true);
    try {
      await onDelete(deletingDoc);
      setDeletingDoc(null);
    } finally {
      setIsDeleting(false);
    }
  };

  if (loading) {
    return (
      <div className={styles.tableWrapper}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Document Name</th>
              <th>Size</th>
              <th>Pages</th>
              <th>Status</th>
              <th>Uploaded</th>
              <th style={{ textAlign: "right" }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {[1, 2, 3].map((n) => (
              <tr key={n}>
                <td><Skeleton width="180px" height="20px" /></td>
                <td><Skeleton width="60px" height="20px" /></td>
                <td><Skeleton width="40px" height="20px" /></td>
                <td><Skeleton width="80px" height="20px" /></td>
                <td><Skeleton width="90px" height="20px" /></td>
                <td><Skeleton width="80px" height="20px" /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  if (documents.length === 0) {
    return (
      <div className={styles.tableWrapper}>
        <div className={styles.emptyState}>
          <FolderOpen size={40} style={{ color: "var(--color-text-tertiary)" }} />
          <div style={{ fontWeight: 600, fontSize: "var(--font-size-md)", color: "var(--color-text-primary)" }}>
            No documents in this workspace
          </div>
          <p style={{ fontSize: "var(--font-size-xs)", maxWidth: "360px" }}>
            Upload PDF files using the box above to trigger ingestion and semantic chunking.
          </p>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className={styles.tableWrapper}>
        <table className={styles.table} aria-label="Document library">
          <thead>
            <tr>
              <th>Document Name</th>
              <th>Size</th>
              <th>Pages</th>
              <th>Status</th>
              <th>Uploaded</th>
              <th style={{ textAlign: "right" }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {documents.map((doc) => {
              const isRetrying = retryingDocId === doc.id;
              return (
                <tr key={doc.id}>
                  <td>
                    <div className={styles.docNameCol}>
                      <FileText size={18} style={{ color: "var(--color-accent)", flexShrink: 0 }} />
                      <span className={styles.docName} title={doc.filename}>
                        {doc.filename}
                      </span>
                    </div>
                  </td>
                  <td style={{ color: "var(--color-text-secondary)", whiteSpace: "nowrap" }}>
                    {formatFileSize(doc.file_size_bytes)}
                  </td>
                  <td style={{ color: "var(--color-text-secondary)" }}>
                    {doc.page_count !== null ? `${doc.page_count} pgs` : "Calculating..."}
                  </td>
                  <td>
                    <DocumentStatusBadge status={doc.status} errorMessage={doc.error_message} />
                  </td>
                  <td style={{ color: "var(--color-text-tertiary)", whiteSpace: "nowrap", fontSize: "var(--font-size-xs)" }}>
                    {new Date(doc.created_at).toLocaleDateString()}
                  </td>
                  <td>
                    <div className={styles.actionsCol}>
                      {doc.status === "failed" && onRetry && (
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => handleRetry(doc)}
                          isLoading={isRetrying}
                          leftIcon={<RotateCcw size={13} />}
                          title="Retry ingestion"
                        >
                          Retry
                        </Button>
                      )}

                      <Link href={`/workspaces/${workspaceId}/documents/${doc.id}`}>
                        <Button
                          variant="ghost"
                          size="sm"
                          leftIcon={<Eye size={14} />}
                          title="Inspect document & PDF"
                        >
                          Inspect
                        </Button>
                      </Link>

                      {onDelete && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setDeletingDoc(doc)}
                          title="Delete document"
                          style={{ color: "var(--color-status-danger-text)" }}
                        >
                          <Trash2 size={14} />
                        </Button>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Delete Document Confirmation Modal */}
      <Modal
        isOpen={Boolean(deletingDoc)}
        onClose={() => !isDeleting && setDeletingDoc(null)}
        title="Delete Document"
      >
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
          <p style={{ color: "var(--color-text-secondary)", fontSize: "var(--font-size-sm)" }}>
            Are you sure you want to delete <strong>{deletingDoc?.filename}</strong>?
            This will purge the stored PDF and cascade-delete all extracted pages, chunks, and embeddings.
            Existing citations will retain persistent snapshot quotes via the tombstone pattern.
          </p>
          <div style={{ display: "flex", justifyContent: "flex-end", gap: "var(--space-2)" }}>
            <Button
              type="button"
              variant="secondary"
              onClick={() => setDeletingDoc(null)}
              disabled={isDeleting}
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant="destructive"
              onClick={handleDeleteConfirm}
              isLoading={isDeleting}
            >
              Delete Permanently
            </Button>
          </div>
        </div>
      </Modal>
    </>
  );
};
