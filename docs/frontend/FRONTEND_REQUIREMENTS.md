# ProofLens AI — Frontend Requirements Specification (`FRONTEND_REQUIREMENTS.md`)

**Document Version:** 1.0.0  
**Status:** Approved for Implementation Planning  
**Target Milestone:** Frontend Phases 1–7 (Next.js 15 App Router + TypeScript)  
**Governing Documents:**  
- [PRD v0.1](file:///Users/apple/Documents/Projects/ProofLense-AI/ProofLens-AI-Project-Kickoff-PRD-v0.1.md) (Authoritative Functional Requirements FR-01 through FR-09)  
- [Operating Guidelines (`AGENTS.md`)](file:///Users/apple/Documents/Projects/ProofLense-AI/AGENTS.md)  
- [Technical Design](file:///Users/apple/Documents/Projects/ProofLense-AI/docs/TECHNICAL-DESIGN.md)  
- [Backend Frontend-Handoff Report v1.1.0](file:///Users/apple/Documents/Projects/ProofLense-AI/docs/backend/FRONTEND_HANDOFF_REPORT.md)  
- [Frontend Design Tokens](file:///Users/apple/Documents/Projects/ProofLense-AI/docs/frontend/FRONTEND_DESIGN_TOKENS.md)  
- [Frontend Design System](file:///Users/apple/Documents/Projects/ProofLense-AI/docs/frontend/FRONTEND_DESIGN_SYSTEM.md)  

---

## 1. Executive Summary & Product Scope

ProofLens AI is an **evidence-first document intelligence platform** engineered for knowledge workers, due-diligence analysts, and audit teams. The platform ingests PDF collections, performs semantic retrieval over page-bounded text chunks, synthesizes answers grounded strictly in retrieved evidence with verifiable page-level citations, coordinates cross-document comparative analysis, and explicitly abstains when evidence is absent or insufficient.

The frontend is a **Next.js 15 (App Router) + TypeScript** single-page web application communicating with the FastAPI backend. It adheres strictly to the approved PRD scope and the calm, high-contrast enterprise design system defined in `FRONTEND_DESIGN_TOKENS.md` and `FRONTEND_DESIGN_SYSTEM.md`.

### Core Architectural Invariants
1. **Evidence First:** Answers, citations, source excerpts, and source documents are visually distinct and always traceable back to physical pages.
2. **Explicit Abstention:** If document evidence is missing or low-confidence, the UI displays an explicit abstention state rather than speculative synthesis.
3. **Zero Secret Exposure:** Backend secrets (`GEMINI_API_KEY`, database credentials, Supabase service keys) never reach the client bundle. Single-passkey gatekeeping is managed via `X-Workspace-Key` in memory/`sessionStorage`.
4. **Honest Highlighting:** Citations provide 1-indexed page numbers and quoted snippets, but **not geometric PDF bounding-box coordinates**. Highlighting is implemented via client-side text matching; the UI never fabricates geometric overlays.

---

## 2. Approved Features Breakdown

### 2.1 Workspace Isolation & Access Management (PRD FR-01)
- **FR-01.1 Passkey Gatekeeper:** Application-level access protection requiring a valid `X-Workspace-Key` header on all API transactions (except public health probes). The frontend prompts for this passkey upon initial entry and securely injects it into all outbound requests.
- **FR-01.2 Workspace Creation:** Users create isolated workspaces with custom names (1–255 characters).
- **FR-01.3 Workspace Listing & Switching:** Fast switching between workspaces. Active workspace context persists in the route URL (`/workspaces/[workspaceId]`).
- **FR-01.4 Workspace Cascade Deletion:** Users can delete a workspace with an explicit confirmation dialog. All contained documents, pages, chunks, queries, and citations are removed.

### 2.2 Document Ingestion & Status Tracking (PRD FR-02, FR-03, FR-09)
- **FR-02.1 Multi-File Drag & Drop Upload:** Batch upload accepting 1 to 5 PDF files simultaneously (`multipart/form-data`).
- **FR-02.2 Client-Side Pre-Validation:**
  - File count $\le 5$ files per batch.
  - File size $\le 10\text{ MB}$ ($10,485,760\text{ bytes}$) per file.
  - MIME type check (`application/pdf`) and magic byte header pre-check (`%PDF-`).
- **FR-02.3 Asynchronous Processing State Machine:** Display real-time lifecycle status badges:
  - `pending`: Uploaded to storage, queued for processing.
  - `processing`: Worker has claimed document; parsing pages, chunking, generating embeddings.
  - `ready`: Parsing and 768-dim vector embedding complete; available for Q&A and comparisons.
  - `failed`: Ingestion error recorded with actionable, sanitized error message.
- **FR-02.4 Ingestion Polling Engine:** Background polling (`GET /api/v1/workspaces/{id}/documents`) active at 2-second intervals while any document is in `pending` or `processing` status. Polling stops automatically when all documents reach a terminal state (`ready` or `failed`).
- **FR-02.5 Manual Retry Action:** One-click retry trigger for failed documents (`POST .../retry`), transitioning status back to `processing`.
- **FR-02.6 Safe Deletion Protocol:** Document deletion with confirmation dialog (`DELETE .../documents/{id}`). Relational cascades clean up pages and chunks, while existing citations snapshot data is preserved as tombstoned references.
- **FR-02.7 Duplicate Hash Rejection:** Surface `409 Conflict` (`DUPLICATE_DOCUMENT`) with user-friendly guidance if an identical document is uploaded twice within the same workspace.

### 2.3 Evidence-Grounded Q&A Console (PRD FR-04, FR-05, FR-06)
- **FR-04.1 Natural Language Query Composer:** Clean query input (1 to 2,000 characters) with optional `top_k` selector (default 5, range 1–20).
- **FR-04.2 Grounded Answer Presentation:** Clear typographic separation between AI-synthesized narrative and cited source evidence. Footnote chips (`[1]`, `[2]`) embedded directly in narrative text.
- **FR-04.3 Server-Authoritative Citations:** Rendered citation cards displaying:
  - Document filename and document ID.
  - 1-indexed physical page number.
  - Verifiable `quoted_snippet` extracted verbatim from document chunk.
- **FR-04.4 Candidate Evidence Drawer:** Collapsible inspection drawer displaying all retrieved evidence chunks, their cosine similarity scores (e.g., `0.8421`), retrieval rank, and page numbers.
- **FR-04.5 Explicit Abstention UI Banner:** Distinct warning/notice card rendered when `is_abstention: true` (tripped when `top_score < 0.65` or when vector retrieval yields no relevant passages). Clear message: *"I do not have sufficient document evidence in this workspace to answer your question."* Zero hallucinations or fabricated citations.
- **FR-04.6 Historical Queries Sidebar:** Paginated list of previous grounded Q&A runs (`GET .../queries`), permitting instant recall and review of historical questions, answers, and citations.

### 2.4 Evidence & Authenticated PDF Document Viewer (PRD FR-06)
- **FR-06.1 Authenticated Binary PDF Delivery:** Client-side authenticated binary retrieval (`GET .../documents/{id}/file` with `X-Workspace-Key`) rendered via client-side canvas (PDF.js).
- **FR-06.2 Synchronized Page Navigation:** Navigating to a citation immediately jumps the viewer to the exact physical page number (`page_number`).
- **FR-06.3 Text Highlighting & Snippet Search:** Client-side text layer searches for the citation's `quoted_snippet` on the active page and applies visual highlight styling (`--color-evidence-highlight`).
- **FR-06.4 Extracted Pages & Chunks Inspector:** Side-by-side drawer displaying raw extracted text and page-bounded chunk segments (`GET .../pages`), allowing full verification of OCR-less text extraction.
- **FR-06.5 Tombstone Citation Resilience:** If a cited document or chunk was deleted, the citation remains viewable with its historical snapshot snippet, page number, and a *"Source document no longer active"* badge.

### 2.5 Cross-Document Comparison Studio (PRD FR-07)
- **FR-07.1 Document Selection:** Multi-document selector supporting 2 to 5 `ready` documents.
- **FR-07.2 Comparative Topic Query:** Prompt input (3 to 1,000 characters) specifying the comparison topic, metric, or contract clause.
- **FR-07.3 Structured Finding Matrix:** Display findings categorized with distinct semantic tags:
  - `agreement` (Success green token)
  - `contradiction` (Danger red token)
  - `difference` (Warning amber token)
  - `not_found` (Muted gray token)
- **FR-07.4 Per-Document Evidence Breakdown:** Each finding displays the specific statement made by each document along with verifiable page-level citations.
- **FR-07.5 Comparative Synthesis & Limitations Banner:** Executive comparative summary followed by an explicit limitations callout highlighting scoping mismatches or incomparable definitions.
- **FR-07.6 Historical Comparisons Sidebar:** Listing of previous comparison runs (`GET .../comparisons`) with timestamp and query topic.

### 2.6 Evaluation & Benchmark Demonstration (PRD FR-08)
- **FR-08.1 Curated Test Benchmark Viewer:** Read-only interface displaying the version-controlled evaluation dataset (test questions, expected documents/pages, ground-truth characteristics).
- **FR-08.2 Target Metrics Summary:** Display of benchmark metrics:
  - Retrieval hit rate ($>85\%$).
  - Citation validity ($100\%$ server-authoritative).
  - Abstention correctness on out-of-domain / unanswerable queries ($100\%$).
- **FR-08.3 Model-Judged Labeling:** Explicit visual tag indicating that qualitative scores are model-judged metrics, not human ground truth.
- **FR-08.4 Repeatable Command Documentation:** Copyable CLI command instructions for executing the automated eval suite (`pytest backend/tests/eval/`).

---

## 3. Approved Screen Map & Routing Architecture

```
/                                             # Route 1: Workspace Hub & Passkey Gate
/workspaces/[workspaceId]                     # Route 2: Workspace Dashboard & Overview
/workspaces/[workspaceId]/documents           # Route 3: Document Library & Ingestion
/workspaces/[workspaceId]/documents/[docId]   # Route 4: PDF Viewer & Evidence Inspector
/workspaces/[workspaceId]/queries             # Route 5: Grounded Q&A Console
/workspaces/[workspaceId]/compare             # Route 6: Cross-Document Comparison Studio
/evaluation                                   # Route 7: Curated Benchmark & Evaluation View
```

### Screen Details & Layout Structures

| Screen Route | Layout Type | Primary Components | Governing PRD FR |
|---|---|---|---|
| `/` | Centered Modal / Grid | `PasskeyModal`, `WorkspaceGrid`, `WorkspaceCreateDialog` | FR-01 |
| `/workspaces/[workspaceId]` | 2-Column Shell | `WorkspaceHeader`, `StatsCards`, `RecentQueriesList`, `QuickActionCards` | FR-01, FR-02 |
| `.../documents` | 2-Column (Library + Upload) | `DocumentTable`, `StatusBadge`, `UploadDropzone`, `DeleteDialog` | FR-02, FR-03, FR-09 |
| `.../documents/[docId]` | Split-Pane (PDF + Text) | `AuthenticatedPdfViewer`, `PageNavigator`, `ChunkDrawer`, `TextMatchHighlighter` | FR-06 |
| `.../queries` | 2-Column (Chat + Evidence) | `QueryComposer`, `AnswerCard`, `CitationChips`, `EvidenceDrawer`, `HistorySidebar` | FR-04, FR-05, FR-06 |
| `.../compare` | Multi-Pane Matrix | `DocSelector`, `TopicComposer`, `FindingMatrix`, `LimitationsBanner`, `CompareHistory` | FR-07 |
| `/evaluation` | Full-Width Table / Cards | `MetricsOverview`, `BenchmarkDatasetTable`, `CliCommandRunnerCard` | FR-08 |

---

## 4. User Flows & Interaction State Machine

### 4.1 Flow 1: Authentication & Workspace Initialization
1. User navigates to `/`.
2. System checks `sessionStorage` for `X-Workspace-Key`. If absent, renders `PasskeyModal`.
3. User enters passkey. Frontend issues `GET /api/v1/auth-test`.
   - On `200 OK`: Passkey stored in memory/`sessionStorage`; renders workspace grid.
   - On `401 Unauthorized`: Displays inline error: *"Invalid access passkey. Please check server configuration."*
4. User selects an existing workspace or clicks *"New Workspace"*, entering a name.
5. Frontend calls `POST /api/v1/workspaces`. On `201 Created`, user is redirected to `/workspaces/[workspaceId]`.

### 4.2 Flow 2: Document Ingestion & Status Tracking
1. User navigates to `/workspaces/[workspaceId]/documents`.
2. User drags 1–5 PDF files into `UploadDropzone`.
3. Client validates: batch size $\le 5$, file size $\le 10\text{ MB}$, `%PDF-` header.
4. User clicks *"Upload & Ingest"*. Frontend posts multipart payload to `POST .../documents/upload`.
5. Backend returns `201 Created` with documents in `pending` state.
6. Frontend activates `IngestionPoller` interval (every 2,000ms):
   - Polls `GET .../documents`.
   - Updates status pill: `pending` (amber) $\rightarrow$ `processing` (blue with spinner) $\rightarrow$ `ready` (forest green) or `failed` (danger red).
   - Polling terminates when no documents remain in `pending` or `processing`.
7. If a document enters `failed` status, user can click *"Retry Ingestion"* (`POST .../retry`), which atomically reclaims the worker and restarts polling.

### 4.3 Flow 3: Grounded Q&A & Evidence Deep-Linking
1. User opens `/workspaces/[workspaceId]/queries`.
2. User types a query into `QueryComposer` and submits.
3. System renders loading skeleton with calm indeterminate progress bar.
4. Backend executes vector search and grounded synthesis, returning `QueryResponse`:
   - **Scenario A (Evidence Found):** Renders synthesized narrative with footnotes `[1]`, `[2]`. Renders citation cards below.
   - **Scenario B (Insufficient Evidence / Low Score):** Renders abstention notice banner: *"I do not have sufficient document evidence in this workspace to answer your question."* Top score displayed if available; citations empty.
5. User clicks Citation `[1]`.
6. Viewer action: Navigates to `/workspaces/[workspaceId]/documents/[docId]?page=4&chunk=[chunkId]`.
7. PDF Viewer fetches binary using `X-Workspace-Key`, renders page 4, highlights `quoted_snippet` in text layer, and opens Chunk Detail drawer.

### 4.4 Flow 4: Cross-Document Comparative Analysis
1. User navigates to `/workspaces/[workspaceId]/compare`.
2. User checks 2 to 5 documents from the `ready` document list.
3. User inputs comparison query (e.g., *"Compare reported Q3 revenue and operating margin guidance."*).
4. System submits `POST .../comparisons`.
5. Frontend renders:
   - Synthesis narrative card.
   - Limitations banner (if definitions diverge).
   - Findings grid: each card features finding badge (`contradiction`, `agreement`, `difference`, `not_found`), topic heading, summary, and per-document statements with clickable citation tags.

---

## 5. UI State Matrix

Every view and component must explicitly implement each state in the table below:

| UI State | Visual Treatment | User Action Available |
|---|---|---|
| **Empty State** | Clean ivory canvas with muted illustration, explanatory headline, and primary action button (e.g., *"Upload your first PDF"*). | Create workspace / Upload files / New query |
| **Loading State** | Subtle skeleton placeholders matching card/text geometry; no bouncing AI orbs or neon spinners. Buttons show spinner and `aria-busy="true"`. | Cancel request (where applicable) |
| **Processing State** | Pulsing neutral indicator badge with live elapsed time or status step label (`"Chunking & embedding..."`). | Retry button enabled if elapsed > 120s |
| **Success State** | High-contrast text, structured cards, citation tags with sharp borders, verified badges. | Copy text / Inspect citation / Export findings |
| **Abstention State** | Calm amber/neutral container (`--color-warning-soft`), clear abstention icon, explanation that retrieved passages did not satisfy confidence threshold. | Rephrase query / Upload additional documents |
| **Recoverable Error** | Semantic danger banner (`--color-danger-soft`) with RFC 7807 error code, sanitized message, and retry button. | *"Try Again"* or dismiss |
| **Unrecoverable Error** | Full-width fallback screen with error ID, suggestion to verify connection or passkey, and link back to Workspace Hub. | Return to `/` |

---

## 6. Acceptance Criteria (AC)

- **AC-01 Workspace Security:** The frontend must never send API requests without the `X-Workspace-Key` header (except to `/health/*` and `GET /`). If the key is invalid, user is gated immediately.
- **AC-02 Ingestion Guardrails:** File uploads exceeding 10 MB or batches $>5$ files must be intercepted on the client with clear validation feedback before initiating HTTP requests.
- **AC-03 Polling Efficiency:** Document polling must execute strictly at 2-second intervals while jobs are active and cease immediately upon reaching terminal state (`ready` / `failed`).
- **AC-04 Provenance Integrity:** Every citation rendered in the UI must display filename, page number, and exact quoted snippet matching backend responses.
- **AC-05 Abstention Compliance:** When `is_abstention: true`, the frontend must render an explicit insufficient-evidence view and must never display AI hallucinated citations or suggestions.
- **AC-06 Authenticated PDF Access:** PDF binaries must load via authenticated requests attaching `X-Workspace-Key`. If an unauthorized request is detected, the viewer displays a secure access error.
- **AC-07 Zero Coordinate Assumptions:** The frontend must navigate to page numbers and perform DOM text matching. It must never attempt or claim geometric canvas polygon overlays.
- **AC-08 Responsive Layout:** The multi-pane layout must adjust gracefully: split-pane on desktop ($\ge 1024\text{px}$), stacked tabs on tablet and mobile ($< 1024\text{px}$).
- **AC-09 Design Token Conformance:** 100% of UI components must consume tokens from `FRONTEND_DESIGN_TOKENS.md`. Zero ad-hoc color hex codes or arbitrary inline font styles.
- **AC-10 Keyboard & Screen Reader Accessibility:** All modal dialogs, drawers, citation chips, and buttons must be operable via keyboard (`Tab`, `Enter`, `Escape`) with visible focus rings and WCAG 2.1 AA compliant contrast.

---

## 7. Traceability Matrix to Authoritative PRD

| PRD Requirement | Specification in this Document | Frontend Component / Screen | Verified API Route |
|---|---|---|---|
| **FR-01: Workspace Isolation** | Section 2.1, Section 4.1 | `/`, `PasskeyModal`, `WorkspaceGrid` | `POST /api/v1/workspaces`, `GET /api/v1/workspaces` |
| **FR-02: Document Ingestion** | Section 2.2, Section 4.2 | `UploadDropzone`, `DocumentTable` | `POST .../documents/upload`, `GET .../documents` |
| **FR-03: Storage & Provenance** | Section 2.2, Section 2.4 | `DocumentTable`, `StatusBadge` | `DELETE .../documents/{id}`, `POST .../retry` |
| **FR-04: Grounded Retrieval** | Section 2.3, Section 4.3 | `QueryComposer`, `AnswerCard` | `POST .../queries` |
| **FR-05: Abstention Policy** | Section 2.3, Section 5 | `AbstentionBanner`, `QueryComposer` | `POST .../queries` (`is_abstention: true`) |
| **FR-06: Evidence Inspection** | Section 2.4, Section 4.3 | `AuthenticatedPdfViewer`, `ChunkDrawer` | `GET .../file`, `GET .../pages`, `GET .../chunks/{id}` |
| **FR-07: Cross-Doc Comparison**| Section 2.5, Section 4.4 | `DocSelector`, `FindingMatrix` | `POST .../comparisons`, `GET .../comparisons` |
| **FR-08: Basic Evaluation** | Section 2.6 | `/evaluation`, `BenchmarkDatasetTable` | CLI runner (`pytest backend/tests/eval/`) |
| **FR-09: Operational Behaviour**| Section 2.2, Section 6 | Error banners, upload boundary checks | RFC 7807 problem details across all routes |
