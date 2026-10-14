# ProofLens AI — Frontend Implementation Roadmap (`FRONTEND_IMPLEMENTATION_ROADMAP.md`)

**Document Version:** 1.0.0  
**Status:** Approved for Phased Execution  
**Execution Target:** Next.js 15 (App Router) + TypeScript 5.x  
**Governing Documents:**  
- [PRD v0.1](file:///Users/apple/Documents/Projects/ProofLense-AI/ProofLens-AI-Project-Kickoff-PRD-v0.1.md)  
- [Operating Guidelines (`AGENTS.md`)](file:///Users/apple/Documents/Projects/ProofLense-AI/AGENTS.md)  
- [Frontend Requirements](file:///Users/apple/Documents/Projects/ProofLense-AI/docs/frontend/FRONTEND_REQUIREMENTS.md)  
- [Frontend Architecture](file:///Users/apple/Documents/Projects/ProofLense-AI/docs/frontend/FRONTEND_ARCHITECTURE.md)  
- [Frontend API Integration](file:///Users/apple/Documents/Projects/ProofLense-AI/docs/frontend/FRONTEND_API_INTEGRATION.md)  
- [Frontend Design Tokens](file:///Users/apple/Documents/Projects/ProofLense-AI/docs/frontend/FRONTEND_DESIGN_TOKENS.md)  
- [Frontend Design System](file:///Users/apple/Documents/Projects/ProofLense-AI/docs/frontend/FRONTEND_DESIGN_SYSTEM.md)  

---

## 1. Roadmap Principles & Phased Execution Strategy

In strict adherence to `AGENTS.md` Section 5 (*Development & Verification Workflow*), frontend implementation is structured into **seven incremental, verifiable phases**.

### Governance Rules
1. **Incremental Progression:** Never generate or scaffold multiple phases in a single unreviewed step.
2. **Explicit User Approval:** Each phase requires verification, test execution, and user sign-off before entering the next phase.
3. **No Unperformed Test Claims:** Accessibility, contrast, and test passes must be executed and verified before claiming compliance.
4. **Absolute Secret Zero:** Zero private credentials or API keys in client code or environment variables.

```
+-------------------------------------------------------------------------------+
|                       Frontend Implementation Timeline                        |
|                                                                               |
|  [Phase 0: Documentation] ---> [Phase 1: Scaffolding & Tokens]                |
|  (CURRENT - COMPLETED)         (Next.js 15, CSS Tokens, UI Primitives)        |
|                                                |                              |
|                                                v                              |
|  [Phase 3: Ingestion & Library] <--- [Phase 2: Shell & Workspace Mgmt]        |
|  (Upload, 2s Polling, Status)        (Passkey Gate, App Shell, /workspaces)   |
|               |                                                               |
|               v                                                               |
|  [Phase 4: PDF & Evidence Viewer] ---> [Phase 5: Grounded Q&A Console]        |
|  (Canvas PDF.js, Page Navigation,     (Query Composer, Answer, Citations,     |
|   DOM Snippet Highlighting)            Abstention UI, Query History)          |
|                                                        |                      |
|                                                        v                      |
|  [Phase 7: Evaluation & Hardening] <--- [Phase 6: Comparison Studio]          |
|  (Benchmark View, E2E Tests, Audits)    (2-5 Docs, Matrix, Synthesis, Limits) |
+-------------------------------------------------------------------------------+
```

---

## 2. Phase-by-Phase Execution Plan

### Phase 0: Architecture & Documentation Completion
*Status: COMPLETED (Current Phase)*

- **Deliverables:**
  - `docs/frontend/FRONTEND_DESIGN_TOKENS.md` (Canonical visual tokens).
  - `docs/frontend/FRONTEND_DESIGN_SYSTEM.md` (Canonical component rules).
  - `docs/frontend/FRONTEND_REQUIREMENTS.md` (Feature scope, screen map, user flows, states, traceability).
  - `docs/frontend/FRONTEND_ARCHITECTURE.md` (Next.js App Router, boundaries, state, authenticated PDF architecture).
  - `docs/frontend/FRONTEND_API_INTEGRATION.md` (Reconciled 23 operations, TypeScript contracts, auth, polling, boundaries).
  - `docs/frontend/FRONTEND_IMPLEMENTATION_ROADMAP.md` (Phased milestones, gates, dependencies).
- **Exit Gate:** Complete documentation package delivered; user review and authorization to proceed to Phase 1.

---

### Phase 1: Project Scaffolding, Design Tokens & Core UI Primitives

- **Objective:** Initialize the Next.js 15 TypeScript project with strict CSS design tokens and develop the reusable UI component primitive catalog.
- **Dependencies:** Approved documentation in `docs/frontend/`.
- **Key Tasks:**
  1. Scaffold Next.js 15 App Router application in `frontend/` with TypeScript 5.x and ESLint.
  2. Implement `frontend/styles/tokens.css` mapping 100% of tokens from `FRONTEND_DESIGN_TOKENS.md`.
  3. Implement `frontend/styles/globals.css` with reset, Inter typography, and focus ring standards.
  4. Develop reusable design system primitives in `frontend/components/ui/`:
     - `Button.tsx` (primary, secondary, ghost, destructive; default, hover, focus, loading, disabled).
     - `Input.tsx` (text, search; label, helper text, error state, focus visible).
     - `Card.tsx` (ivory/white surfaces, subtle borders, responsive padding).
     - `Badge.tsx` (neutral, success, warning, danger, info variants).
     - `Modal.tsx` (accessible dialog with focus trap, Escape listener, Backdrop).
     - `Toast.tsx` & `ToastProvider.tsx` (transient status announcements).
     - `Skeleton.tsx` (stable loading geometry placeholders).
  5. Configure Vitest and React Testing Library for component testing.
- **Contrast & Accessibility Validation Gate:**
  - Run automated color contrast check across all token combinations:
    - Text primary (`#202720`) on Canvas (`#F7F7F4`): Ratio $> 13:1$ (Passes AAA).
    - Text secondary (`#58645B`) on Canvas (`#F7F7F4`): Ratio $> 5.8:1$ (Passes AA).
    - Text tertiary (`#737D75`) on Canvas (`#F7F7F4`): Measure and tune if $< 4.5:1$.
    - Accent (`#315A1B`) on White (`#FFFFFF`): Ratio $> 7.5:1$ (Passes AAA).
- **Exit Criteria:**
  - `npm run build` compiles with zero TypeScript or ESLint errors.
  - Component unit tests pass with $100\%$ primitive coverage.
  - Contrast audit logged with zero WCAG 2.1 AA violations.

---

### Phase 2: Authentication Gate, Workspace Management & Navigation Shell

- **Objective:** Implement passkey-based gatekeeping, API client infrastructure, and the multi-workspace navigation shell.
- **Dependencies:** Phase 1 (UI primitives and design tokens).
- **Key Tasks:**
  1. Implement `lib/auth/passkey.ts`: `sessionStorage` accessor and memory cache for `X-Workspace-Key`.
  2. Implement `lib/api/client.ts`: Typed fetch wrapper attaching `X-Workspace-Key` and handling RFC 7807 problem details.
  3. Implement `PasskeyModal.tsx`: Password prompt with auto-focus, validating against `GET /api/v1/auth-test`.
  4. Implement `AppHeader.tsx` & `Sidebar.tsx`: Navigation bar with workspace selector, active route indicators, and mobile drawer.
  5. Implement Route `/` (`app/page.tsx`): Workspace Hub with grid of existing workspaces and *"Create Workspace"* modal (`POST /api/v1/workspaces`).
  6. Implement Route `/workspaces/[workspaceId]` (`app/workspaces/[id]/page.tsx`): Workspace dashboard showing document count, recent queries, and quick links.
- **Verification Gates:**
  - Unauthorized interceptor: Request with missing/bad passkey triggers `PasskeyModal`.
  - Workspace CRUD: Creation, listing, switching, and deletion verified against FastAPI backend.
- **Exit Criteria:**
  - User can enter passkey, create a workspace, navigate to `/workspaces/[id]`, and delete a workspace.

---

### Phase 3: Document Ingestion, Polling Lifecycle & Library Management

- **Objective:** Deliver the document library, multi-file drag-and-drop upload dropzone, 2-second background polling engine, and safe deletion.
- **Dependencies:** Phase 2 (Workspace shell & API client).
- **Key Tasks:**
  1. Implement `UploadDropzone.tsx`: Drag-and-drop zone with client validation:
     - Batch limit $\le 5$ files.
     - Size limit $\le 10\text{ MB}$ ($10,485,760\text{ bytes}$).
     - Header check for `%PDF-` signature.
  2. Implement `lib/api/documents.ts`: Multipart streaming upload (`POST .../documents/upload`), document list (`GET .../documents`), document detail, and retry (`POST .../retry`).
  3. Implement `useIngestionPolling.ts`: 2,000ms polling hook tracking `pending` $\rightarrow$ `processing` $\rightarrow$ `ready` / `failed`.
  4. Implement `DocumentTable.tsx` & `DocumentStatusBadge.tsx`: Displays filename, size, page count, status pill, and action menu.
  5. Implement manual retry action for `failed` documents and safe deletion modal (`DELETE .../documents/{id}`).
- **Verification Gates:**
  - Upload boundary tests: Files $>10\text{ MB}$ or batches $>5$ rejected client-side before network dispatch.
  - Polling lifecycle test: Mocked status sequence correctly updates badge and stops when all items are `ready`.
  - Duplicate upload test: Backend `409 Conflict` rendered gracefully as duplicate error banner.
- **Exit Criteria:**
  - User can upload 1–5 PDF files, observe real-time status transitions, retry failures, and delete documents.

---

### Phase 4: Authenticated PDF Viewer & Evidence Inspector

- **Objective:** Build the split-pane PDF document viewer with authenticated binary streaming, canvas rendering, page navigation, and DOM text snippet highlighting.
- **Dependencies:** Phase 3 (Uploaded PDF documents in `ready` status).
- **Key Tasks:**
  1. Integrate PDF.js library with dedicated web worker (`public/pdf.worker.min.js`).
  2. Implement `lib/api/documents.ts:fetchDocumentPdfBlob`: Streams PDF binary with `X-Workspace-Key` header (`GET .../documents/{id}/file`).
  3. Implement `AuthenticatedPdfViewer.tsx`: Canvas rendering engine with high-DPI scaling (`window.devicePixelRatio`).
  4. Implement `PageNavigator.tsx`: 1-indexed page controls (Previous, Next, page number input, zoom slider).
  5. Implement `TextHighlightLayer.tsx`: Transparent text layer overlaid on canvas with normalized text search for `quoted_snippet`, applying `.evidence-highlight` styling.
  6. Implement `ExtractedChunksDrawer.tsx`: Collapsible inspector displaying extracted page text and embedded chunk segments (`GET .../pages`).
  7. Implement object URL cleanup on component unmount (`URL.revokeObjectURL`) to prevent memory leaks.
- **Verification Gates:**
  - Header verification: PDF binary stream successfully loads through authenticated `fetch()`.
  - Coordinate honesty test: Highlights strictly use text search and physical page navigation; zero geometric bounding box canvas overlays.
- **Exit Criteria:**
  - User can open any ready document, navigate pages, view extracted chunk text, and observe highlighted snippets.

---

### Phase 5: Grounded Q&A Console & Citation Drawer

- **Objective:** Build the natural language Q&A interface with grounded answer rendering, footnote citation chips, candidate evidence inspection, explicit abstention UI, and query history.
- **Dependencies:** Phase 4 (PDF Viewer and citation deep-linking).
- **Key Tasks:**
  1. Implement `QueryComposer.tsx`: Query input (1–2,000 chars) with `top_k` selector and loading skeleton.
  2. Implement `lib/api/queries.ts`: Grounded query execution (`POST .../queries`) and history retrieval (`GET .../queries`).
  3. Implement `lib/utils/citations.ts`: AST-based footnote parser converting `[1]`, `[2]` into interactive `CitationChip.tsx` components.
  4. Implement `AnswerNarrativeCard.tsx`: Displays synthesized answer, citation tags, and timestamp.
  5. Implement `RetrievedEvidenceDrawer.tsx`: Collapsible drawer showing all retrieved chunks, similarity scores, and ranks.
  6. Implement `AbstentionNoticeCard.tsx`: High-visibility warning container rendered when `is_abstention: true` with zero hallucinated citations.
  7. Implement deep-linking navigation: Clicking citation `[N]` navigates to Document Viewer on page `P` with snippet highlighted.
  8. Implement `HistoricalQueriesSidebar.tsx`: Paginated query run history with instant recall.
- **Verification Gates:**
  - Abstention policy test: Submitting an unanswerable query renders the abstention banner and suppresses citations.
  - Tombstone citation test: Viewing query with deleted source document displays snapshot snippet and inactive document badge without crashing.
- **Exit Criteria:**
  - User can submit questions, view grounded answers with citations, inspect candidate evidence, and click citations to jump to exact PDF source pages.

---

### Phase 6: Cross-Document Comparison Studio

- **Objective:** Implement the multi-document comparison studio with finding classification cards (`agreement`, `contradiction`, `difference`, `not_found`), comparative synthesis, and limitations callout.
- **Dependencies:** Phase 5 (Grounded Q&A & citation infrastructure).
- **Key Tasks:**
  1. Implement `DocumentSelectorList.tsx`: Checkbox selector enforcing 2 to 5 `ready` documents.
  2. Implement `TopicQueryInput.tsx`: Topic/prompt composer (3–1,000 characters).
  3. Implement `lib/api/comparisons.ts`: Comparative execution (`POST .../comparisons`) and history listing (`GET .../comparisons`).
  4. Implement `ComparisonFindingCard.tsx`: Finding card featuring semantic category badge, topic headline, per-document statement cards, and clickable citation tags.
  5. Implement `LimitationsBanner.tsx`: High-visibility notice highlighting scoping divergences or incomparable definitions.
  6. Implement `HistoricalComparisonsSidebar.tsx`: List of saved comparison runs with timestamp and query topic.
- **Verification Gates:**
  - Validation test: Selecting $<2$ or $>5$ documents disables submission with explanatory tooltip.
  - Finding classification test: Each finding type (`agreement`, `contradiction`, `difference`, `not_found`) renders correct semantic token styles.
- **Exit Criteria:**
  - User can compare 2–5 documents on a specific topic, view classified findings with citations, and review documented limitations.

---

### Phase 7: Evaluation Demonstration View & Operational Hardening

- **Objective:** Build the read-only evaluation benchmark viewer, implement end-to-end integration tests, and perform production hardening.
- **Dependencies:** Phases 1–6 complete.
- **Key Tasks:**
  1. Implement Route `/evaluation` (`app/evaluation/page.tsx`):
     - Curated test dataset table (test queries, expected document/page, ground-truth characteristics).
     - Target metrics summary card (Hit rate $>85\%$, citation validity $100\%$, abstention correctness $100\%$).
     - Model-judged metric disclaimer banner.
     - Copyable CLI command runner instructions (`pytest backend/tests/eval/`).
  2. Implement Playwright E2E test suite covering full user journey:
     - `auth-gate.spec.ts`: Passkey entry and validation.
     - `ingestion.spec.ts`: Upload PDF, monitor 2s polling, confirm ready status.
     - `grounded-qa.spec.ts`: Submit query, verify answer, click citation, verify PDF page and snippet.
     - `comparison.spec.ts`: Select 2 documents, run comparison, verify findings matrix.
  3. Implement React Error Boundaries on all major view regions to catch and isolate unexpected runtime errors.
  4. Verify production build bundle size, zero secret leaks, and lighthouse accessibility score ($>95$).
- **Verification Gates:**
  - Full E2E suite passes in CI/local headless environment.
  - Zero build warnings or type errors (`next build`).
- **Exit Criteria:**
  - Complete, hardened frontend application ready for production deployment on Vercel.

---

## 3. Implementation Gate & Sign-Off Checklist

| Phase # | Phase Name | Prerequisite | Verification Gate | Sign-Off Status |
|---|---|---|---|---|
| **Phase 0** | Documentation Completion | PRD & Backend Audit | 4 Core Documents in `docs/frontend/` | **COMPLETE** |
| **Phase 1** | Scaffolding, Tokens & Primitives | Phase 0 Approval | 100% Token Mapping & Contrast Audit | Pending User Approval |
| **Phase 2** | Auth Gate & Workspace Shell | Phase 1 Complete | Passkey Gatekeeper & Workspace CRUD | Pending Phase 1 |
| **Phase 3** | Ingestion & Library Management | Phase 2 Complete | Upload Bounds, 2s Polling & Status | Pending Phase 2 |
| **Phase 4** | PDF Viewer & Evidence Inspector | Phase 3 Complete | Authenticated Binary & Text Highlighting | Pending Phase 3 |
| **Phase 5** | Grounded Q&A Console | Phase 4 Complete | Answer Footnotes, Citations & Abstention | Pending Phase 4 |
| **Phase 6** | Comparison Studio | Phase 5 Complete | 2–5 Docs Matrix & Classified Findings | Pending Phase 5 |
| **Phase 7** | Evaluation View & Hardening | Phase 6 Complete | E2E Playwright Suite & Production Build | Pending Phase 6 |
