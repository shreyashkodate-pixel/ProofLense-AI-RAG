"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { Plus, FolderOpen, ArrowRight, Trash2, AlertCircle, RefreshCw } from "lucide-react";
import { AppHeader } from "@/components/layout/AppHeader";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Skeleton } from "@/components/ui/Skeleton";
import { useToast } from "@/components/ui/Toast";
import { useAuth } from "@/lib/auth/AuthContext";
import {
  listWorkspaces,
  createWorkspace,
  deleteWorkspace,
} from "@/lib/api/workspaces";
import { WorkspaceResponse, ProblemDetails } from "@/lib/api/types";
import styles from "./page.module.css";

export default function WorkspaceHubPage() {
  const [workspaces, setWorkspaces] = useState<WorkspaceResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Create Workspace Modal
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [newWorkspaceName, setNewWorkspaceName] = useState("");
  const [createError, setCreateError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  // Delete Workspace Confirmation Modal
  const [deletingWorkspace, setDeletingWorkspace] = useState<WorkspaceResponse | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const { addToast } = useToast();
  const { isAuthenticated, openPasskeyModal } = useAuth();

  const loadWorkspaces = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listWorkspaces();
      setWorkspaces(data);
    } catch (err: unknown) {
      const problem = err as ProblemDetails;
      if (problem.status_code === 401) {
        setError("Access passkey required to view workspaces.");
        openPasskeyModal();
      } else {
        setError(problem.message || "Failed to load workspaces. Please check backend connection.");
      }
    } finally {
      setLoading(false);
    }
  }, [openPasskeyModal]);

  useEffect(() => {
    loadWorkspaces();
  }, [loadWorkspaces, isAuthenticated]);

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = newWorkspaceName.trim();
    if (!trimmed) {
      setCreateError("Workspace name is required.");
      return;
    }
    if (trimmed.length > 255) {
      setCreateError("Workspace name cannot exceed 255 characters.");
      return;
    }

    setCreating(true);
    setCreateError(null);
    try {
      const created = await createWorkspace({ name: trimmed });
      setWorkspaces((prev) => [created, ...prev]);
      setIsCreateOpen(false);
      setNewWorkspaceName("");
      addToast({
        title: "Workspace created",
        message: `Workspace "${created.name}" is ready.`,
        type: "success",
      });
    } catch (err: unknown) {
      const problem = err as ProblemDetails;
      setCreateError(problem.message || "Failed to create workspace.");
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteConfirm = async () => {
    if (!deletingWorkspace) return;
    setIsDeleting(true);
    try {
      await deleteWorkspace(deletingWorkspace.id);
      setWorkspaces((prev) => prev.filter((w) => w.id !== deletingWorkspace.id));
      addToast({
        title: "Workspace deleted",
        message: `Workspace "${deletingWorkspace.name}" was permanently removed.`,
        type: "info",
      });
      setDeletingWorkspace(null);
    } catch (err: unknown) {
      const problem = err as ProblemDetails;
      addToast({
        title: "Deletion failed",
        message: problem.message || "Failed to delete workspace.",
        type: "error",
      });
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className={styles.page}>
      <AppHeader />

      <main className={styles.main}>
        <div className={styles.hero}>
          <div className={styles.titleArea}>
            <h1 className={styles.title}>Workspace Hub</h1>
            <p className={styles.subtitle}>
              Select or create an isolated workspace for evidence-first document intelligence.
            </p>
          </div>
          <Button
            variant="primary"
            leftIcon={<Plus size={16} />}
            onClick={() => {
              setCreateError(null);
              setNewWorkspaceName("");
              setIsCreateOpen(true);
            }}
          >
            New Workspace
          </Button>
        </div>

        {/* Error banner */}
        {error && (
          <div
            role="alert"
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "var(--space-3) var(--space-4)",
              backgroundColor: "var(--color-status-danger-bg)",
              border: "var(--border-width-thin) solid var(--color-status-danger-border)",
              borderRadius: "var(--radius-md)",
              color: "var(--color-status-danger-text)",
              fontSize: "var(--font-size-sm)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
              <AlertCircle size={18} />
              <span>{error}</span>
            </div>
            <Button variant="secondary" size="sm" onClick={loadWorkspaces} leftIcon={<RefreshCw size={14} />}>
              Retry
            </Button>
          </div>
        )}

        {/* Loading state */}
        {loading && (
          <div className={styles.grid}>
            {[1, 2, 3].map((n) => (
              <div
                key={n}
                style={{
                  padding: "var(--space-5)",
                  backgroundColor: "var(--color-surface)",
                  borderRadius: "var(--radius-lg)",
                  border: "var(--border-width-thin) solid var(--color-border)",
                  display: "flex",
                  flexDirection: "column",
                  gap: "var(--space-3)",
                }}
              >
                <Skeleton width="60%" height="24px" />
                <Skeleton width="40%" height="16px" />
                <div style={{ marginTop: "var(--space-4)" }}>
                  <Skeleton width="100%" height="36px" />
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Empty state */}
        {!loading && !error && workspaces.length === 0 && (
          <div className={styles.emptyState}>
            <FolderOpen size={48} className={styles.emptyIcon} />
            <h2 className={styles.emptyTitle}>No workspaces found</h2>
            <p className={styles.emptyDescription}>
              Create your first workspace to start uploading PDF documents, running grounded queries,
              and verifying citations.
            </p>
            <Button
              variant="primary"
              leftIcon={<Plus size={16} />}
              onClick={() => setIsCreateOpen(true)}
            >
              Create Workspace
            </Button>
          </div>
        )}

        {/* Workspaces Grid */}
        {!loading && !error && workspaces.length > 0 && (
          <div className={styles.grid}>
            {workspaces.map((workspace) => (
              <div key={workspace.id} className={styles.workspaceCard}>
                <div className={styles.cardHeader}>
                  <div style={{ minWidth: 0 }}>
                    <h2 className={styles.cardName} title={workspace.name}>
                      {workspace.name}
                    </h2>
                    <span style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-tertiary)" }}>
                      Created {new Date(workspace.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={(e) => {
                      e.preventDefault();
                      setDeletingWorkspace(workspace);
                    }}
                    title="Delete workspace"
                    style={{ color: "var(--color-status-danger-text)" }}
                  >
                    <Trash2 size={16} />
                  </Button>
                </div>

                <div className={styles.cardFooter}>
                  <Link
                    href={`/workspaces/${workspace.id}`}
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "var(--space-1)",
                      color: "var(--color-accent)",
                      fontWeight: 600,
                      textDecoration: "none",
                    }}
                  >
                    <span>Open Workspace</span>
                    <ArrowRight size={14} />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>

      {/* Create Workspace Modal */}
      <Modal
        isOpen={isCreateOpen}
        onClose={() => !creating && setIsCreateOpen(false)}
        title="Create New Workspace"
      >
        <form onSubmit={handleCreateSubmit} style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
          <Input
            label="Workspace Name"
            placeholder="e.g., Financial Q3 Audit or Clinical Trials 2026"
            value={newWorkspaceName}
            onChange={(e) => setNewWorkspaceName(e.target.value)}
            errorMessage={createError || undefined}
            disabled={creating}
            autoFocus
            maxLength={255}
          />
          <div style={{ display: "flex", justifyContent: "flex-end", gap: "var(--space-2)", marginTop: "var(--space-2)" }}>
            <Button
              type="button"
              variant="secondary"
              onClick={() => setIsCreateOpen(false)}
              disabled={creating}
            >
              Cancel
            </Button>
            <Button type="submit" variant="primary" isLoading={creating}>
              Create Workspace
            </Button>
          </div>
        </form>
      </Modal>

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={Boolean(deletingWorkspace)}
        onClose={() => !isDeleting && setDeletingWorkspace(null)}
        title="Delete Workspace"
      >
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
          <p style={{ color: "var(--color-text-secondary)", fontSize: "var(--font-size-sm)" }}>
            Are you sure you want to delete workspace <strong>{deletingWorkspace?.name}</strong>?
            This will permanently cascade-delete all uploaded documents, extracted pages, and
            semantic embeddings. This action cannot be undone.
          </p>
          <div style={{ display: "flex", justifyContent: "flex-end", gap: "var(--space-2)" }}>
            <Button
              type="button"
              variant="secondary"
              onClick={() => setDeletingWorkspace(null)}
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
    </div>
  );
}
