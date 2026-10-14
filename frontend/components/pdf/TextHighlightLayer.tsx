"use client";

import React, { useMemo } from "react";
import { CheckCircle2, AlertCircle, HelpCircle } from "lucide-react";
import styles from "./TextHighlightLayer.module.css";

export interface TextMatchResult {
  matchStatus: "exact" | "approximate" | "unmatched" | "none";
  confidence: number;
}

/**
 * Honest Evidence Matcher
 * Strictly searches normalized text extracted from the current PDF page against the cited snippet.
 * Never fabricates bounding box coordinates or canvas rectangles.
 */
export function matchSnippetInPageText(
  pageText: string,
  targetSnippet?: string | null
): TextMatchResult {
  if (!targetSnippet || !targetSnippet.trim()) {
    return { matchStatus: "none", confidence: 0 };
  }

  const normalize = (text: string) =>
    text.toLowerCase().replace(/\s+/g, " ").trim();

  const normPage = normalize(pageText);
  const normSnippet = normalize(targetSnippet);

  if (!normPage || !normSnippet) {
    return { matchStatus: "none", confidence: 0 };
  }

  // Exact normalized match
  if (normPage.includes(normSnippet)) {
    return { matchStatus: "exact", confidence: 1.0 };
  }

  // Token-level subsequence match for approximate verification
  const cleanWord = (w: string) => w.replace(/[.,;:!?()"']/g, "");
  const snippetWords = normSnippet
    .split(" ")
    .map(cleanWord)
    .filter((w) => w.length > 2);
  if (snippetWords.length > 2) {
    const matchedCount = snippetWords.filter((w) => normPage.includes(w)).length;
    const ratio = matchedCount / snippetWords.length;
    if (ratio >= 0.7) {
      return { matchStatus: "approximate", confidence: ratio };
    }
  }

  return { matchStatus: "unmatched", confidence: 0 };
}

export interface TextHighlightLayerProps {
  pageNumber: number;
  pageText: string;
  targetSnippet?: string | null;
  onClearSnippet?: () => void;
}

export const TextHighlightLayer: React.FC<TextHighlightLayerProps> = ({
  pageNumber,
  pageText,
  targetSnippet,
  onClearSnippet,
}) => {
  const matchResult = useMemo(
    () => matchSnippetInPageText(pageText, targetSnippet),
    [pageText, targetSnippet]
  );

  if (!targetSnippet || matchResult.matchStatus === "none") {
    return null;
  }

  return (
    <div className={styles.container} role="region" aria-label="Evidence citation inspection">
      <div className={styles.header}>
        {matchResult.matchStatus === "exact" && (
          <div className={`${styles.statusBadge} ${styles.statusExact}`}>
            <CheckCircle2 size={14} />
            <span>Exact Text Match Verified on Page {pageNumber}</span>
          </div>
        )}
        {matchResult.matchStatus === "approximate" && (
          <div className={`${styles.statusBadge} ${styles.statusApproximate}`}>
            <AlertCircle size={14} />
            <span>Approximate Text Match ({Math.round(matchResult.confidence * 100)}%) on Page {pageNumber}</span>
          </div>
        )}
        {matchResult.matchStatus === "unmatched" && (
          <div className={`${styles.statusBadge} ${styles.statusUnmatched}`}>
            <HelpCircle size={14} />
            <span>Navigated to Cited Page {pageNumber} (Text layer match unverified)</span>
          </div>
        )}

        {onClearSnippet && (
          <button
            type="button"
            className={styles.clearBtn}
            onClick={onClearSnippet}
            aria-label="Clear active snippet highlight"
          >
            Clear
          </button>
        )}
      </div>

      <div className={styles.snippetBox}>
        <div className={styles.snippetLabel}>Quoted Evidence Snippet:</div>
        <blockquote className={styles.snippetText}>
          &ldquo;{targetSnippet}&rdquo;
        </blockquote>
      </div>
    </div>
  );
};
