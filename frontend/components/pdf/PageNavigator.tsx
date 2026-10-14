"use client";

import React from "react";
import {
  ChevronLeft,
  ChevronRight,
  ZoomIn,
  ZoomOut,
  Maximize2,
} from "lucide-react";
import { Button } from "@/components/ui/Button";

export interface PageNavigatorProps {
  currentPage: number;
  totalPages: number;
  scale: number;
  onPageChange: (newPage: number) => void;
  onScaleChange: (newScale: number) => void;
  disabled?: boolean;
}

export const PageNavigator: React.FC<PageNavigatorProps> = ({
  currentPage,
  totalPages,
  scale,
  onPageChange,
  onScaleChange,
  disabled = false,
}) => {
  const handlePageInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseInt(e.target.value, 10);
    if (!isNaN(val) && val >= 1 && val <= totalPages) {
      onPageChange(val);
    }
  };

  const zoomIn = () => {
    if (scale < 2.5) onScaleChange(Math.min(2.5, scale + 0.25));
  };

  const zoomOut = () => {
    if (scale > 0.5) onScaleChange(Math.max(0.5, scale - 0.25));
  };

  const resetZoom = () => {
    onScaleChange(1.0);
  };

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "var(--space-2) var(--space-4)",
        backgroundColor: "var(--color-surface)",
        border: "var(--border-width-thin) solid var(--color-border)",
        borderRadius: "var(--radius-md)",
        flexWrap: "wrap",
        gap: "var(--space-2)",
      }}
      role="toolbar"
      aria-label="PDF Navigation Controls"
    >
      {/* Page Navigation */}
      <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onPageChange(currentPage - 1)}
          disabled={disabled || currentPage <= 1}
          aria-label="Previous page"
          title="Previous page"
        >
          <ChevronLeft size={16} />
        </Button>

        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-1)", fontSize: "var(--font-size-xs)" }}>
          <span>Page</span>
          <input
            type="number"
            min={1}
            max={totalPages || 1}
            value={currentPage}
            onChange={handlePageInput}
            disabled={disabled || totalPages <= 1}
            style={{
              width: "48px",
              textAlign: "center",
              padding: "var(--space-1)",
              borderRadius: "var(--radius-sm)",
              border: "var(--border-width-thin) solid var(--color-border)",
              backgroundColor: "var(--color-canvas)",
              color: "var(--color-text-primary)",
              fontSize: "var(--font-size-xs)",
            }}
            aria-label="Current page number"
          />
          <span style={{ color: "var(--color-text-tertiary)" }}>of {totalPages || 1}</span>
        </div>

        <Button
          variant="ghost"
          size="sm"
          onClick={() => onPageChange(currentPage + 1)}
          disabled={disabled || currentPage >= totalPages}
          aria-label="Next page"
          title="Next page"
        >
          <ChevronRight size={16} />
        </Button>
      </div>

      {/* Zoom Controls */}
      <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
        <Button
          variant="ghost"
          size="sm"
          onClick={zoomOut}
          disabled={disabled || scale <= 0.5}
          aria-label="Zoom out"
          title="Zoom out"
        >
          <ZoomOut size={15} />
        </Button>

        <span
          style={{
            fontSize: "var(--font-size-xs)",
            color: "var(--color-text-secondary)",
            minWidth: "44px",
            textAlign: "center",
          }}
        >
          {Math.round(scale * 100)}%
        </span>

        <Button
          variant="ghost"
          size="sm"
          onClick={zoomIn}
          disabled={disabled || scale >= 2.5}
          aria-label="Zoom in"
          title="Zoom in"
        >
          <ZoomIn size={15} />
        </Button>

        <Button
          variant="ghost"
          size="sm"
          onClick={resetZoom}
          disabled={disabled || scale === 1.0}
          aria-label="Fit width / Reset zoom"
          title="Reset zoom to 100%"
        >
          <Maximize2 size={15} />
        </Button>
      </div>
    </div>
  );
};
