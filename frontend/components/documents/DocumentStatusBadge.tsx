"use client";

import React from "react";
import { CheckCircle2, Loader2, Clock, AlertTriangle } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { DocumentProcessingStatus } from "@/lib/api/types";

export interface DocumentStatusBadgeProps {
  status: DocumentProcessingStatus;
  errorMessage?: string | null;
}

export const DocumentStatusBadge: React.FC<DocumentStatusBadgeProps> = ({
  status,
  errorMessage,
}) => {
  switch (status) {
    case "ready":
      return (
        <Badge variant="success">
          <span style={{ display: "inline-flex", alignItems: "center", gap: "var(--space-1)" }}>
            <CheckCircle2 size={12} />
            <span>Ready</span>
          </span>
        </Badge>
      );
    case "processing":
      return (
        <Badge variant="warning">
          <span style={{ display: "inline-flex", alignItems: "center", gap: "var(--space-1)" }}>
            <Loader2 size={12} className="lucide-spin" style={{ animation: "spin 1s linear infinite" }} />
            <span>Processing</span>
          </span>
        </Badge>
      );
    case "pending":
      return (
        <Badge variant="neutral">
          <span style={{ display: "inline-flex", alignItems: "center", gap: "var(--space-1)" }}>
            <Clock size={12} />
            <span>Queued</span>
          </span>
        </Badge>
      );
    case "failed":
      return (
        <span title={errorMessage || "Ingestion failed"} style={{ display: "inline-flex" }}>
          <Badge variant="danger">
            <span style={{ display: "inline-flex", alignItems: "center", gap: "var(--space-1)" }}>
              <AlertTriangle size={12} />
              <span>Failed</span>
            </span>
          </Badge>
        </span>
      );
    default:
      return <Badge variant="neutral">{status}</Badge>;
  }
};
