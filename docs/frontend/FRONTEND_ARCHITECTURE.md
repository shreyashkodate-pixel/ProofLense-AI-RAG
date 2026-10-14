# ProofLens AI — Frontend Architecture Specification (`FRONTEND_ARCHITECTURE.md`)

**Document Version:** 1.0.0  
**Status:** Approved for Implementation Planning  
**Target Framework:** Next.js 15 (App Router) + TypeScript 5.x + Vanilla CSS Tokens  
**Governing Documents:**  
- [PRD v0.1](file:///Users/apple/Documents/Projects/ProofLense-AI/ProofLens-AI-Project-Kickoff-PRD-v0.1.md)  
- [Operating Guidelines (`AGENTS.md`)](file:///Users/apple/Documents/Projects/ProofLense-AI/AGENTS.md)  
- [Frontend Requirements](file:///Users/apple/Documents/Projects/ProofLense-AI/docs/frontend/FRONTEND_REQUIREMENTS.md)  
- [Frontend Design Tokens](file:///Users/apple/Documents/Projects/ProofLense-AI/docs/frontend/FRONTEND_DESIGN_TOKENS.md)  
- [Frontend Design System](file:///Users/apple/Documents/Projects/ProofLense-AI/docs/frontend/FRONTEND_DESIGN_SYSTEM.md)  
- [Backend Frontend-Handoff Report v1.1.0](file:///Users/apple/Documents/Projects/ProofLense-AI/docs/backend/FRONTEND_HANDOFF_REPORT.md)  

---

## 1. Architectural Overview & Design Philosophy

The ProofLens AI frontend is architected as an **evidence-first, low-latency, and high-provenance Next.js application**. The interface prioritizes verifiable source citations, responsive navigation across dense documents, and resilient offline/real-time state synchronization.

```
+-------------------------------------------------------------------------------+
|                             Next.js 15 App Router                             |
|                                                                               |
|  +--------------------+  +----------------------+  +-----------------------+  |
|  | Server Components  |  |  Client Components   |  |     State & Hooks     |  |
|  | - Shell layouts    |  | - Canvas PDF Viewer  |  | - useIngestionPolling |  |
|  | - Page metadata    |  | - Upload dropzone    |  | - useGroundedQuery    |  |
|  | - Static frames    |  | - Citation drawer    |  | - useComparison       |  |
|  +---------+----------+  +----------+-----------+  +-----------+-----------+  |
|            |                        |                          |              |
|            v                        v                          v              |
|  +-------------------------------------------------------------------------+  |
|  |                         API Client Layer (lib/api)                      |  |
|  |  - Injects X-Workspace-Key from sessionStorage/memory                   |  |
|  |  - Validates typed Pydantic-mirrored responses                          |  |
|  |  - Parses RFC 7807 problem details error envelopes                      |  |
|  +-------------------------------------+-----------------------------------+  |
+----------------------------------------|--------------------------------------+
                                         | HTTP / REST (X-Workspace-Key)
                                         v
+-------------------------------------------------------------------------------+
|                       FastAPI Backend Service (Port 8000)                     |
|  - Passkey Gatekeeper (X-Workspace-Key)                                       |
|  - PostgreSQL + pgvector (AsyncPG)                                            |
|  - Ingestion Engine (pypdf + Matryoshka 768-dim embeddings)                   |
|  - Grounded Synthesis & Comparator (Gemini 2.5 Flash)                         |
+-------------------------------------------------------------------------------+
```

---

## 2. Next.js 15 Application Structure & Modular Hierarchy

The application structure strictly separates pages, reusable design system primitives, feature domain modules, and infrastructure libraries:

```
frontend/
├── app/                                    # Next.js 15 App Router directory
│   ├── layout.tsx                          # Root layout: font loading, global tokens, Toast provider
│   ├── page.tsx                            # Route /: Workspace Hub & Passkey Gatekeeper
│   ├── evaluation/                         # Route /evaluation: Benchmark summary
│   │   └── page.tsx
│   └── workspaces/
│       └── [workspaceId]/                  # Dynamic workspace route boundary
│           ├── layout.tsx                  # Workspace shell: Header, Persistent Sidebar, Context
│           ├── page.tsx                    # Route /workspaces/[id]: Workspace Dashboard
│           ├── documents/
│           │   ├── page.tsx                # Route .../documents: Document Library & Upload
│           │   └── [documentId]/
│           │       └── page.tsx            # Route .../documents/[id]: PDF Viewer & Chunk Inspector
│           ├── queries/
│           │   └── page.tsx                # Route .../queries: Grounded Q&A Console
│           └── compare/
│               └── page.tsx                # Route .../compare: Cross-Document Comparison Studio
├── components/
│   ├── ui/                                 # Design system primitives (Token-compliant)
│   │   ├── Button.tsx
│   │   ├── Input.tsx
│   │   ├── Card.tsx
│   │   ├── Badge.tsx
│   │   ├── Modal.tsx
│   │   ├── Toast.tsx
│   │   ├── Skeleton.tsx
│   │   └── Popover.tsx
│   ├── layout/                             # Structural layout components
│   │   ├── AppHeader.tsx
│   │   ├── Sidebar.tsx
│   │   ├── WorkspaceSelector.tsx
│   │   └── PasskeyModal.tsx
│   ├── documents/                          # Ingestion & library domain components
│   │   ├── UploadDropzone.tsx
│   │   ├── DocumentTable.tsx
│   │   ├── DocumentStatusBadge.tsx
│   │   └── IngestionProgressCard.tsx
│   ├── pdf/                                # PDF rendering & citation inspection
│   │   ├── AuthenticatedPdfViewer.tsx      # Canvas-based PDF.js binary renderer
│   │   ├── PageNavigator.tsx               # 1-indexed page jumping controls
│   │   ├── TextHighlightLayer.tsx          # DOM search highlight for quoted_snippet
│   │   └── ExtractedChunksDrawer.tsx       # Side panel showing page raw text & chunks
│   ├── queries/                            # Grounded Q&A domain components
│   │   ├── QueryComposer.tsx
│   │   ├── AnswerNarrativeCard.tsx
│   │   ├── CitationChip.tsx
│   │   ├── RetrievedEvidenceDrawer.tsx
│   │   └── HistoricalQueriesSidebar.tsx
│   └── comparison/                         # Comparison matrix domain components
│       ├── DocumentSelectorList.tsx
│       ├── TopicQueryInput.tsx
│       ├── ComparisonFindingCard.tsx
│       ├── LimitationsBanner.tsx
│       └── HistoricalComparisonsSidebar.tsx
├── lib/
│   ├── api/                                # Typed API client modules
│   │   ├── client.ts                       # Base fetch wrapper with auth header injection
│   │   ├── workspaces.ts                   # Workspace CRUD endpoints
│   │   ├── documents.ts                    # Streaming upload, binary fetch, pages, chunks
│   │   ├── queries.ts                      # Grounded query execution & history
│   │   └── comparisons.ts                  # Multi-document comparison & history
│   ├── auth/                               # Client security & passkey storage
│   │   ├── passkey.ts                      # sessionStorage & in-memory token manager
│   │   └── AuthContext.tsx                 # React auth provider & modal trigger
│   ├── hooks/                              # Custom React lifecycle & polling hooks
│   │   ├── useWorkspaces.ts
│   │   ├── useDocuments.ts
│   │   ├── useIngestionPolling.ts          # 2000ms terminal status poller
│   │   ├── useGroundedQuery.ts
│   │   └── useComparison.ts
│   └── utils/
│       ├── citations.ts                    # Footnote parsing: converts [1] to interactive tags
│       ├── textMatch.ts                    # Fuzzy & exact string matching for PDF text layer
│       └── formatters.ts                   # Date, byte sizes, and score formatters
├── styles/
│   ├── tokens.css                          # Canonical CSS custom properties from FRONTEND_DESIGN_TOKENS.md
│   └── globals.css                         # Base resets, typography, and focus ring definitions
└── public/
    └── pdf.worker.min.js                   # Dedicated worker for background PDF parsing
```

---

## 3. Server vs. Client Component Boundaries

Next.js App Router enforces explicit separation between React Server Components (RSC) and Client Components (`"use client"`). We adhere to the following strict boundaries:

```
+-------------------------------------------------------------------------------+
|                            Server Component Boundary                          |
|  - app/layout.tsx: Global metadata, fonts, CSS token inclusion                |
|  - app/workspaces/[id]/layout.tsx: Route framing, page scaffolding            |
|  - app/evaluation/page.tsx: Curated benchmark table & static CLI guide        |
+---------------------------------------+---------------------------------------+
                                        |
                   Boundary passing props & route params
                                        v
+-------------------------------------------------------------------------------+
|                            Client Component Boundary                          |
|  - PasskeyModal: Browser sessionStorage access & interactive password entry    |
|  - UploadDropzone: File drag/drop events, ArrayBuffer pre-checks, streaming   |
|  - IngestionPoller: setInterval(2000) state machine polling                   |
|  - AuthenticatedPdfViewer: HTML5 Canvas rendering, Web Worker, text layer     |
|  - QueryComposer & AnswerCard: Text selection, footnote clicks, popovers      |
|  - DocumentSelector & ComparisonMatrix: Multi-checkbox selection state       |
+-------------------------------------------------------------------------------+
```

### Boundary Rationale
1. **Passkey Interception:** Since `X-Workspace-Key` is stored in the browser (`sessionStorage` or client memory) and must never be exposed to the server environment, all data-fetching operations requiring authentication must execute on the client or via client-orchestrated API calls.
2. **Interactive Canvas Rendering:** Rendering PDF binaries requires direct access to browser DOM APIs (`HTMLCanvasElement`, `window.devicePixelRatio`, `ResizeObserver`). The PDF viewer is strictly a Client Component.
3. **Background Status Polling:** Tracking ingestion progress (`pending` $\rightarrow$ `processing` $\rightarrow$ `ready`) requires a reactive timer (`setInterval`) and dynamic UI state updates, necessitating client execution.

---

## 4. Data Fetching & State Management Strategy

### 4.1 State Hierarchy
1. **URL as Single Source of Truth:**
   - Active Workspace: Route path `/workspaces/[workspaceId]`.
   - Active Document in Viewer: Route path `/workspaces/[workspaceId]/documents/[documentId]`.
   - Deep-Linked Citation: Search parameters `?page=4&chunk=b18f0c29...`.
   - Benefits: Full browser history support (Back/Forward), shareable internal URLs, and zero stale state on refresh.
2. **Client-Side Cache & React Hooks:**
   - Instead of heavy external state management libraries (Redux/Zustand), the application utilizes a lightweight, hook-based SWR/React Query architecture (`lib/hooks/`).
   - Hooks maintain cached responses for document lists, query history, and chunk text, invalidating queries when mutations occur (e.g., re-fetching document list upon upload completion or retry).
3. **Ephemeral UI State:**
   - Standard React `useState` and `useReducer` for modal visibility, active citation popover, search query text, and multi-document checkbox selections.

---

## 5. Authenticated PDF Binary Delivery & Rendering Architecture

### 5.1 The Authentication Barrier
Standard browser `<iframe src="...">` or `<embed>` elements **cannot send custom HTTP headers** (such as `X-Workspace-Key`). Direct embedding would fail with `401 Unauthorized` because the backend strictly protects `GET /api/v1/workspaces/{id}/documents/{id}/file`.

### 5.2 The Verified Solution
```
[Client Component: AuthenticatedPdfViewer]
         |
         | 1. fetch('/api/v1/workspaces/.../file', { headers: { 'X-Workspace-Key': passkey } })
         v
[FastAPI: GET .../file] (Validates passkey, streams application/pdf binary)
         |
         | 2. Binary stream received as ArrayBuffer / Blob
         v
[Client Memory]
         |
         | 3. URL.createObjectURL(blob) or direct pdfjsLib.getDocument({ data: arrayBuffer })
         v
[PDF.js Web Worker (pdf.worker.min.js)]
         |
         | 4. Parses PDF pages asynchronously off main thread
         v
[HTML5 Canvas + Text Layer Div]
         |
         | 5. Draws vector PDF page on Canvas
         | 6. Injects transparent selectable text layer directly over Canvas
         v
[TextHighlightLayer]
         |
         | 7. Scans DOM text nodes for citation.quoted_snippet
         | 8. Wraps matching range in <mark class="evidence-highlight">
```

### 5.3 Memory Management Invariant
When opening and closing documents in the viewer, all generated object URLs must be explicitly revoked (`URL.revokeObjectURL(url)`) and PDF.js document instances destroyed (`pdfDocument.destroy()`) in component cleanup hooks (`useEffect` return callback) to prevent browser memory leaks.

---

## 6. Text Highlighting & Coordinate Boundary Invariant

### 6.1 Architectural Constraint (Zero Geometric Bounding Boxes)
- The backend ingestion pipeline parses physical PDF pages with `pypdf` and creates page-bounded text chunks.
- **The backend produces 1-indexed `page_number`, `raw_text`, and `chunk_text`, but does NOT generate bounding box coordinates (`x0, y0, x1, y1`) or character quad-points.**
- **Rule:** The frontend must never claim or attempt to draw geometric bounding-box rectangles on the PDF canvas.

### 6.2 Frontend Highlighting Protocol
1. Upon citation navigation (`?page=N&chunk=UUID`), the PDF viewer renders page `N`.
2. The `TextHighlightLayer` component extracts the text content of the rendered transparent DOM text layer.
3. A normalized substring search matches `citation.quoted_snippet` against the page text (normalizing multiple spaces and linebreaks).
4. If an exact match is located:
   - The corresponding text span is wrapped with `.evidence-highlight` (styled with `--color-evidence-highlight: #E7EFD9` and `--color-evidence-outline: #8DA878`).
   - The viewer smoothly scrolls the matching text span into the center of the viewport.
5. If match is ambiguous or missing (e.g. minor whitespace discrepancies or hyphenation):
   - The UI displays an amber indicator tag in the Evidence Drawer: *"Source excerpt on page N (text highlight approximate or not matched in visual text layer)"*.
   - The verbatim `quoted_snippet` is rendered in full in the inspector drawer.

---

## 7. Security Boundaries & Zero-Leakage Architecture

### 7.1 Absolute Secret Zero Compliance
- The frontend client bundle contains **zero backend secrets**.
- Public environment variables are restricted strictly to:
  - `NEXT_PUBLIC_API_BASE_URL` (e.g. `http://localhost:8000` or production Render backend URL).
  - `NEXT_PUBLIC_APP_URL` (Vercel deployment URL).
- `GEMINI_API_KEY`, Supabase database connection strings, Supabase service keys, and internal signing secrets exist exclusively in the backend runtime environment.
- The build process fails immediately if any non-`NEXT_PUBLIC_` secret is referenced in client modules.

### 7.2 Passkey Storage & Isolation
- The `X-Workspace-Key` is entered by the user in `PasskeyModal`.
- It is saved in `sessionStorage` (cleared automatically when the browser tab closes) and mirrored in a React context memory store.
- It is never stored in persistent `localStorage` or browser cookies.

### 7.3 Untrusted Content & Prompt Injection Defense
- PDF text content, extracted chunks, and LLM-generated answers are treated as **untrusted user input**.
- The frontend **never uses `dangerouslySetInnerHTML`** to render document text, answers, or snippets.
- All dynamic strings are rendered through standard React text nodes (`<span>{text}</span>`) to prevent XSS.
- Citation footnote tags (`[1]`, `[2]`) are parsed using an AST-style tokenizing parser that constructs React component trees without raw HTML evaluation.

---

## 8. Testing Architecture & Verification Gates

```
+-------------------------------------------------------------------------------+
|                            Frontend Verification Suite                        |
|                                                                               |
|  +---------------------+  +----------------------+  +----------------------+  |
|  |     Unit Tests      |  |  Integration Tests   |  |      E2E Tests       |  |
|  |     (Vitest + RTL)  |  |  (MSW + Vitest)      |  |     (Playwright)     |  |
|  | - Design primitives |  | - Polling lifecycle  |  | - Workspace create   |  |
|  | - Citation parser   |  | - Passkey rejection  |  | - Upload -> Ingest   |  |
|  | - Token contrast    |  | - RFC 7807 parsing   |  | - Query -> Citation   |  |
|  +---------------------+  +----------------------+  +----------------------+  |
+-------------------------------------------------------------------------------+
```

1. **Unit Testing (Vitest + React Testing Library):**
   - Validates all component primitives (`Button`, `Input`, `Card`, `Badge`).
   - Validates footnote citation parser (`parseFootnotes("Answer [1] details...")`).
   - Validates token contrast ratios against WCAG 2.1 AA requirements.
2. **Integration Testing (Mock Service Worker — MSW):**
   - Mocks FastAPI backend routes and verifies frontend API client error handling.
   - Tests ingestion polling state transitions (`pending` $\rightarrow$ `processing` $\rightarrow$ `ready`).
   - Tests passkey rejection flow (`401 Unauthorized` triggers modal).
3. **End-to-End Testing (Playwright):**
   - Automates the full PRD user journey against local test servers:
     `Passkey Login` $\rightarrow$ `Create Workspace` $\rightarrow$ `Upload PDF` $\rightarrow$ `Wait for Ready` $\rightarrow$ `Execute Grounded Query` $\rightarrow$ `Click Citation` $\rightarrow$ `Verify PDF Page & Snippet`.
