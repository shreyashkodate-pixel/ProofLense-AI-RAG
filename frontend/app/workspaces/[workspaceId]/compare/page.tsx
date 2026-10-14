"use client";

import React, { use, useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { executeComparison, listComparisons, getComparison } from "@/lib/api/comparisons";
import { listDocuments } from "@/lib/api/documents";
import type {
  ComparisonResponse,
  SavedComparisonResponse,
  DocumentResponse,
} from "@/lib/api/types";
import { DocumentSelector } from "@/components/comparison/DocumentSelector";
import { ComparisonMatrix } from "@/components/comparison/ComparisonMatrix";
import styles from "./compare.module.css";

interface ComparePageProps {
  params: Promise<{ workspaceId: string }>;
}

const MIN_QUERY_LENGTH = 3;
const MAX_QUERY_LENGTH = 1000;

export default function WorkspaceComparePage({ params }: ComparePageProps) {
  const workspaceId =
    params && typeof (params as unknown as Promise<unknown>).then === "function"
      ? use(params).workspaceId
      : (params as unknown as { workspaceId: string }).workspaceId;

  const [documents, setDocuments] = useState<DocumentResponse[]>([]);
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
  const [queryText, setQueryText] = useState("");
  const [history, setHistory] = useState<SavedComparisonResponse[]>([]);
  const [activeComparison, setActiveComparison] = useState<
    ComparisonResponse | SavedComparisonResponse | null
  >(null);
  const [loadingData, setLoadingData] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const loadInitialData = useCallback(async () => {
    try {
      setLoadingData(true);
      const [docs, comps] = await Promise.all([
        listDocuments(workspaceId).catch(() => []),
        listComparisons(workspaceId).catch(() => []),
      ]);
      setDocuments(docs);
      setHistory(comps);

      const ready = docs.filter((d) => d.status === "ready");
      if (ready.length >= 2) {
        setSelectedDocIds(ready.slice(0, Math.min(ready.length, 5)).map((d) => d.id));
      }

      if (comps.length > 0) {
        // Load the most recent comparison into view
        try {
          const detail = await getComparison(workspaceId, comps[0].comparison_id);
          setActiveComparison(detail);
        } catch {
          // ignore
        }
      }
    } catch {
      // ignore
    } finally {
      setLoadingData(false);
    }
  }, [workspaceId]);

  useEffect(() => {
    loadInitialData();
  }, [loadInitialData]);

  const readyDocs = documents.filter((d) => d.status === "ready");
  const trimmed = queryText.trim();
  const isValidQuery = trimmed.length >= MIN_QUERY_LENGTH && trimmed.length <= MAX_QUERY_LENGTH;
  const isValidDocs = selectedDocIds.length >= 2 && selectedDocIds.length <= 5;
  const canSubmit = isValidQuery && isValidDocs && !submitting;

  const handleCompare = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;

    try {
      setSubmitting(true);
      setErrorMessage(null);

      const result = await executeComparison(workspaceId, {
        query_text: trimmed,
        document_ids: selectedDocIds,
      });

      setActiveComparison(result);

      // Prepend to history
      const savedItem: SavedComparisonResponse = {
        comparison_id: result.comparison_id,
        workspace_id: result.workspace_id,
        query_text: result.query_text,
        status: result.status,
        is_abstention: result.is_abstention,
        top_score: null,
        synthesis: result.synthesis,
        citations: result.findings.flatMap((f) => f.citations),
        retrieved_evidence: result.retrieved_evidence,
        created_at: result.created_at,
      };
      setHistory((prev) => [
        savedItem,
        ...prev.filter((p) => p.comparison_id !== savedItem.comparison_id),
      ]);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to execute comparison.";
      setErrorMessage(msg);
    } finally {
      setSubmitting(false);
    }
  };

  const handleSelectHistory = async (saved: SavedComparisonResponse) => {
    try {
      setErrorMessage(null);
      const detail = await getComparison(workspaceId, saved.comparison_id);
      setActiveComparison(detail);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load past comparison.";
      setErrorMessage(msg);
    }
  };

  return (
    <div className={styles.pageContainer}>
      <header className={styles.header}>
        <h1 className={styles.title}>Cross-Document Comparison</h1>
        <p className={styles.subtitle}>
          Compare clauses, policies, or topics across 2 to 5 indexed documents. ProofLens categorizes findings into agreements, contradictions, and differences with strict citation grounding.
        </p>
      </header>

      {readyDocs.length < 2 && !loadingData && (
        <div className={styles.warningBanner} role="status">
          <span>
            At least 2 processed documents are required for cross-document comparison. Currently, {readyDocs.length} ready document(s) available.
          </span>
          <Link
            href={`/workspaces/${workspaceId}/documents`}
            className={styles.warningLink}
          >
            Upload More Documents &rarr;
          </Link>
        </div>
      )}

      {errorMessage && (
        <div className={styles.errorBanner} role="alert">
          <span>{errorMessage}</span>
          <button
            type="button"
            className={styles.dismissBtn}
            onClick={() => setErrorMessage(null)}
          >
            Dismiss
          </button>
        </div>
      )}

      <div className={styles.layoutGrid}>
        <div className={styles.mainColumn}>
          <form className={styles.composerCard} onSubmit={handleCompare} noValidate>
            <h2 className={styles.composerTitle}>Comparison Query</h2>

            <DocumentSelector
              documents={documents}
              selectedIds={selectedDocIds}
              onChange={setSelectedDocIds}
              disabled={submitting}
            />

            <div>
              <textarea
                className={`${styles.textarea} ${
                  queryText.length > MAX_QUERY_LENGTH ? styles.textareaError : ""
                }`}
                value={queryText}
                onChange={(e) => setQueryText(e.target.value)}
                placeholder="e.g., Compare the termination notice periods and severance liability across these agreements."
                disabled={submitting || readyDocs.length < 2}
                aria-label="Comparison topic or question"
                rows={3}
              />

              <div className={styles.metaRow}>
                {queryText.length > 0 && queryText.length < MIN_QUERY_LENGTH && (
                  <p className={styles.errorMessage} role="alert">
                    Query must be at least {MIN_QUERY_LENGTH} characters.
                  </p>
                )}
                <span
                  className={`${styles.charCounter} ${
                    queryText.length > MAX_QUERY_LENGTH ? styles.charCounterExceeded : ""
                  }`}
                  aria-live="polite"
                >
                  {queryText.length} / {MAX_QUERY_LENGTH}
                </span>
              </div>
            </div>

            <button
              type="submit"
              className={styles.submitBtn}
              disabled={!canSubmit}
            >
              {submitting ? (
                <>
                  <svg
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    className="spin"
                    aria-hidden="true"
                  >
                    <circle cx="12" cy="12" r="10" strokeDasharray="32" strokeDashoffset="12" />
                  </svg>
                  <span>Synthesizing Across Documents...</span>
                </>
              ) : (
                <>
                  <svg
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    aria-hidden="true"
                  >
                    <line x1="18" y1="20" x2="18" y2="10" />
                    <line x1="12" y1="20" x2="12" y2="4" />
                    <line x1="6" y1="20" x2="6" y2="14" />
                  </svg>
                  <span>Run Comparison</span>
                </>
              )}
            </button>
          </form>

          {activeComparison && (
            <ComparisonMatrix
              comparison={activeComparison}
              workspaceId={workspaceId}
            />
          )}
        </div>

        <aside className={styles.sidebarColumn} aria-label="Comparison History">
          <h2 className={styles.historyTitle}>Comparison History</h2>

          {loadingData ? (
            <p className={styles.emptyHistory}>Loading comparison history...</p>
          ) : history.length === 0 ? (
            <p className={styles.emptyHistory}>
              No comparisons executed yet. Select documents and enter a query to run a comparison.
            </p>
          ) : (
            <div className={styles.historyList} role="list">
              {history.map((comp) => {
                const isActive = activeComparison?.comparison_id === comp.comparison_id;
                return (
                  <button
                    key={comp.comparison_id}
                    type="button"
                    className={`${styles.historyItem} ${
                      isActive ? styles.historyItemActive : ""
                    }`}
                    onClick={() => handleSelectHistory(comp)}
                    aria-current={isActive ? "true" : undefined}
                  >
                    <span className={styles.historyQueryText}>{comp.query_text}</span>
                    <div className={styles.historyMeta}>
                      <span>
                        {new Date(comp.created_at).toLocaleDateString(undefined, {
                          month: "short",
                          day: "numeric",
                        })}
                      </span>
                      {comp.is_abstention ? (
                        <span
                          style={{
                            fontSize: 10,
                            fontWeight: 600,
                            color: "#b45309",
                            backgroundColor: "#fef3c7",
                            padding: "1px 6px",
                            borderRadius: "var(--radius-sm)",
                          }}
                        >
                          Abstained
                        </span>
                      ) : (
                        <span
                          style={{
                            fontSize: 10,
                            fontWeight: 600,
                            color: "var(--color-accent)",
                            backgroundColor: "var(--color-accent-soft)",
                            padding: "1px 6px",
                            borderRadius: "var(--radius-sm)",
                          }}
                        >
                          Compared
                        </span>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
