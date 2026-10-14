"use client";

import React from "react";
import type { ComparisonFindingResponse, ComparisonFindingType } from "@/lib/api/types";
import { CitationCard } from "@/components/queries/CitationCard";
import styles from "./FindingCard.module.css";

interface FindingCardProps {
  finding: ComparisonFindingResponse;
  workspaceId: string;
}

const BADGE_MAP: Record<
  ComparisonFindingType,
  { label: string; className: string }
> = {
  agreement: {
    label: "Agreement",
    className: styles.badgeAgreement,
  },
  contradiction: {
    label: "Contradiction",
    className: styles.badgeContradiction,
  },
  difference: {
    label: "Difference",
    className: styles.badgeDifference,
  },
  not_found: {
    label: "Not Found",
    className: styles.badgeNotFound,
  },
  insufficient_evidence: {
    label: "Insufficient Evidence",
    className: styles.badgeInsufficientEvidence,
  },
};

export function FindingCard({ finding, workspaceId }: FindingCardProps) {
  const badgeInfo = BADGE_MAP[finding.finding_type] || {
    label: finding.finding_type,
    className: styles.badgeNotFound,
  };

  return (
    <article className={styles.card} aria-labelledby={`finding-${finding.topic.replace(/\s+/g, "-")}`}>
      <div className={styles.header}>
        <h4 id={`finding-${finding.topic.replace(/\s+/g, "-")}`} className={styles.topicTitle}>
          {finding.topic}
        </h4>
        <span className={`${styles.badge} ${badgeInfo.className}`} role="status">
          {badgeInfo.label}
        </span>
      </div>

      <p className={styles.summary}>{finding.summary}</p>

      {finding.per_document_evidence && finding.per_document_evidence.length > 0 && (
        <div className={styles.evidenceGrid} aria-label="Per-Document Evidence">
          {finding.per_document_evidence.map((docEvidence, idx) => (
            <div key={`${docEvidence.document_id}-${idx}`} className={styles.docEvidenceBlock}>
              <div className={styles.docEvidenceHeader}>
                <span className={styles.docEvidenceFilename}>
                  {docEvidence.document_filename}
                </span>
              </div>
              <p className={styles.docStatement}>{docEvidence.statement}</p>

              {docEvidence.citations && docEvidence.citations.length > 0 && (
                <div className={styles.citationsList}>
                  {docEvidence.citations.map((cite) => (
                    <CitationCard
                      key={cite.id}
                      citation={cite}
                      workspaceId={workspaceId}
                      compact
                    />
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </article>
  );
}
