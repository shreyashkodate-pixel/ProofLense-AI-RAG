"use client";

import React, { use, useEffect, useState } from "react";
import Link from "next/link";
import { Files, UploadCloud, CheckCircle2, Clock, AlertTriangle, ArrowRight } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
import { DocumentResponse } from "@/lib/api/types";
import { listDocuments } from "@/lib/api/documents";

export default function WorkspaceOverviewPage({
  params,
}: {
  params: Promise<{ workspaceId: string }>;
}) {
  const { workspaceId } = use(params);
  const [documents, setDocuments] = useState<DocumentResponse[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    async function fetchDocs() {
      try {
        const docs = await listDocuments(workspaceId);
        if (mounted) setDocuments(docs);
      } catch {
        // Handled silently or empty state
      } finally {
        if (mounted) setLoading(false);
      }
    }
    fetchDocs();
    return () => {
      mounted = false;
    };
  }, [workspaceId]);

  const readyCount = documents.filter((d) => d.status === "ready").length;
  const processingCount = documents.filter((d) => d.status === "processing" || d.status === "pending").length;
  const failedCount = documents.filter((d) => d.status === "failed").length;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-6)" }}>
      {/* Hero Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "var(--space-4)" }}>
        <div>
          <h1 style={{ fontSize: "var(--font-size-3xl)", fontWeight: 700, color: "var(--color-text-primary)" }}>
            Workspace Dashboard
          </h1>
          <p style={{ fontSize: "var(--font-size-md)", color: "var(--color-text-secondary)", marginTop: "var(--space-1)" }}>
            Evidence-grounded intelligence overview and document library stats.
          </p>
        </div>
        <div style={{ display: "flex", gap: "var(--space-3)" }}>
          <Link href={`/workspaces/${workspaceId}/documents`}>
            <Button variant="primary" leftIcon={<UploadCloud size={16} />}>
              Manage & Upload Documents
            </Button>
          </Link>
        </div>
      </div>

      {/* KPI Stat Cards */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: "var(--space-4)",
        }}
      >
        <Card>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <span style={{ fontSize: "var(--font-size-sm)", color: "var(--color-text-secondary)" }}>
              Total Documents
            </span>
            <Files size={18} style={{ color: "var(--color-accent)" }} />
          </div>
          <div style={{ fontSize: "var(--font-size-3xl)", fontWeight: 700, marginTop: "var(--space-2)" }}>
            {loading ? <Skeleton width="48px" height="36px" /> : documents.length}
          </div>
        </Card>

        <Card>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <span style={{ fontSize: "var(--font-size-sm)", color: "var(--color-text-secondary)" }}>
              Ready for Search
            </span>
            <CheckCircle2 size={18} style={{ color: "var(--color-status-success-text)" }} />
          </div>
          <div style={{ fontSize: "var(--font-size-3xl)", fontWeight: 700, marginTop: "var(--space-2)", color: "var(--color-status-success-text)" }}>
            {loading ? <Skeleton width="48px" height="36px" /> : readyCount}
          </div>
        </Card>

        <Card>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <span style={{ fontSize: "var(--font-size-sm)", color: "var(--color-text-secondary)" }}>
              In Progress
            </span>
            <Clock size={18} style={{ color: "var(--color-status-warning-text)" }} />
          </div>
          <div style={{ fontSize: "var(--font-size-3xl)", fontWeight: 700, marginTop: "var(--space-2)", color: "var(--color-status-warning-text)" }}>
            {loading ? <Skeleton width="48px" height="36px" /> : processingCount}
          </div>
        </Card>

        <Card>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <span style={{ fontSize: "var(--font-size-sm)", color: "var(--color-text-secondary)" }}>
              Failed Ingestions
            </span>
            <AlertTriangle size={18} style={{ color: "var(--color-status-danger-text)" }} />
          </div>
          <div style={{ fontSize: "var(--font-size-3xl)", fontWeight: 700, marginTop: "var(--space-2)", color: "var(--color-status-danger-text)" }}>
            {loading ? <Skeleton width="48px" height="36px" /> : failedCount}
          </div>
        </Card>
      </div>

      {/* Recent Documents Section */}
      <Card>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "var(--space-4)" }}>
          <span style={{ fontWeight: 600, fontSize: "var(--font-size-lg)" }}>Recent Documents</span>
          <Link
            href={`/workspaces/${workspaceId}/documents`}
            style={{
              fontSize: "var(--font-size-sm)",
              color: "var(--color-accent)",
              textDecoration: "none",
              display: "inline-flex",
              alignItems: "center",
              gap: "var(--space-1)",
            }}
          >
            <span>View All</span>
            <ArrowRight size={14} />
          </Link>
        </div>
        {loading ? (
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
            <Skeleton width="100%" height="40px" />
            <Skeleton width="100%" height="40px" />
          </div>
        ) : documents.length === 0 ? (
          <div style={{ textAlign: "center", padding: "var(--space-8) 0", color: "var(--color-text-secondary)" }}>
            <p>No documents uploaded yet in this workspace.</p>
            <Link href={`/workspaces/${workspaceId}/documents`} style={{ marginTop: "var(--space-3)", display: "inline-block" }}>
              <Button variant="secondary" size="sm" leftIcon={<UploadCloud size={14} />}>
                Upload your first PDF
              </Button>
            </Link>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
            {documents.slice(0, 5).map((doc) => (
              <div
                key={doc.id}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "var(--space-3)",
                  borderRadius: "var(--radius-md)",
                  border: "var(--border-width-thin) solid var(--color-border)",
                  backgroundColor: "var(--color-canvas)",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
                  <Files size={18} style={{ color: "var(--color-text-secondary)" }} />
                  <div>
                    <div style={{ fontWeight: 500, fontSize: "var(--font-size-sm)", color: "var(--color-text-primary)" }}>
                      {doc.filename}
                    </div>
                    <div style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-tertiary)" }}>
                      {(doc.file_size_bytes / 1024).toFixed(1)} KB • {doc.page_count ? `${doc.page_count} pages` : "Pages calculating..."}
                    </div>
                  </div>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
                  <Badge
                    variant={
                      doc.status === "ready"
                        ? "success"
                        : doc.status === "failed"
                        ? "danger"
                        : "warning"
                    }
                  >
                    {doc.status}
                  </Badge>
                  <Link href={`/workspaces/${workspaceId}/documents/${doc.id}`}>
                    <Button variant="ghost" size="sm">
                      Inspect
                    </Button>
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
