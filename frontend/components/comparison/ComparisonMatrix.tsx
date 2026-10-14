"use client";

import React, { useState } from "react";
import type {
  ComparisonResponse,
  SavedComparisonResponse,
} from "@/lib/api/types";
import { FindingCard } from "./FindingCard";
import { CitationCard } from "@/components/queries/CitationCard";
import styles from "./ComparisonMatrix.module.css";

interface ComparisonMatrixProps {
  comparison: ComparisonResponse | SavedComparisonResponse;
  workspaceId: string;
}

export function ComparisonMatrix({
  comparison,
  workspaceId,
}: ComparisonMatrixProps) {
  const [selectedFilter, setSelectedFilter] = useState<string>("all");
  const [showEvidence, setShowEvidence] = useState(false);

  const findings = ("findings" in comparison ? comparison.findings : []) || [];
  const limitations = "limitations" in comparison ? comparison.limitations : null;
  const docCount = "document_ids" in comparison ? comparison.document_ids.length : null;
  const directCitations = "citations" in comparison ? comparison.citations : [];

  const counts: Record<string, number> = {
    all: findings.length,
    agreement: 0,
    contradiction: 0,
    difference: 0,
    not_found: 0,
    insufficient_evidence: 0,
  };

  findings.forEach((f) => {
    if (counts[f.finding_type] !== undefined) {
      counts[f.finding_type]++;
    }
  });

  const filteredFindings =
    selectedFilter === "all"
      ? findings
      : findings.filter((f) => f.finding_type === selectedFilter);

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h2 className={styles.queryTitle}>{comparison.query_text}</h2>
        <span className={styles.docCountMeta}>
          {docCount !== null
            ? `Cross-document analysis across ${docCount} documents`
            : "Saved historical comparison"}
        </span>
      </header>

      {comparison.is_abstention ? (
        <div className={styles.abstentionBanner} role="status">
          <div className={styles.abstentionHeader}>
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" />
              <line x1="12" y1="9" x2="12" y2="13" />
              <line x1="12" y1="17" x2="12.01" y2="17" />
            </svg>
            <span>Explicit Abstention — Insufficient Cross-Document Evidence</span>
          </div>
          <p className={styles.abstentionText}>{comparison.synthesis}</p>
        </div>
      ) : (
        <div className={styles.synthesisBox}>
          <h3 className={styles.synthesisTitle}>Executive Synthesis</h3>
          <p className={styles.synthesisText}>{comparison.synthesis}</p>
        </div>
      )}

      {limitations && (
        <aside className={styles.limitationsBanner} aria-label="Analysis Limitations">
          <h4 className={styles.limitationsTitle}>Noted Limitations &amp; Caveats</h4>
          <p className={styles.limitationsText}>{limitations}</p>
        </aside>
      )}

      {findings.length === 0 && directCitations && directCitations.length > 0 && (
        <section aria-label="Comparison Citations">
          <h4 style={{ fontSize: "var(--font-size-xs)", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--color-text-secondary)", margin: "0 0 var(--space-3) 0" }}>
            Citations ({directCitations.length})
          </h4>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "var(--space-3)" }}>
            {directCitations.map((cite) => (
              <CitationCard
                key={cite.id}
                citation={cite}
                workspaceId={workspaceId}
              />
            ))}
          </div>
        </section>
      )}

      {findings.length > 0 && (
        <>
          <nav className={styles.filterBar} aria-label="Filter findings by type">
            <button
              type="button"
              className={`${styles.filterBtn} ${
                selectedFilter === "all" ? styles.filterBtnActive : ""
              }`}
              onClick={() => setSelectedFilter("all")}
            >
              All ({counts.all})
            </button>
            {counts.agreement > 0 && (
              <button
                type="button"
                className={`${styles.filterBtn} ${
                  selectedFilter === "agreement" ? styles.filterBtnActive : ""
                }`}
                onClick={() => setSelectedFilter("agreement")}
              >
                Agreement ({counts.agreement})
              </button>
            )}
            {counts.contradiction > 0 && (
              <button
                type="button"
                className={`${styles.filterBtn} ${
                  selectedFilter === "contradiction" ? styles.filterBtnActive : ""
                }`}
                onClick={() => setSelectedFilter("contradiction")}
              >
                Contradiction ({counts.contradiction})
              </button>
            )}
            {counts.difference > 0 && (
              <button
                type="button"
                className={`${styles.filterBtn} ${
                  selectedFilter === "difference" ? styles.filterBtnActive : ""
                }`}
                onClick={() => setSelectedFilter("difference")}
              >
                Difference ({counts.difference})
              </button>
            )}
            {counts.not_found > 0 && (
              <button
                type="button"
                className={`${styles.filterBtn} ${
                  selectedFilter === "not_found" ? styles.filterBtnActive : ""
                }`}
                onClick={() => setSelectedFilter("not_found")}
              >
                Not Found ({counts.not_found})
              </button>
            )}
            {counts.insufficient_evidence > 0 && (
              <button
                type="button"
                className={`${styles.filterBtn} ${
                  selectedFilter === "insufficient_evidence"
                    ? styles.filterBtnActive
                    : ""
                }`}
                onClick={() => setSelectedFilter("insufficient_evidence")}
              >
                Insufficient Evidence ({counts.insufficient_evidence})
              </button>
            )}
          </nav>

          <section className={styles.findingsList} aria-label="Comparison Findings">
            {filteredFindings.length === 0 ? (
              <div className={styles.emptyFilter}>
                No findings found matching category &ldquo;{selectedFilter}&rdquo;.
              </div>
            ) : (
              filteredFindings.map((finding, idx) => (
                <FindingCard
                  key={`${finding.topic}-${idx}`}
                  finding={finding}
                  workspaceId={workspaceId}
                />
              ))
            )}
          </section>
        </>
      )}

      {comparison.retrieved_evidence && comparison.retrieved_evidence.length > 0 && (
        <section className={styles.evidenceSection} aria-label="Retrieved Evidence Passages">
          <button
            type="button"
            className={styles.evidenceToggle}
            onClick={() => setShowEvidence(!showEvidence)}
            aria-expanded={showEvidence}
          >
            <span>
              Retrieved Evidence Passages ({comparison.retrieved_evidence.length})
            </span>
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              style={{
                transform: showEvidence ? "rotate(180deg)" : "rotate(0deg)",
                transition: "transform 150ms ease",
              }}
              aria-hidden="true"
            >
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </button>

          {showEvidence && (
            <div className={styles.evidenceList}>
              {comparison.retrieved_evidence.map((evidence) => (
                <div key={evidence.chunk_id} className={styles.evidenceItem}>
                  <div className={styles.evidenceMeta}>
                    <span>
                      <strong>{evidence.document_filename}</strong> — Page {evidence.page_number} (Rank #{evidence.rank})
                    </span>
                    <span>Score: {(evidence.similarity_score * 100).toFixed(1)}%</span>
                  </div>
                  <p className={styles.evidenceSnippet}>&ldquo;{evidence.snippet}&rdquo;</p>
                </div>
              ))}
            </div>
          )}
        </section>
      )}
    </div>
  );
}
