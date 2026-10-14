/**
 * ProofLens AI — Document Ingestion & Evidence API Service
 * Implements upload with multi-file boundary validation, listing, retries, safe deletion,
 * authenticated PDF binary fetching, and chunk/page inspection.
 */

import { apiFetch, apiFetchBlob } from "./client";
import {
  DocumentChunkDetailResponse,
  DocumentPagesResponse,
  DocumentResponse,
  UploadBatchResponse,
  ProblemDetails,
} from "./types";

export const MAX_UPLOAD_FILES_PER_BATCH = 5;
export const MAX_UPLOAD_FILE_SIZE_BYTES = 10 * 1024 * 1024; // 10 MB

/**
 * Validate files client-side before sending to server.
 * Provides instant user feedback while treating server-side validation as authoritative.
 */
export function validateFilesForUpload(files: File[]): { valid: boolean; error?: string } {
  if (files.length === 0) {
    return { valid: false, error: "Please select at least one PDF file to upload." };
  }
  if (files.length > MAX_UPLOAD_FILES_PER_BATCH) {
    return {
      valid: false,
      error: `Maximum ${MAX_UPLOAD_FILES_PER_BATCH} files allowed per upload batch. You selected ${files.length}.`,
    };
  }
  for (const file of files) {
    if (file.size > MAX_UPLOAD_FILE_SIZE_BYTES) {
      return {
        valid: false,
        error: `File "${file.name}" exceeds the 10 MB size limit (${(file.size / (1024 * 1024)).toFixed(1)} MB).`,
      };
    }
    // PDF MIME or filename check
    if (!file.name.toLowerCase().endsWith(".pdf") && file.type !== "application/pdf") {
      return {
        valid: false,
        error: `File "${file.name}" is not a PDF. Only PDF files are supported.`,
      };
    }
  }
  return { valid: true };
}

export async function listDocuments(workspaceId: string): Promise<DocumentResponse[]> {
  return apiFetch<DocumentResponse[]>(`/api/v1/workspaces/${workspaceId}/documents`, {
    method: "GET",
  });
}

export async function getDocument(
  workspaceId: string,
  documentId: string
): Promise<DocumentResponse> {
  return apiFetch<DocumentResponse>(
    `/api/v1/workspaces/${workspaceId}/documents/${documentId}`,
    {
      method: "GET",
    }
  );
}

export async function uploadDocuments(
  workspaceId: string,
  files: File[]
): Promise<UploadBatchResponse> {
  const validation = validateFilesForUpload(files);
  if (!validation.valid) {
    const error: ProblemDetails = {
      error_code: "CLIENT_VALIDATION_ERROR",
      message: validation.error || "File validation failed.",
      status_code: 400,
    };
    throw error;
  }

  const formData = new FormData();
  for (const file of files) {
    formData.append("files", file);
  }

  return apiFetch<UploadBatchResponse>(
    `/api/v1/workspaces/${workspaceId}/documents/upload`,
    {
      method: "POST",
      body: formData,
    }
  );
}

export async function deleteDocument(
  workspaceId: string,
  documentId: string
): Promise<null> {
  return apiFetch<null>(
    `/api/v1/workspaces/${workspaceId}/documents/${documentId}`,
    {
      method: "DELETE",
    }
  );
}

export async function retryDocument(
  workspaceId: string,
  documentId: string
): Promise<DocumentResponse> {
  return apiFetch<DocumentResponse>(
    `/api/v1/workspaces/${workspaceId}/documents/${documentId}/retry`,
    {
      method: "POST",
    }
  );
}

export async function getDocumentFile(
  workspaceId: string,
  documentId: string
): Promise<Blob> {
  return apiFetchBlob(
    `/api/v1/workspaces/${workspaceId}/documents/${documentId}/file`,
    {
      method: "GET",
    }
  );
}

export async function getDocumentPages(
  workspaceId: string,
  documentId: string,
  pageNumber?: number
): Promise<DocumentPagesResponse> {
  const query = pageNumber ? `?page_number=${pageNumber}` : "";
  return apiFetch<DocumentPagesResponse>(
    `/api/v1/workspaces/${workspaceId}/documents/${documentId}/pages${query}`,
    {
      method: "GET",
    }
  );
}

export async function getDocumentChunk(
  workspaceId: string,
  documentId: string,
  chunkId: string
): Promise<DocumentChunkDetailResponse> {
  return apiFetch<DocumentChunkDetailResponse>(
    `/api/v1/workspaces/${workspaceId}/documents/${documentId}/chunks/${chunkId}`,
    {
      method: "GET",
    }
  );
}
