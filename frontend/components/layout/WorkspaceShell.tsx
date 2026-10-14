"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { ArrowLeft, AlertCircle, RefreshCw } from "lucide-react";
import { AppHeader } from "./AppHeader";
import { Sidebar } from "./Sidebar";
import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Skeleton";
import { getWorkspace } from "@/lib/api/workspaces";
import { WorkspaceResponse, ProblemDetails } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthContext";
import styles from "./WorkspaceShell.module.css";

export interface WorkspaceShellProps {
  workspaceId: string;
  children: React.ReactNode;
}

export const WorkspaceShell: React.FC<WorkspaceShellProps> = ({
  workspaceId,
  children,
}) => {
  const [workspace, setWorkspace] = useState<WorkspaceResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ProblemDetails | null>(null);
  const { isAuthenticated, openPasskeyModal } = useAuth();

  const loadWorkspace = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getWorkspace(workspaceId);
      setWorkspace(data);
    } catch (err: unknown) {
      const problem = err as ProblemDetails;
      setError(problem);
      if (problem.status_code === 401) {
        openPasskeyModal();
      }
    } finally {
      setLoading(false);
    }
  }, [workspaceId, openPasskeyModal]);

  useEffect(() => {
    loadWorkspace();
  }, [loadWorkspace, isAuthenticated]);

  if (loading) {
    return (
      <div className={styles.shell}>
        <AppHeader />
        <div className={styles.body}>
          <Sidebar workspaceId={workspaceId} />
          <main className={styles.mainContent}>
            <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
              <Skeleton width="40%" height="32px" />
              <Skeleton width="20%" height="20px" />
              <Skeleton width="100%" height="200px" />
            </div>
          </main>
        </div>
      </div>
    );
  }

  if (error) {
    const isNotFound = error.status_code === 404;
    return (
      <div className={styles.shell}>
        <AppHeader />
        <div className={styles.body}>
          <Sidebar workspaceId={workspaceId} />
          <main className={styles.mainContent}>
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                textAlign: "center",
                padding: "var(--space-12) var(--space-6)",
                backgroundColor: "var(--color-surface)",
                borderRadius: "var(--radius-lg)",
                border: "var(--border-width-thin) solid var(--color-border)",
                gap: "var(--space-4)",
                marginTop: "var(--space-8)",
              }}
            >
              <AlertCircle size={48} style={{ color: "var(--color-status-danger-text)" }} />
              <h2 style={{ fontSize: "var(--font-size-2xl)", fontWeight: 600 }}>
                {isNotFound ? "Workspace Not Found" : "Unable to Load Workspace"}
              </h2>
              <p
                style={{
                  color: "var(--color-text-secondary)",
                  fontSize: "var(--font-size-sm)",
                  maxWidth: "480px",
                }}
              >
                {isNotFound
                  ? `The requested workspace '${workspaceId}' does not exist or may have been deleted.`
                  : error.message}
              </p>
              <div style={{ display: "flex", gap: "var(--space-3)" }}>
                <Link href="/">
                  <Button variant="secondary" leftIcon={<ArrowLeft size={16} />}>
                    Return to Hub
                  </Button>
                </Link>
                {!isNotFound && (
                  <Button variant="primary" onClick={loadWorkspace} leftIcon={<RefreshCw size={16} />}>
                    Retry
                  </Button>
                )}
              </div>
            </div>
          </main>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.shell}>
      <AppHeader workspaceName={workspace?.name} />
      <div className={styles.body}>
        <Sidebar workspaceId={workspaceId} />
        <main className={styles.mainContent}>{children}</main>
      </div>
    </div>
  );
};
