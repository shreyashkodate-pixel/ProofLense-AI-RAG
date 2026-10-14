"use client";

import React, { useState } from "react";
import styles from "./QueryComposer.module.css";

interface QueryComposerProps {
  onSubmit: (queryText: string, topK: number) => Promise<void> | void;
  isSubmitting: boolean;
  initialQuery?: string;
  disabled?: boolean;
}

const MAX_QUERY_LENGTH = 2000;

export function QueryComposer({
  onSubmit,
  isSubmitting,
  initialQuery = "",
  disabled = false,
}: QueryComposerProps) {
  const [queryText, setQueryText] = useState(initialQuery);
  const [topK, setTopK] = useState<number>(5);
  const [validationError, setValidationError] = useState<string | null>(null);

  const trimmed = queryText.trim();
  const charCount = queryText.length;
  const isOverLimit = charCount > MAX_QUERY_LENGTH;
  const isValid = trimmed.length >= 1 && !isOverLimit;

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!isValid || isSubmitting || disabled) {
      if (trimmed.length === 0) {
        setValidationError("Please enter a question to query your documents.");
      } else if (isOverLimit) {
        setValidationError(`Query cannot exceed ${MAX_QUERY_LENGTH} characters.`);
      }
      return;
    }

    setValidationError(null);
    await onSubmit(trimmed, topK);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <form className={styles.composer} onSubmit={handleSubmit} noValidate>
      <div className={styles.composerHeader}>
        <div>
          <h2 className={styles.title}>Ask a Grounded Question</h2>
          <p className={styles.subtitle}>
            Answers are strictly cited against indexed PDF evidence. If evidence is absent, ProofLens explicitly abstains.
          </p>
        </div>
      </div>

      <div className={styles.inputGroup}>
        <textarea
          className={`${styles.textarea} ${
            validationError || isOverLimit ? styles.textareaError : ""
          }`}
          value={queryText}
          onChange={(e) => {
            setQueryText(e.target.value);
            if (validationError) setValidationError(null);
          }}
          onKeyDown={handleKeyDown}
          placeholder="e.g., What are the termination clauses under Section 8, and what notice period is required?"
          disabled={disabled || isSubmitting}
          aria-label="Query text"
          rows={3}
        />

        <div className={styles.metaRow}>
          {validationError ? (
            <p className={styles.errorMessage} role="alert">
              {validationError}
            </p>
          ) : (
            <p className={styles.hint}>
              Press <kbd>Ctrl+Enter</kbd> (or <kbd>⌘+Enter</kbd>) to ask
            </p>
          )}

          <span
            className={`${styles.charCounter} ${
              isOverLimit ? styles.charCounterExceeded : ""
            }`}
            aria-live="polite"
          >
            {charCount} / {MAX_QUERY_LENGTH}
          </span>
        </div>
      </div>

      <div className={styles.controlsRow}>
        <div className={styles.topKGroup}>
          <label htmlFor="topK-select" className={styles.topKLabel}>
            Retrieved Passages:
          </label>
          <select
            id="topK-select"
            className={styles.topKSelect}
            value={topK}
            onChange={(e) => setTopK(Number(e.target.value))}
            disabled={disabled || isSubmitting}
          >
            <option value={3}>Top 3</option>
            <option value={5}>Top 5 (Recommended)</option>
            <option value={8}>Top 8</option>
            <option value={10}>Top 10</option>
            <option value={15}>Top 15</option>
          </select>
        </div>

        <div className={styles.actions}>
          <button
            type="submit"
            className={styles.submitBtn}
            disabled={!isValid || isSubmitting || disabled}
          >
            {isSubmitting ? (
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
                <span>Retrieving & Grounding...</span>
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
                  <circle cx="11" cy="11" r="8" />
                  <line x1="21" y1="21" x2="16.65" y2="16.65" />
                </svg>
                <span>Ask Question</span>
              </>
            )}
          </button>
        </div>
      </div>
    </form>
  );
}
