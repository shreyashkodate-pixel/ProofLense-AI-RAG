"use client";

import React, { useState } from "react";
import { Layers, Search, FileText, ChevronRight } from "lucide-react";
import { Input } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
import {
  DocumentChunkDetailResponse,
  DocumentPageDetailResponse,
} from "@/lib/api/types";
import styles from "./ExtractedChunksDrawer.module.css";

export interface ExtractedChunksDrawerProps {
  pages: DocumentPageDetailResponse[];
  loading?: boolean;
  selectedChunkId?: string | null;
  onSelectChunk: (chunk: DocumentChunkDetailResponse) => void;
}

export const ExtractedChunksDrawer: React.FC<ExtractedChunksDrawerProps> = ({
  pages,
  loading = false,
  selectedChunkId,
  onSelectChunk,
}) => {
  const [filterText, setFilterText] = useState("");

  const filteredPages = pages
    .map((page) => {
      const filteredChunks = (page.chunks || []).filter((chunk) => {
        if (!filterText.trim()) return true;
        return chunk.chunk_text.toLowerCase().includes(filterText.toLowerCase());
      });
      return {
        ...page,
        chunks: filteredChunks,
      };
    })
    .filter((page) => page.chunks.length > 0 || !filterText.trim());

  const totalChunks = pages.reduce((acc, p) => acc + (p.chunks?.length || 0), 0);

  return (
    <aside className={styles.drawer} aria-label="Extracted Evidence Chunks">
      <div className={styles.header}>
        <div className={styles.titleArea}>
          <div className={styles.title}>
            <Layers size={18} style={{ color: "var(--color-accent)" }} />
            <span>Evidence Chunks</span>
          </div>
          <Badge variant="neutral">{totalChunks} chunks</Badge>
        </div>

        <Input
          placeholder="Filter chunk text..."
          value={filterText}
          onChange={(e) => setFilterText(e.target.value)}
          leftIcon={<Search size={14} />}
          style={{ fontSize: "var(--font-size-xs)" }}
        />
      </div>

      <div className={styles.content}>
        {loading ? (
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
            <Skeleton width="100%" height="80px" />
            <Skeleton width="100%" height="80px" />
            <Skeleton width="100%" height="80px" />
          </div>
        ) : pages.length === 0 ? (
          <div className={styles.emptyState}>
            <FileText size={32} />
            <div>No extracted chunks available yet</div>
            <p>Once ingestion completes, physical page chunks will appear here for inspection.</p>
          </div>
        ) : filteredPages.length === 0 ? (
          <div className={styles.emptyState}>
            <div>No chunks match &ldquo;{filterText}&rdquo;</div>
          </div>
        ) : (
          filteredPages.map((page) => (
            <div key={page.id} className={styles.pageSection}>
              <div className={styles.pageHeader}>
                <span>Page {page.page_number}</span>
                <span>{page.char_count} chars</span>
              </div>

              {(page.chunks || []).map((chunk) => {
                const isSelected = selectedChunkId === chunk.id;
                return (
                  <button
                    key={chunk.id}
                    type="button"
                    className={`${styles.chunkCard} ${
                      isSelected ? styles.chunkCardActive : ""
                    }`}
                    onClick={() => onSelectChunk(chunk)}
                  >
                    <div className={styles.chunkMeta}>
                      <span>Chunk #{chunk.chunk_index}</span>
                      <span style={{ display: "inline-flex", alignItems: "center", gap: "2px" }}>
                        <span>{chunk.token_count ?? "~"} tokens</span>
                        <ChevronRight size={12} />
                      </span>
                    </div>
                    <div className={styles.chunkText} title={chunk.chunk_text}>
                      {chunk.chunk_text}
                    </div>
                  </button>
                );
              })}
            </div>
          ))
        )}
      </div>
    </aside>
  );
};
