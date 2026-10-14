# ProofLens AI — Frontend API Integration Specification (`FRONTEND_API_INTEGRATION.md`)

**Document Version:** 1.0.0  
**Status:** Approved for Implementation  
**Backend Framework:** FastAPI `0.115.8` (AsyncIO + Pydantic v2 + SQLAlchemy 2.0)  
**Frontend Client:** TypeScript 5.x + Fetch API  
**Governing Documents:**  
- [PRD v0.1](file:///Users/apple/Documents/Projects/ProofLense-AI/ProofLens-AI-Project-Kickoff-PRD-v0.1.md)  
- [Operating Guidelines (`AGENTS.md`)](file:///Users/apple/Documents/Projects/ProofLense-AI/AGENTS.md)  
- [Backend Frontend-Handoff Report v1.1.0](file:///Users/apple/Documents/Projects/ProofLense-AI/docs/backend/FRONTEND_HANDOFF_REPORT.md)  
- [Frontend Requirements](file:///Users/apple/Documents/Projects/ProofLense-AI/docs/frontend/FRONTEND_REQUIREMENTS.md)  
- [Frontend Architecture](file:///Users/apple/Documents/Projects/ProofLense-AI/docs/frontend/FRONTEND_ARCHITECTURE.md)  

---

## 1. API Verification Status & Operation Inventory Reconciliation

### 1.1 Resolution of Operation Count Discrepancy
The previous backend handoff report (`FRONTEND_HANDOFF_REPORT.md` Section 2) contained a textual count stating *"21 endpoint operations across 18 unique paths"*.

A rigorous code-level audit of the FastAPI application routers (`main.py`, `health.py`, `workspaces.py`, `documents.py`, `queries.py`, and `comparisons.py`) reconciles this discrepancy:
- **Total Unique URL Paths:** **18**
- **Total Registered Endpoint Operations (Method + Path):** **23**

The discrepancy arose because the previous report's introductory sentence counted 21 operations prior to splitting chunk retrieval (`GET .../documents/{id}/chunks/{chunk_id}` and `GET .../chunks/{chunk_id}`) and adding pagination query listing endpoints. The complete, verified inventory contains **23 operations** as detailed in the matrix below.

### 1.2 Verification Levels Defined
- **Level 1: Code Verified:** The AST, route decorators, Pydantic schemas, and SQLAlchemy repositories have been directly inspected in the active codebase.
- **Level 2: Automated Test Verified:** The endpoint operation is covered by automated integration or unit tests executing in the continuous verification suite (214 passing tests).
- **Level 3: Live Infrastructure Verified:** Verified against live running cloud infrastructure (Render backend / Supabase PostgreSQL + pgvector).
- **Level 4: Unverified / Known Limitation:** Endpoint not exposed via HTTP, or functionality requires architectural mock/gap handling.

---

## 2. Exhaustive API Operation Inventory & Verification Matrix

| # | HTTP Method | Path Pattern | Summary & Purpose | Auth Header | Verification Level | Test Source File |
|---|---|---|---|---|---|---|
| **1** | `GET` | `/` | Root service metadata & environment info | None (Public) | Code & Test Verified | `test_health.py` |
| **2** | `GET` | `/health/live` | Process liveness probe | None (Public) | Code & Test Verified | `test_health.py` |
| **3** | `GET` | `/health/ready` | Database & pgvector connectivity probe | None (Public) | Code & Test Verified | `test_health.py` |
| **4** | `GET` | `/api/v1/auth-test` | Passkey gatekeeper verification diagnostic | `X-Workspace-Key` | Code & Test Verified | `test_security.py` |
| **5** | `POST` | `/api/v1/workspaces` | Create isolated workspace | `X-Workspace-Key` | Code & Test Verified | `test_workspaces_documents.py` |
| **6** | `GET` | `/api/v1/workspaces` | List all workspaces | `X-Workspace-Key` | Code & Test Verified | `test_workspaces_documents.py` |
| **7** | `GET` | `/api/v1/workspaces/{workspace_id}` | Retrieve specific workspace metadata | `X-Workspace-Key` | Code & Test Verified | `test_workspaces_documents.py` |
| **8** | `DELETE` | `/api/v1/workspaces/{workspace_id}` | Delete workspace & cascade database records | `X-Workspace-Key` | Code & Test Verified | `test_workspaces_documents.py` |
| **9** | `POST` | `/api/v1/workspaces/{workspace_id}/documents/upload` | Stream upload 1–5 PDFs ($\le 10\text{MB}$ each) | `X-Workspace-Key` | Code & Test Verified | `test_workspaces_documents.py` |
| **10** | `GET` | `/api/v1/workspaces/{workspace_id}/documents` | List documents & monitor ingestion status | `X-Workspace-Key` | Code & Test Verified | `test_workspaces_documents.py` |
| **11** | `GET` | `/api/v1/workspaces/{workspace_id}/documents/{document_id}` | Get document status & metadata | `X-Workspace-Key` | Code & Test Verified | `test_workspaces_documents.py` |
| **12** | `DELETE` | `/api/v1/workspaces/{workspace_id}/documents/{document_id}` | Safe two-step document deletion & file purge | `X-Workspace-Key` | Code & Test Verified | `test_workspaces_documents.py` |
| **13** | `POST` | `/api/v1/workspaces/{workspace_id}/documents/{document_id}/retry` | Manually retry failed document ingestion | `X-Workspace-Key` | Code & Test Verified | `test_document_ingestion_pipeline.py` |
| **14** | `GET` | `/api/v1/workspaces/{workspace_id}/documents/{document_id}/file` | Stream raw PDF binary for canvas viewer | `X-Workspace-Key` | Code & Test Verified | `test_document_endpoints_closure.py` |
| **15** | `GET` | `/api/v1/workspaces/{workspace_id}/documents/{document_id}/pages` | Inspect extracted pages & text chunks | `X-Workspace-Key` | Code & Test Verified | `test_document_endpoints_closure.py` |
| **16** | `GET` | `/api/v1/workspaces/{workspace_id}/documents/{document_id}/chunks/{chunk_id}` | Chunk inspection scoped to document | `X-Workspace-Key` | Code & Test Verified | `test_document_endpoints_closure.py` |
| **17** | `GET` | `/api/v1/workspaces/{workspace_id}/chunks/{chunk_id}` | Chunk inspection scoped to workspace | `X-Workspace-Key` | Code & Test Verified | `test_document_endpoints_closure.py` |
| **18** | `POST` | `/api/v1/workspaces/{workspace_id}/queries` | Execute grounded Q&A with citations | `X-Workspace-Key` | Code & Test Verified | `test_rag_pipeline.py` |
| **19** | `GET` | `/api/v1/workspaces/{workspace_id}/queries` | List historical Q&A queries (paginated) | `X-Workspace-Key` | Code & Test Verified | `test_query_endpoints_closure.py` |
| **20** | `GET` | `/api/v1/workspaces/{workspace_id}/queries/{query_run_id}` | Retrieve specific Q&A execution | `X-Workspace-Key` | Code & Test Verified | `test_query_endpoints_closure.py` |
| **21** | `POST` | `/api/v1/workspaces/{workspace_id}/comparisons` | Execute cross-document comparison | `X-Workspace-Key` | Code & Test Verified | `test_comparisons.py` |
| **22** | `GET` | `/api/v1/workspaces/{workspace_id}/comparisons` | List historical comparisons (paginated) | `X-Workspace-Key` | Code & Test Verified | `test_comparison_endpoints_closure.py` |
| **23** | `GET` | `/api/v1/workspaces/{workspace_id}/comparisons/{comparison_id}` | Retrieve specific comparison run | `X-Workspace-Key` | Code & Test Verified | `test_comparison_endpoints_closure.py` |

---

## 3. TypeScript Type Definitions & Data Contracts

These interfaces mirror the Pydantic v2 schemas defined in `backend/app/schemas/`:

```typescript
// ============================================================================
// 1. Common & Error Envelopes (RFC 7807)
// ============================================================================

export interface ProblemDetails {
  error_code: string;
  message: string;
  details: Record<string, unknown>;
  timestamp?: string;
  status_code?: number;
}

export interface ApiHealthResponse {
  status: "ready" | "alive";
  database?: "connected" | "disconnected";
  pgvector?: boolean;
}

// ============================================================================
// 2. Workspace Domain
// ============================================================================

export interface WorkspaceCreate {
  name: string; // 1 to 255 characters
}

export interface WorkspaceResponse {
  id: string; // UUIDv4
  name: string;
  created_at: string; // ISO 8601 UTC
  updated_at: string; // ISO 8601 UTC
}

// ============================================================================
// 3. Document Ingestion Domain
// ============================================================================

export type DocumentProcessingStatus = "pending" | "processing" | "ready" | "failed";

export interface DocumentResponse {
  id: string; // UUIDv4
  workspace_id: string; // UUIDv4
  filename: string;
  content_hash: string; // SHA-256 hex digest
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
  page_number: number | null; // 1-indexed physical page
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

// ============================================================================
// 4. Grounded Q&A Domain
// ============================================================================

export interface QueryRequest {
  query_text: string; // 1 to 2000 characters
  top_k?: number;     // 1 to 20, default 5
}

export interface CitationResponse {
  id: string; // UUIDv4
  chunk_id: string | null; // Nullable if cited document was deleted (Tombstone)
  document_id: string | null;
  document_filename: string;
  page_number: number; // 1-indexed
  quoted_snippet: string;
}

export interface RetrievedEvidenceResponse {
  chunk_id: string;
  document_id: string;
  document_filename: string;
  page_number: number;
  snippet: string;
  similarity_score: number; // Cosine similarity [0.0, 1.0]
  rank: number;
}

export interface QueryResponse {
  query_run_id: string;
  workspace_id: string;
  query_text: string;
  status: "completed" | "failed";
  answer_text: string;
  is_abstention: boolean;
  top_score: number | null;
  citations: CitationResponse[];
  retrieved_evidence: RetrievedEvidenceResponse[];
  created_at: string;
}

// ============================================================================
// 5. Cross-Document Comparison Domain
// ============================================================================

export interface ComparisonRequest {
  query_text: string; // 3 to 1000 characters
  document_ids?: string[]; // 2 to 5 UUIDs (optional; auto-selects ready docs if omitted)
}

export interface PerDocumentEvidenceResponse {
  document_id: string;
  document_filename: string;
  statement: string;
  citations: CitationResponse[];
}

export type FindingClassification = "agreement" | "contradiction" | "difference" | "not_found";

export interface ComparisonFindingResponse {
  finding_type: FindingClassification;
  topic: string;
  summary: string;
  per_document_evidence: PerDocumentEvidenceResponse[];
  citations: CitationResponse[];
}

export interface ComparisonResponse {
  comparison_id: string;
  workspace_id: string;
  query_text: string;
  document_ids: string[];
  status: "completed" | "failed";
  is_abstention: boolean;
  findings: ComparisonFindingResponse[];
  synthesis: string;
  limitations: string | null;
  retrieved_evidence: RetrievedEvidenceResponse[];
  created_at: string;
}

export interface SavedComparisonResponse {
  comparison_id: string;
  workspace_id: string;
  query_text: string;
  status: "completed" | "failed";
  is_abstention: boolean;
  top_score: number | null;
  synthesis: string;
  citations: CitationResponse[];
  retrieved_evidence: RetrievedEvidenceResponse[];
  created_at: string;
}
```

---

## 4. Authentication & Passkey Handling Protocol

### 4.1 Header Injection Mechanism
All requests to `/api/v1/*` (excluding `/` and `/health/*`) must include the HTTP header:
```http
X-Workspace-Key: <user_configured_passkey>
```

### 4.2 API Client Interceptor Implementation (`lib/api/client.ts`)
```typescript
import { getStoredPasskey } from "@/lib/auth/passkey";
import { ProblemDetails } from "@/lib/api/types";

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const passkey = getStoredPasskey();
  const headers = new Headers(options.headers || {});

  if (passkey) {
    headers.set("X-Workspace-Key", passkey);
  }

  // Only set Content-Type to JSON if not sending FormData
  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorDetails: ProblemDetails;
    try {
      errorDetails = await response.json();
    } catch {
      errorDetails = {
        error_code: "HTTP_ERROR",
        message: `HTTP ${response.status} ${response.statusText}`,
        details: {},
        status_code: response.status,
      };
    }

    if (response.status === 401) {
      // Dispatches custom event to trigger PasskeyModal
      window.dispatchEvent(new CustomEvent("prooflens:unauthorized"));
    }

    throw errorDetails;
  }

  if (response.status === 204) {
    return null as T;
  }

  return response.json() as Promise<T>;
}
```

---

## 5. Ingestion Polling Protocol & State Machine

```
[Upload Submitted]
       |
       v
[Status: "pending"] <-------------------+
       |                                |
       | (Worker claims document)       | (Poll interval: 2000ms)
       v                                |
[Status: "processing"] -----------------+
       |
       +--------------------------------+
       |                                |
       v (Success)                      v (Error / Timeout)
[Status: "ready"]               [Status: "failed"]
(Stop Polling)                  (Stop Polling)
                                        |
                                        | (User clicks "Retry")
                                        v
                                [POST .../retry]
                                        |
                                        v
                                [Status: "processing"] (Resume Polling)
```

### Polling Hook Implementation Rules
1. **Interval:** Fixed 2,000 milliseconds.
2. **Endpoint:** `GET /api/v1/workspaces/{workspace_id}/documents`.
3. **Termination Condition:** Terminates when every document in the array has `status === "ready"` or `status === "failed"`.
4. **Window Inactive Handling:** When the browser tab is hidden (`document.visibilityState === "hidden"`), pause polling to conserve client CPU and backend network cycles. Resume immediately upon tab focus.

---

## 6. Authenticated PDF Binary Delivery & Rendering Protocol

### 6.1 Binary Fetch (`lib/api/documents.ts`)
```typescript
export async function fetchDocumentPdfBlob(
  workspaceId: string,
  documentId: string
): Promise<Blob> {
  const passkey = getStoredPasskey();
  const res = await fetch(
    `${BASE_URL}/api/v1/workspaces/${workspaceId}/documents/${documentId}/file`,
    {
      headers: {
        "X-Workspace-Key": passkey || "",
      },
    }
  );

  if (!res.ok) {
    throw new Error(`Failed to stream PDF binary: HTTP ${res.status}`);
  }

  return await res.blob();
}
```

### 6.2 Citation Click Navigation Protocol
1. User clicks footnote tag or citation chip referencing Document `D`, Page `P`, and Snippet `S`.
2. UI updates route to:
   `/workspaces/[workspaceId]/documents/[documentId]?page=[pageNumber]&chunk=[chunkId]`
3. `AuthenticatedPdfViewer` receives `page` parameter, renders Page `P` using PDF.js.
4. `TextHighlightLayer` scans rendered DOM text layer nodes on page `P`.
5. Matches `quoted_snippet` substring, wraps matched range with `.evidence-highlight` CSS class, and invokes `element.scrollIntoView({ behavior: 'smooth', block: 'center' })`.

---

## 7. Explicit Labels for Unresolved or Unverified Contracts

The following capabilities must be explicitly understood by frontend engineering as architectural boundaries:

| Feature / Domain | Current Contract Reality | Frontend Engineering Directive |
|---|---|---|
| **Evaluation Endpoint** | **No HTTP Route Registered.** Evaluation logic resides in `backend/app/services/evaluation/` and executes via CLI commands (`pytest backend/tests/eval/`). | Do NOT invent a fake `POST /api/v1/evaluations` endpoint. Screen `/evaluation` displays static benchmark dataset fixtures and provides the copyable CLI command. |
| **PDF Bounding Boxes** | **No Coordinates Available.** Backend extracts page-level text via `pypdf`, providing `page_number` and text snippets. Geometric `[x0, y0, x1, y1]` coordinates are not extracted. | Do NOT promise or attempt geometric SVG/canvas polygon overlays. Rely strictly on physical page navigation and DOM text matching. |
| **User Accounts / Multi-Tenant Auth** | **Single Passkey Only.** Authentication uses single `X-Workspace-Key`. No JWT, sessions, OAuth, or user table exists in the backend. | Do NOT build login/signup or user profile screens. Implement only the `PasskeyModal` gatekeeper. |
| **Physical File Deletion on Workspace Purge** | Relational cascade cleans up DB rows. On `local` storage backend, files in `./data/uploads` remain as non-blocking technical debt (TD-01). | Frontend simply calls `DELETE /workspaces/{id}` and updates workspace list UI on `204 No Content`. |
