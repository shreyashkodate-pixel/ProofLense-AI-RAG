"use client";

import React, { useState, useRef } from "react";
import { UploadCloud, FileText, X, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/Button";
import {
  uploadDocuments,
  validateFilesForUpload,
  MAX_UPLOAD_FILES_PER_BATCH,
} from "@/lib/api/documents";
import { UploadBatchResponse, ProblemDetails } from "@/lib/api/types";
import styles from "./UploadDropzone.module.css";

export interface UploadDropzoneProps {
  workspaceId: string;
  onUploadSuccess: (batch: UploadBatchResponse) => void;
  disabled?: boolean;
}

export const UploadDropzone: React.FC<UploadDropzoneProps> = ({
  workspaceId,
  onUploadSuccess,
  disabled = false,
}) => {
  const [isDragActive, setIsDragActive] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const handleFilesChosen = (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setErrorMessage(null);

    const incoming = Array.from(files);
    const combined = [...selectedFiles, ...incoming];

    // Validate incoming batch
    const validation = validateFilesForUpload(combined);
    if (!validation.valid) {
      setErrorMessage(validation.error || "Invalid file selection.");
      return;
    }

    setSelectedFiles(combined);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    if (disabled || isUploading) return;
    setIsDragActive(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragActive(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragActive(false);
    if (disabled || isUploading) return;
    handleFilesChosen(e.dataTransfer.files);
  };

  const removeFile = (index: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
    setErrorMessage(null);
  };

  const handleUploadSubmit = async () => {
    if (selectedFiles.length === 0) return;

    setIsUploading(true);
    setErrorMessage(null);

    try {
      const batch = await uploadDocuments(workspaceId, selectedFiles);
      setSelectedFiles([]);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
      onUploadSuccess(batch);
    } catch (err: unknown) {
      const problem = err as ProblemDetails;
      setErrorMessage(
        problem.message || "Failed to upload document. Please check the backend service."
      );
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
      <div
        className={`${styles.dropzone} ${isDragActive ? styles.dropzoneActive : ""} ${
          disabled || isUploading ? styles.dropzoneDisabled : ""
        }`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !disabled && !isUploading && fileInputRef.current?.click()}
        role="button"
        tabIndex={disabled || isUploading ? -1 : 0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            fileInputRef.current?.click();
          }
        }}
        aria-label="Upload PDF documents"
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="application/pdf,.pdf"
          multiple
          className={styles.hiddenInput}
          onChange={(e) => handleFilesChosen(e.target.files)}
          disabled={disabled || isUploading}
        />
        <UploadCloud size={36} className={styles.icon} />
        <div>
          <div className={styles.title}>Click or drag PDF documents here to upload</div>
          <div className={styles.subtitle}>
            Up to {MAX_UPLOAD_FILES_PER_BATCH} PDFs per batch • Maximum 10 MB each • Untrusted content sanitized
          </div>
        </div>
      </div>

      {errorMessage && (
        <div className={styles.errorBanner} role="alert">
          <AlertCircle size={16} />
          <span>{errorMessage}</span>
        </div>
      )}

      {selectedFiles.length > 0 && (
        <div>
          <div className={styles.fileList}>
            {selectedFiles.map((file, idx) => (
              <div key={`${file.name}-${idx}`} className={styles.fileItem}>
                <div className={styles.fileInfo}>
                  <FileText size={16} style={{ color: "var(--color-accent)", flexShrink: 0 }} />
                  <span className={styles.fileName} title={file.name}>
                    {file.name}
                  </span>
                  <span className={styles.fileSize}>
                    ({(file.size / (1024 * 1024)).toFixed(2)} MB)
                  </span>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    removeFile(idx);
                  }}
                  disabled={isUploading}
                  title="Remove file"
                  style={{ padding: "var(--space-1)" }}
                >
                  <X size={14} />
                </Button>
              </div>
            ))}
          </div>

          <div className={styles.uploadActions}>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                setSelectedFiles([]);
                setErrorMessage(null);
                if (fileInputRef.current) fileInputRef.current.value = "";
              }}
              disabled={isUploading}
            >
              Clear Selection
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={handleUploadSubmit}
              isLoading={isUploading}
              leftIcon={<UploadCloud size={14} />}
            >
              Upload {selectedFiles.length} {selectedFiles.length === 1 ? "File" : "Files"}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
};
