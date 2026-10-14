"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { DocumentResponse } from "@/lib/api/types";
import { listDocuments } from "@/lib/api/documents";

export const POLLING_INTERVAL_MS = 2000;

export interface UseIngestionPollingReturn {
  documents: DocumentResponse[];
  setDocuments: React.Dispatch<React.SetStateAction<DocumentResponse[]>>;
  isPolling: boolean;
  loading: boolean;
  error: string | null;
  refreshDocuments: () => Promise<void>;
}

export function useIngestionPolling(workspaceId: string): UseIngestionPollingReturn {
  const [documents, setDocuments] = useState<DocumentResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isPolling, setIsPolling] = useState(false);

  const isMountedRef = useRef(true);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  const fetchDocs = useCallback(async (isInitial = false) => {
    if (!workspaceId) return;
    if (isInitial) setLoading(true);

    try {
      const data = await listDocuments(workspaceId);
      if (!isMountedRef.current) return;
      setDocuments(data);
      setError(null);
    } catch (err: unknown) {
      if (!isMountedRef.current) return;
      const msg = err instanceof Error ? err.message : "Failed to load documents.";
      if (isInitial) setError(msg);
    } finally {
      if (isMountedRef.current && isInitial) {
        setLoading(false);
      }
    }
  }, [workspaceId]);

  // Initial fetch on mount or workspaceId change
  useEffect(() => {
    isMountedRef.current = true;
    fetchDocs(true);

    return () => {
      isMountedRef.current = false;
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [fetchDocs]);

  // Polling loop logic: poll if any document is in non-terminal state
  useEffect(() => {
    const hasActiveJobs = documents.some(
      (doc) => doc.status === "pending" || doc.status === "processing"
    );

    if (hasActiveJobs) {
      setIsPolling(true);
      if (!timerRef.current) {
        timerRef.current = setInterval(() => {
          fetchDocs(false);
        }, POLLING_INTERVAL_MS);
      }
    } else {
      setIsPolling(false);
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    }

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [documents, fetchDocs]);

  return {
    documents,
    setDocuments,
    isPolling,
    loading,
    error,
    refreshDocuments: () => fetchDocs(false),
  };
}
