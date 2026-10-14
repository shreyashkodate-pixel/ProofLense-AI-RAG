"use client";

import React from "react";
import type { DocumentResponse } from "@/lib/api/types";
import styles from "./DocumentSelector.module.css";

interface DocumentSelectorProps {
  documents: DocumentResponse[];
  selectedIds: string[];
  onChange: (ids: string[]) => void;
  disabled?: boolean;
}

export function DocumentSelector({
  documents,
  selectedIds,
  onChange,
  disabled = false,
}: DocumentSelectorProps) {
  const readyDocs = documents.filter((d) => d.status === "ready");
  const count = selectedIds.length;
  const isValidCount = count >= 2 && count <= 5;

  const handleToggle = (id: string) => {
    if (disabled) return;
    if (selectedIds.includes(id)) {
      onChange(selectedIds.filter((item) => item !== id));
    } else {
      if (selectedIds.length >= 5) return;
      onChange([...selectedIds, id]);
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <div>
          <h3 className={styles.title}>Select Documents to Compare</h3>
          <p className={styles.helperText}>
            Cross-document comparison requires selecting between 2 and 5 processed documents.
          </p>
        </div>
        <span
          className={`${styles.countBadge} ${
            isValidCount ? styles.countValid : styles.countInvalid
          }`}
          role="status"
        >
          {count} / 5 Selected {isValidCount ? "(Valid)" : "(Need 2–5)"}
        </span>
      </div>

      {readyDocs.length === 0 ? (
        <div className={styles.emptyState}>
          No ready documents available in this workspace. Upload and process documents first.
        </div>
      ) : (
        <div className={styles.docGrid} role="group" aria-label="Selectable documents">
          {readyDocs.map((doc) => {
            const isSelected = selectedIds.includes(doc.id);
            const isMaxReached = selectedIds.length >= 5 && !isSelected;

            return (
              <label
                key={doc.id}
                className={`${styles.docItem} ${
                  isSelected ? styles.docItemSelected : ""
                }`}
                style={{
                  opacity: isMaxReached || disabled ? 0.6 : 1,
                  cursor: isMaxReached || disabled ? "not-allowed" : "pointer",
                }}
              >
                <input
                  type="checkbox"
                  className={styles.checkbox}
                  checked={isSelected}
                  onChange={() => handleToggle(doc.id)}
                  disabled={disabled || (isMaxReached && !isSelected)}
                  aria-label={`Select ${doc.filename}`}
                />
                <div className={styles.docInfo}>
                  <span className={styles.docFilename} title={doc.filename}>
                    {doc.filename}
                  </span>
                  <span className={styles.docPages}>
                    {doc.page_count ? `${doc.page_count} pages` : "Document"}
                  </span>
                </div>
              </label>
            );
          })}
        </div>
      )}
    </div>
  );
}
