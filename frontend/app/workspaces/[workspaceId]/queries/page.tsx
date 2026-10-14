"use client";

import React, { use, useEffect, useState } from "react";
import Link from "next/link";
import { executeQuery, listQueries } from "@/lib/api/queries";
import { listDocuments } from "@/lib/api/documents";
import type { QueryResponse, DocumentResponse } from "@/lib/api/types";
import { QueryComposer } from "@/components/queries/QueryComposer";
import { AnswerDisplay } from "@/components/queries/AnswerDisplay";
import styles from "./queries.module.css";

interface QueriesPageProps {
  params: Promise<{ workspaceId: string }>;
}

export default function WorkspaceQueriesPage({ params }: QueriesPageProps) {
  const workspaceId =
    params && typeof (params as unknown as Promise<unknown>).then === "function"
      ? use(params).workspaceId
      : (params as unknown as { workspaceId: string }).workspaceId;

  const [documents, setDocuments] = useState<DocumentResponse[]>([]);
  const [history, setHistory] = useState<QueryResponse[]>([]);
  const [activeQuery, setActiveQuery] = useState<QueryResponse | null>(null);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    async function init() {
      try {
        setLoadingHistory(true);
        const [docs, queries] = await Promise.all([
          listDocuments(workspaceId).catch(() => []),
          listQueries(workspaceId).catch(() => []),
        ]);
        if (mounted) {
          setDocuments(docs);
          setHistory(queries);
          if (queries.length > 0) {
            setActiveQuery(queries[0]);
          }
        }
      } catch {
        // Handled silently
      } finally {
        if (mounted) setLoadingHistory(false);
      }
    }

    init();
    return () => {
      mounted = false;
    };
  }, [workspaceId]);

  const handleAsk = async (queryText: string, topK: number) => {
    try {
      setSubmitting(true);
      setErrorMessage(null);

      const response = await executeQuery(workspaceId, {
        query_text: queryText,
        top_k: topK,
      });

      setActiveQuery(response);
      setHistory((prev) => [
        response,
        ...prev.filter((p) => p.query_run_id !== response.query_run_id),
      ]);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to execute query.";
      setErrorMessage(msg);
    } finally {
      setSubmitting(false);
    }
  };

  const readyDocuments = documents.filter((d) => d.status === "ready");

  return (
    <div className={styles.pageContainer}>
      <header className={styles.header}>
        <h1 className={styles.title}>Grounded Document Q&amp;A</h1>
        <p className={styles.subtitle}>
          Ask questions across your indexed PDF documents. ProofLens extracts verifiable citations with 1-indexed page provenance, explicitly abstaining when adequate evidence is absent.
        </p>
      </header>

      {readyDocuments.length === 0 && !loadingHistory && (
        <div className={styles.warningBanner} role="status">
          <span>
            No processed documents found in this workspace. Upload and process PDF files first to enable grounded retrieval.
          </span>
          <Link
            href={`/workspaces/${workspaceId}/documents`}
            className={styles.warningLink}
          >
            Upload Documents &rarr;
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
          <QueryComposer
            onSubmit={handleAsk}
            isSubmitting={submitting}
            disabled={readyDocuments.length === 0 && !loadingHistory}
          />

          {activeQuery && (
            <AnswerDisplay
              response={activeQuery}
              workspaceId={workspaceId}
            />
          )}
        </div>

        <aside className={styles.sidebarColumn} aria-label="Query History">
          <h2 className={styles.historyTitle}>Query History</h2>

          {loadingHistory ? (
            <p className={styles.emptyHistory}>Loading query history...</p>
          ) : history.length === 0 ? (
            <p className={styles.emptyHistory}>
              No queries executed yet. Ask a question above to begin.
            </p>
          ) : (
            <div className={styles.historyList} role="list">
              {history.map((q) => {
                const isActive = activeQuery?.query_run_id === q.query_run_id;
                return (
                  <button
                    key={q.query_run_id}
                    type="button"
                    className={`${styles.historyItem} ${
                      isActive ? styles.historyItemActive : ""
                    }`}
                    onClick={() => setActiveQuery(q)}
                    aria-current={isActive ? "true" : undefined}
                  >
                    <span className={styles.historyQueryText}>{q.query_text}</span>
                    <div className={styles.historyMeta}>
                      <span>
                        {new Date(q.created_at).toLocaleDateString(undefined, {
                          month: "short",
                          day: "numeric",
                        })}
                      </span>
                      {q.is_abstention ? (
                        <span className={styles.historyAbstentionBadge}>
                          Abstained
                        </span>
                      ) : (
                        <span className={styles.historyGroundedBadge}>
                          {q.citations?.length || 0} Citations
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
