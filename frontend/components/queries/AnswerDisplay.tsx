"use client";

import React, { useState } from "react";
import type { QueryResponse } from "@/lib/api/types";
import { CitationCard } from "./CitationCard";
import styles from "./AnswerDisplay.module.css";

interface AnswerDisplayProps {
  response: QueryResponse;
  workspaceId: string;
}

export function AnswerDisplay({ response, workspaceId }: AnswerDisplayProps) {
  const [showEvidence, setShowEvidence] = useState(false);

  return (
    <article className={styles.container} aria-labelledby="query-answer-heading">
      <div className={styles.header}>
        <div>
          <h3 id="query-answer-heading" className={styles.queryTitle}>
            {response.query_text}
          </h3>
        </div>
        <div className={styles.queryMeta}>
          {response.top_score !== null && (
            <span
              className={styles.scoreBadge}
              title="Cosine similarity score of highest ranking retrieved passage"
            >
              Similarity: {(response.top_score * 100).toFixed(1)}%
            </span>
          )}
        </div>
      </div>

      {response.is_abstention ? (
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
            <span>Explicit Abstention — Insufficient Grounded Evidence</span>
          </div>
          <p className={styles.abstentionText}>{response.answer_text}</p>
          <p className={styles.abstentionNotice}>
            ProofLens AI enforces an evidence-first principle: if retrieved passages are inadequate or absent, the system explicitly abstains rather than speculating or hallucinating.
          </p>
        </div>
      ) : (
        <div className={styles.answerBody}>
          <p className={styles.answerText}>{response.answer_text}</p>
        </div>
      )}

      {response.citations && response.citations.length > 0 && (
        <section className={styles.citationsSection} aria-label="Grounded Citations">
          <div className={styles.sectionHeader}>
            <h4 className={styles.sectionTitle}>
              Verified Citations ({response.citations.length})
            </h4>
          </div>
          <div className={styles.citationGrid}>
            {response.citations.map((citation) => (
              <CitationCard
                key={citation.id}
                citation={citation}
                workspaceId={workspaceId}
              />
            ))}
          </div>
        </section>
      )}

      {response.retrieved_evidence && response.retrieved_evidence.length > 0 && (
        <section className={styles.evidenceSection} aria-label="Retrieved Evidence Passages">
          <button
            type="button"
            className={styles.evidenceToggle}
            onClick={() => setShowEvidence(!showEvidence)}
            aria-expanded={showEvidence}
          >
            <span>
              Retrieved Evidence Passages ({response.retrieved_evidence.length})
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
              {response.retrieved_evidence.map((evidence) => (
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
    </article>
  );
}
