"use client";

import React from "react";
import Link from "next/link";
import type { CitationResponse } from "@/lib/api/types";
import styles from "./CitationCard.module.css";

interface CitationCardProps {
  citation: CitationResponse;
  workspaceId: string;
  onInspect?: (citation: CitationResponse) => void;
  compact?: boolean;
}

export function CitationCard({
  citation,
  workspaceId,
  onInspect,
  compact = false,
}: CitationCardProps) {
  const isTombstone = !citation.document_id;
  const targetHref = citation.document_id
    ? `/workspaces/${workspaceId}/documents/${citation.document_id}?page=${citation.page_number}&snippet=${encodeURIComponent(
        citation.quoted_snippet
      )}`
    : undefined;

  const content = (
    <>
      <div className={styles.header}>
        <div className={styles.sourceInfo}>
          <span
            className={styles.docFilename}
            title={citation.document_filename}
          >
            {citation.document_filename || "Document Evidence"}
          </span>
          <span className={styles.pageBadge}>
            Page {citation.page_number}
          </span>
          {isTombstone && (
            <span
              className={styles.tombstoneBadge}
              title="Underlying document was deleted; provenance snapshot preserved"
            >
              Preserved Snapshot
            </span>
          )}
        </div>
      </div>

      {!compact && citation.quoted_snippet && (
        <div className={styles.snippetBox}>
          <p className={styles.snippetText}>
            &ldquo;{citation.quoted_snippet}&rdquo;
          </p>
        </div>
      )}

      {!isTombstone && targetHref && (
        <div className={styles.inspectAction}>
          <span>View in Document</span>
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
            <polyline points="15 3 21 3 21 9" />
            <line x1="10" y1="14" x2="21" y2="3" />
          </svg>
        </div>
      )}
    </>
  );

  if (!isTombstone && targetHref) {
    return (
      <Link
        href={targetHref}
        className={styles.citationCard}
        onClick={() => onInspect?.(citation)}
        aria-label={`Inspect citation on page ${citation.page_number} of ${citation.document_filename}`}
      >
        {content}
      </Link>
    );
  }

  return (
    <div
      className={styles.citationCard}
      aria-label={`Citation on page ${citation.page_number} of ${citation.document_filename} (deleted source)`}
    >
      {content}
    </div>
  );
}
