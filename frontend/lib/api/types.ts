/**
 * ProofLens AI — Canonical Frontend TypeScript API Contracts
 * Strictly mirroring backend Pydantic v2 schemas and RFC 7807 Error Envelopes.
 */

// ----------------------------------------------------------------------------
// 1. Error & Diagnostics
// ----------------------------------------------------------------------------

export interface ProblemDetails {
  error_code: string;
  message: string;
  details?: Record<string, unknown>;
  status_code?: number;
}

export interface AuthTestResponse {
  authenticated: boolean;
  message: string;
}

export interface ApiHealthResponse {
  status: "ready" | "alive";
  database?: "connected" | "disconnected";
  pgvector?: boolean;
}

// ----------------------------------------------------------------------------
// 2. Workspace Domain
// ----------------------------------------------------------------------------

export interface WorkspaceCreate {
  name: string; // 1 to 255 chars
}

export interface WorkspaceResponse {
  id: string; // UUIDv4
  name: string;
  created_at: string;
  updated_at: string;
}

// ----------------------------------------------------------------------------
// 3. Document Ingestion Domain
// ----------------------------------------------------------------------------

export type DocumentProcessingStatus = "pending" | "processing" | "ready" | "failed";

export interface DocumentResponse {
  id: string; // UUIDv4
  workspace_id: string; // UUIDv4
  filename: string;
  content_hash: string;
  file_size_bytes: number;
  page_count: number | null;
  status: DocumentProcessingStatus;
  error_message: string | null;
  processing_attempts: number;
  processing_started_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface UploadBatchResponse {
  uploaded: DocumentResponse[];
  total_uploaded: number;
}

export interface DocumentChunkDetailResponse {
  id: string; // UUIDv4
  document_id: string; // UUIDv4
  page_id: string; // UUIDv4
  chunk_index: number;
  chunk_text: string;
  token_count: number | null;
  page_number: number | null; // 1-indexed
}

export interface DocumentPageDetailResponse {
  id: string; // UUIDv4
  document_id: string; // UUIDv4
  page_number: number; // 1-indexed
  raw_text: string;
  char_count: number;
  chunks: DocumentChunkDetailResponse[];
}

export interface DocumentPagesResponse {
  document_id: string;
  workspace_id: string;
  total_pages: number;
  pages: DocumentPageDetailResponse[];
}

// ----------------------------------------------------------------------------
// 4. Citation & Evidence Inspection Domain
// ----------------------------------------------------------------------------

export interface CitationResponse {
  id: string; // UUIDv4
  chunk_id: string | null; // Nullable when source chunk tombstoned
  document_id: string | null; // Nullable when tombstoned
  document_filename: string;
  page_number: number; // 1-indexed
  quoted_snippet: string;
}

export interface RetrievedEvidenceResponse {
  chunk_id: string; // UUIDv4
  document_id: string; // UUIDv4
  document_filename: string;
  page_number: number; // 1-indexed
  snippet: string;
  similarity_score: number;
  rank: number;
}

// ----------------------------------------------------------------------------
// 5. Grounded Q&A Domain (Phase 5)
// ----------------------------------------------------------------------------

export interface QueryRequest {
  query_text: string; // 1 to 2000 chars
  top_k?: number; // 1 to 20
}

export interface QueryResponse {
  query_run_id: string; // UUIDv4
  workspace_id: string; // UUIDv4
  query_text: string;
  status: "completed" | "failed";
  answer_text: string;
  is_abstention: boolean;
  top_score: number | null;
  citations: CitationResponse[];
  retrieved_evidence: RetrievedEvidenceResponse[];
  created_at: string;
}

// ----------------------------------------------------------------------------
// 6. Cross-Document Comparison Domain (Phase 6)
// ----------------------------------------------------------------------------

export type ComparisonFindingType =
  | "agreement"
  | "contradiction"
  | "difference"
  | "not_found"
  | "insufficient_evidence";

export interface ComparisonRequest {
  query_text: string; // 3 to 1000 chars
  document_ids?: string[]; // Optional specific docs (min 2, max 5)
}

export interface PerDocumentEvidenceResponse {
  document_id: string;
  document_filename: string;
  statement: string;
  citations: CitationResponse[];
}

export interface ComparisonFindingResponse {
  finding_type: ComparisonFindingType;
  topic: string;
  summary: string;
  per_document_evidence: PerDocumentEvidenceResponse[];
  citations: CitationResponse[];
}

export interface ComparisonResponse {
  comparison_id: string; // UUIDv4
  workspace_id: string; // UUIDv4
  query_text: string;
  document_ids: string[];
  status: "completed" | "insufficient_evidence";
  is_abstention: boolean;
  findings: ComparisonFindingResponse[];
  synthesis: string;
  limitations: string | null;
  retrieved_evidence: RetrievedEvidenceResponse[];
  created_at: string;
}

export interface SavedComparisonResponse {
  comparison_id: string; // UUIDv4
  workspace_id: string; // UUIDv4
  query_text: string;
  status: "completed" | "insufficient_evidence";
  is_abstention: boolean;
  top_score: number | null;
  synthesis: string;
  citations: CitationResponse[];
  retrieved_evidence: RetrievedEvidenceResponse[];
  created_at: string;
}
