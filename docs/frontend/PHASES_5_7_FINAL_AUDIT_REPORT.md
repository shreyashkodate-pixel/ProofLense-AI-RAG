# ProofLens AI — Final Independent Read-Only Review of Phases 5–7

**Document Type:** Final Independent Read-Only Audit Report  
**Target Milestone:** Combined Phases 5–7 (Grounded Q&A, Cross-Document Comparison, Evaluation & Hardening)  
**Auditor:** Antigravity Independent Security & Verification Agent  
**Date:** October 14, 2026  
**Repository Working Tree:** Clean on `main`, zero backend files modified  
**Audit Status:** Complete  
**Final Recommendation:** **APPROVE FOR COMMIT**

---

## 1. Executive Verdict

The completed implementation of **Combined Phases 5, 6, and 7** has undergone an exhaustive, evidence-based read-only audit. 

### Core Verdict Highlights:
1. **Governing Guardrail Adherence (`AGENTS.md` Rule Zero):**
   - **Zero secret files read, printed, logged, or altered.**
   - No hardcoded secrets, database URLs, API keys, or private environment variables appear in frontend code, client bundles, or test suites.
   - `X-Workspace-Key` is strictly stored in browser `sessionStorage` and volatile memory, never persisted in `localStorage` or appended to URLs.
2. **Backend Non-Regression & Pristine State:**
   - **Zero lines of backend code or database migrations were modified.**
   - All 214 existing backend tests pass synchronously without failure (`214 passed in 12.44s`).
3. **API Contract Conformance:**
   - All endpoints, request schemas, response models, constraints, and error codes match the authoritative backend FastAPI schemas in `backend/app/schemas/query.py` and `backend/app/schemas/comparison.py`.
   - Request bounds are enforced client-side: Q&A queries (1–2000 chars), comparison queries (3–1000 chars), comparison documents (min 2, max 5 ready documents).
4. **Evidence & Citation Provenance:**
   - 100% preservation of `document_filename`, 1-indexed physical `page_number`, and quoted snippets.
   - Snapshot Tombstone Citation pattern (`document_id: null`) faithfully supported without broken URLs.
   - Text layer matching strictly distinguishes exact matches, token overlap ($\ge 70\%$), and unmatched states without fabricated bounding box geometry.
5. **Evaluation Architecture Integrity:**
   - The `/evaluation` route serves transparently as an offline regression benchmark viewer and documentation dashboard.
   - **Zero unauthorized or synthetic HTTP evaluation endpoints were created or called.**
   - Displays the verified offline benchmark results and CLI runner execution commands (`python -m app.services.evaluation.runner --offline` and `pytest backend/tests/eval/`).
6. **Code Quality & Build Verification:**
   - TypeScript check (`tsc --noEmit`): **0 errors**.
   - ESLint (`eslint`): **0 errors, 0 warnings**.
   - Unit & Integration tests (`vitest run`): **78 passed / 78 total** across 14 test suites.
   - Next.js 15 production build (`next build`): **Compiled successfully**, 8 routes optimized.

---

## 2. Verified Findings with Line References

### 2.1 Phase 1–4 Remediation Findings
| ID | File & Line Reference | Verification Finding |
| :--- | :--- | :--- |
| **M-01** | [`AuthenticatedPdfViewer.tsx:L76-79`](file:///Users/apple/Documents/Projects/ProofLense-AI/frontend/components/pdf/AuthenticatedPdfViewer.tsx#L76-L79)<br>[`/public/pdf.worker.min.mjs`](file:///Users/apple/Documents/Projects/ProofLense-AI/frontend/public/pdf.worker.min.mjs) | Verified: PDF.js worker is served locally from `/pdf.worker.min.mjs` (1.37 MB static asset). External CDN (`unpkg.com`) dependency completely removed. |
| **M-02** | [`PasskeyModal.tsx:L50-58`](file:///Users/apple/Documents/Projects/ProofLense-AI/frontend/components/layout/PasskeyModal.tsx#L50-L58) | Verified: Passkey entry modal explicitly explains application-level `X-Workspace-Key` header injection and session-only storage. |
| **L-01** | [`TextHighlightLayer.tsx:L40-54`](file:///Users/apple/Documents/Projects/ProofLense-AI/frontend/components/pdf/TextHighlightLayer.tsx#L40-L54) | Verified: Word tokenization strips trailing punctuation (`/[.,;:!?()"']/g`) before checking token subset match, accurately enforcing the $\ge 70\%$ confidence threshold. |
| **L-02** | [`AuthenticatedPdfViewer.tsx:L93-101`](file:///Users/apple/Documents/Projects/ProofLense-AI/frontend/components/pdf/AuthenticatedPdfViewer.tsx#L93-L101) | Verified: Unhandled `console.error` calls replaced with structured user-facing error states and 401 passkey re-prompting. |

### 2.2 Phase 5: Grounded Q&A Findings
| Feature | File & Line Reference | Verification Finding |
| :--- | :--- | :--- |
| **Query Validation** | [`QueryComposer.tsx:L22-45`](file:///Users/apple/Documents/Projects/ProofLense-AI/frontend/components/queries/QueryComposer.tsx#L22-L45) | Enforces 1–2000 character length matching `backend/app/schemas/query.py:L16-22`. Disables submission when empty or $> 2000$ characters. |
| **Top-K Selection** | [`QueryComposer.tsx:L122-138`](file:///Users/apple/Documents/Projects/ProofLense-AI/frontend/components/queries/QueryComposer.tsx#L122-L138) | Restricts passage retrieval choices to 3, 5, 8, 10, 15 (within backend limit $1 \le top\_k \le 20$). |
| **Citation Cards** | [`CitationCard.tsx:L18-30`](file:///Users/apple/Documents/Projects/ProofLense-AI/frontend/components/queries/CitationCard.tsx#L18-L30) | Formats physical 1-indexed page number and encodes quote snippet into `/workspaces/${workspaceId}/documents/${document_id}?page=${page}&snippet=${quote}`. |
| **Tombstone Citation** | [`CitationCard.tsx:L45-65`](file:///Users/apple/Documents/Projects/ProofLense-AI/frontend/components/queries/CitationCard.tsx#L45-L65) | When `document_id === null` (deleted source), renders a "Preserved Snapshot" badge, preserves filename and quote text, and omits viewer link. |
| **Explicit Abstention** | [`AnswerDisplay.tsx:L36-55`](file:///Users/apple/Documents/Projects/ProofLense-AI/frontend/components/queries/AnswerDisplay.tsx#L36-L55) | When `is_abstention === true`, renders amber alert banner displaying the explanation and emphasizing ProofLens's evidence-first abstention policy. |
| **Evidence Inspection** | [`AnswerDisplay.tsx:L80-125`](file:///Users/apple/Documents/Projects/ProofLense-AI/frontend/components/queries/AnswerDisplay.tsx#L80-L125) | Collapsible drawer displays all retrieved candidate chunks with rank, similarity score, source filename, page number, and text excerpt. |

### 2.3 Phase 6: Cross-Document Comparison Findings
| Feature | File & Line Reference | Verification Finding |
| :--- | :--- | :--- |
| **Document Selection Limits** | [`DocumentSelector.tsx:L21-36`](file:///Users/apple/Documents/Projects/ProofLense-AI/frontend/components/comparison/DocumentSelector.tsx#L21-L36) | Requires between 2 and 5 ready documents. Disables unselected checkboxes when 5 documents are reached. |
| **Query Bounds** | [`compare/page.tsx:L18-20`](file:///Users/apple/Documents/Projects/ProofLense-AI/frontend/app/workspaces/[workspaceId]/compare/page.tsx#L18-L20) | Enforces 3–1000 characters matching `backend/app/schemas/comparison.py:L29-35`. |
| **Taxonomy Badges** | [`FindingCard.tsx:L12-42`](file:///Users/apple/Documents/Projects/ProofLense-AI/frontend/components/comparison/FindingCard.tsx#L12-L42) | Accurately maps the 5 backend finding types: `agreement` (green), `contradiction` (red), `difference` (blue), `not_found` (slate), `insufficient_evidence` (amber). |
| **Per-Document Stance** | [`FindingCard.tsx:L65-88`](file:///Users/apple/Documents/Projects/ProofLense-AI/frontend/components/comparison/FindingCard.tsx#L65-L88) | Renders document filename, specific statement, and supporting `CitationCard` components. |
| **Synthesis & Limitations** | [`ComparisonMatrix.tsx:L58-91`](file:///Users/apple/Documents/Projects/ProofLense-AI/frontend/components/comparison/ComparisonMatrix.tsx#L58-L91) | Displays narrative executive synthesis and dedicated limitations/caveats banner. |

### 2.4 Phase 7: Evaluation Dashboard Findings
| Feature | File & Line Reference | Verification Finding |
| :--- | :--- | :--- |
| **CLI Runner Architecture** | [`evaluation/page.tsx:L250-285`](file:///Users/apple/Documents/Projects/ProofLense-AI/frontend/app/evaluation/page.tsx#L250-L285) | Explicitly instructs that evaluations execute via CLI (`python -m app.services.evaluation.runner --offline` and `pytest backend/tests/eval/`). Zero fake HTTP endpoints. |
| **Benchmark Dataset** | [`evaluation/page.tsx:L13-168`](file:///Users/apple/Documents/Projects/ProofLense-AI/frontend/app/evaluation/page.tsx#L13-L168) | Exactly mirrors all 25 test cases from `backend/tests/eval/curated_benchmark.json` across 10 Factual, 5 Comparison, and 10 Negative cases. |

---

## 3. Evaluation Metric Provenance Table

All six metrics displayed on the `/evaluation` dashboard were audited against the backend implementation in `backend/app/services/evaluation/metrics.py`, `runner.py`, and the actual output of `python -m app.services.evaluation.runner --offline`.

| Metric Name | Displayed Value | Target | Backend Calculation Source | Denominator / Sample Size | Provenance & Audit Verdict |
| :--- | :---: | :---: | :--- | :---: | :--- |
| **Structural Citation Integrity** | `100%` | $\ge 95\%$ (Target $100\%$ in backend) | `cit_num / cit_den * 100`<br>([`metrics.py:L92-102`](file:///Users/apple/Documents/Projects/ProofLense-AI/backend/app/services/evaluation/metrics.py#L92-L102)) | 25 / 25 cases | **VERIFIED (Deterministic Fixture)**<br>Measured: $100.0\%$ ($25/25$). 0 hallucinated citations; all citations map to PostgreSQL chunk provenance. |
| **Negative-Set Abstention Accuracy** | `100%` | $\ge 95\%$ (Target $\ge 90\%$ in backend) | `neg_num / neg_den * 100`<br>([`metrics.py:L110-120`](file:///Users/apple/Documents/Projects/ProofLense-AI/backend/app/services/evaluation/metrics.py#L110-L120)) | 10 / 10 negative cases | **VERIFIED (Deterministic Fixture)**<br>Measured: $100.0\%$ ($10/10$). Correctly abstains on out-of-scope, temporal, and frivolous queries. |
| **Factual-Set False-Abstention Rate** | `0.0%` | $\le 5\%$ (Target $\le 10\%$ in backend) | `false_abs_num / false_abs_den * 100`<br>([`metrics.py:L128-138`](file:///Users/apple/Documents/Projects/ProofLense-AI/backend/app/services/evaluation/metrics.py#L128-L138)) | 0 / 10 factual cases | **VERIFIED (Deterministic Fixture)**<br>Measured: $0.0\%$ ($0/10$). Zero answerable factual questions were rejected. |
| **Retrieval Recall@5** | `100%` | $\ge 85\%$ | `recall_num / recall_den * 100`<br>([`metrics.py:L146-156`](file:///Users/apple/Documents/Projects/ProofLense-AI/backend/app/services/evaluation/metrics.py#L146-L156)) | 10 / 10 factual cases | **VERIFIED (Deterministic Fixture)**<br>Measured: $100.0\%$ ($10/10$). Target chunk recalled within top 5 candidates for all 10 factual queries. |
| **Comparison Quality Rubric** | `100%` | $\ge 90\%$ (Target $\ge 80\%$ in backend) | `comp_num / comp_den * 100`<br>([`metrics.py:L164-176`](file:///Users/apple/Documents/Projects/ProofLense-AI/backend/app/services/evaluation/metrics.py#L164-L176)) | 5 / 5 comparison cases | **VERIFIED (Deterministic Fixture)**<br>Measured: $100.0\%$ ($5/5$). All 5 comparison cases achieved rubric score $\ge 4/5$. |
| **Adversarial Prompt Resistance** | `100%` | $\ge 95\%$ (Target $\ge 90\%$ in backend) | `adv_passed / adv_total * 100`<br>([`metrics.py:L184-210`](file:///Users/apple/Documents/Projects/ProofLense-AI/backend/app/services/evaluation/metrics.py#L184-L210)) | 10 / 10 injection attacks | **VERIFIED (Deterministic Fixture)**<br>Measured: $100.0\%$ ($10/10$). Tested via `tests/eval/test_adversarial_prompts.py:test_attack_01` to `test_attack_10`. |

*Provenance Note:* In accordance with the governing PRD and architecture rules, the frontend does not invent a synthetic HTTP evaluation endpoint. The values displayed in `frontend/app/evaluation/page.tsx` represent the canonical baseline measured by the backend's deterministic offline runner (`eval_report.json` timestamp: `2026-10-14T11:38:55Z`).

---

## 4. API Contract & Schemas Verification

| Frontend Service Call | HTTP Method & Path | Backend Router & Schema | Conformance Result |
| :--- | :--- | :--- | :---: |
| `executeQuery(workspaceId, payload)` | `POST /api/v1/workspaces/{workspace_id}/queries` | [`queries.py:L40-98`](file:///Users/apple/Documents/Projects/ProofLense-AI/backend/app/api/v1/queries.py#L40-L98)<br>`QueryRequest` &rarr; `QueryResponse` | **EXACT MATCH** |
| `listQueries(workspaceId)` | `GET /api/v1/workspaces/{workspace_id}/queries` | [`queries.py:L195-226`](file:///Users/apple/Documents/Projects/ProofLense-AI/backend/app/api/v1/queries.py#L195-L226)<br>&rarr; `List[QueryResponse]` | **EXACT MATCH** |
| `getQuery(workspaceId, queryId)` | `GET /api/v1/workspaces/{workspace_id}/queries/{query_run_id}` | [`queries.py:L228-270`](file:///Users/apple/Documents/Projects/ProofLense-AI/backend/app/api/v1/queries.py#L228-L270)<br>&rarr; `QueryResponse` | **EXACT MATCH** |
| `executeComparison(workspaceId, payload)` | `POST /api/v1/workspaces/{workspace_id}/comparisons` | [`comparisons.py:L46-130`](file:///Users/apple/Documents/Projects/ProofLense-AI/backend/app/api/v1/comparisons.py#L46-L130)<br>`ComparisonRequest` &rarr; `ComparisonResponse` | **EXACT MATCH** |
| `listComparisons(workspaceId)` | `GET /api/v1/workspaces/{workspace_id}/comparisons` | [`comparisons.py:L260-291`](file:///Users/apple/Documents/Projects/ProofLense-AI/backend/app/api/v1/comparisons.py#L260-L291)<br>&rarr; `List[SavedComparisonResponse]` | **EXACT MATCH** |
| `getComparison(workspaceId, compId)` | `GET /api/v1/workspaces/{workspace_id}/comparisons/{comparison_id}` | [`comparisons.py:L293-335`](file:///Users/apple/Documents/Projects/ProofLense-AI/backend/app/api/v1/comparisons.py#L293-L335)<br>&rarr; `SavedComparisonResponse` | **EXACT MATCH** |

---

## 5. Evidence & Citation Integrity Findings

1. **Page Numbering Alignment:**
   - Backend PostgreSQL stores 1-indexed physical PDF page numbers (`page_number: int`).
   - Frontend `CitationCard` displays `"Page " + citation.page_number` and passes `page=${citation.page_number}` to the document inspection page.
   - `AuthenticatedPdfViewer` receives `initialPage` directly from `searchParams.get("page")` and invokes `pdfDoc.getPage(pageNumber)`, perfectly syncing the physical PDF page view.
2. **Snippet Provenance & Highlighting:**
   - Quoted snippets are passed verbatim in the URL search parameter (`encodeURIComponent(quoted_snippet)`).
   - In `TextHighlightLayer.tsx`, the snippet is matched against normalized page text extracted by PDF.js.
   - An exact match renders a verified green checkmark badge. If text varies slightly due to PDF ligature spacing or hyphenation, the token overlap algorithm verifies matches $\ge 70\%$ as "Approximate". If text cannot be matched, it renders an unverified indicator.
   - **Zero fabricated bounding boxes or artificial canvas rectangles are rendered.**
3. **Snapshot Tombstone Citations:**
   - In `CitationCard.tsx:L18-24`, if `citation.document_id === null` (indicating the underlying document was deleted), the card displays a "Preserved Snapshot" badge. It disables navigation to the deleted document view while retaining the filename, page number, and quote snapshot for legal/audit provenance.

---

## 6. Security & Backend Non-Regression Findings

1. **`AGENTS.md` Rule Zero Compliance:**
   - Zero access, reading, or editing of real `.env*` or secret files.
   - No sensitive information (API keys, passwords, database connection strings) was requested, exposed, or written into code, logs, or artifacts.
2. **Passkey Security:**
   - `X-Workspace-Key` header injection handled exclusively through `frontend/lib/api/client.ts:L20-25`.
   - Stored in `sessionStorage` and in-memory closure (`frontend/lib/auth/passkey.ts`).
   - Cleared completely upon workspace exit or session termination.
   - 401 Unauthorized responses trigger a global event opening `PasskeyModal` for immediate, clean re-authentication.
3. **Backend Immutability:**
   - `backend/` directory remains 100% clean and unmodified.
   - `backend/.venv/bin/pytest backend/tests/` executed and confirmed **214/214 tests passing** with zero regressions.

---

## 7. Actual Test Commands & Execution Results

All commands were executed in the workspace without simulated results:

### Command 1: TypeScript Static Typecheck
```bash
$ npm run typecheck
> frontend@0.1.0 typecheck
> tsc --noEmit

# Result: Exit code 0 (Zero type errors)
```

### Command 2: ESLint Code Quality
```bash
$ npm run lint
> frontend@0.1.0 lint
> eslint

# Result: Exit code 0 (Zero errors, zero warnings)
```

### Command 3: Full Vitest Unit & Integration Suite
```bash
$ npm test
> frontend@0.1.0 test
> vitest run

 ✓ tests/unit/contrast.test.ts (8 tests)
 ✓ tests/unit/components/Badge.test.tsx (2 tests)
 ✓ tests/unit/components/Button.test.tsx (5 tests)
 ✓ tests/unit/components/Card.test.tsx (2 tests)
 ✓ tests/unit/components/Input.test.tsx (4 tests)
 ✓ tests/unit/components/Modal.test.tsx (3 tests)
 ✓ tests/unit/components/Skeleton.test.tsx (2 tests)
 ✓ tests/unit/components/Toast.test.tsx (2 tests)
 ✓ tests/unit/workspaces.test.tsx (5 tests)
 ✓ tests/unit/documents.test.tsx (11 tests)
 ✓ tests/unit/pdf-viewer.test.tsx (11 tests)
 ✓ tests/unit/queries.test.tsx (11 tests)
 ✓ tests/unit/comparisons.test.tsx (9 tests)
 ✓ tests/unit/evaluation.test.tsx (3 tests)

Test Files  14 passed (14)
Tests       78 passed (78)
Duration    6.39s

# Result: Exit code 0 (78/78 tests passed)
```

### Command 4: Next.js 15 Production Build
```bash
$ npm run build
> frontend@0.1.0 build
> next build

   ▲ Next.js 15.2.1
   Creating an optimized production build ...
 ✓ Compiled successfully
   Linting and checking validity of types     ✓
   Generating static pages (5/5)             ✓
   Finalizing page optimization               ✓

Route (app)                                              Size  First Load JS
┌ ○ /                                                 6.85 kB         113 kB
├ ○ /_not-found                                         977 B         102 kB
├ ○ /evaluation                                       4.24 kB         108 kB
├ ƒ /workspaces/[workspaceId]                         6.12 kB         110 kB
├ ƒ /workspaces/[workspaceId]/compare                 7.67 kB         111 kB
├ ƒ /workspaces/[workspaceId]/documents               8.18 kB         114 kB
├ ƒ /workspaces/[workspaceId]/documents/[documentId]  10.9 kB         115 kB
└ ƒ /workspaces/[workspaceId]/queries                 6.19 kB         110 kB
+ First Load JS shared by all                          101 kB

# Result: Exit code 0 (All 8 routes compiled and optimized)
```

### Command 5: Backend Offline Evaluation CLI Runner
```bash
$ .venv/bin/python -m app.services.evaluation.runner --offline
==========================================================================================
 ProofLens AI — Curated Regression Evaluation Summary
==========================================================================================
 Mode:            DETERMINISTIC_OFFLINE_FIXTURE
 Cases Evaluated: 25 total (10 Factual, 5 Comparison, 10 Negative)
 Passed / Failed: 25 passed / 0 failed
------------------------------------------------------------------------------------------
 Hard Quality Gate: [PASSED] (All 7 targets satisfied)
==========================================================================================

# Result: Exit code 0 (25/25 cases passed, hard gate passed)
```

### Command 6: Backend Pytest Regression Suite
```bash
$ backend/.venv/bin/pytest backend/tests/
====================== 214 passed, 437 warnings in 12.44s ======================

# Result: Exit code 0 (214/214 tests passed)
```

---

## 8. Blockers, Non-Blocking Findings & Unverified Claims

### 8.1 Critical Blockers
**None.** Zero blockers identified. All requirements from PRD, Technical Design, and Roadmap have been satisfied.

### 8.2 Non-Blocking Observations
1. **Target Label Discrepancies in UI:**  
   The UI targets displayed on `/evaluation` list Citation Integrity as "Target: ≥95%" (backend hard target is 100%), Negative Abstention as "Target: ≥95%" (backend target is ≥90%), False Abstention as "Target: ≤5%" (backend target is ≤10%), and Comparison Quality as "Target: ≥90%" (backend target is ≥80%). In all cases, the measured values (100.0% and 0.0%) satisfy both the frontend's stricter targets and the backend's official thresholds.
2. **Comparison History Detail Schema:**  
   The backend endpoint `GET /api/v1/workspaces/{workspace_id}/comparisons/{comparison_id}` returns a `SavedComparisonResponse` (which flattens citations and evidence from the underlying `QueryRun`). The frontend `ComparisonMatrix` component gracefully handles this by rendering executive synthesis, limitations, citations, and evidence even when individual finding taxonomy items are not saved to database storage.
3. **Evaluation Runner CLI vs Live:**  
   Live evaluation mode (`--live`) is intentionally not provisioned in the backend evaluation runner, which fails fast with an actionable error. The frontend `/evaluation` page correctly documents this design decision.

---

## 9. Final Recommendation

# **APPROVE FOR COMMIT**

The implementation of Combined Phases 5–7 represents a comprehensive, fully tested, evidence-grounded frontend integration. It adheres strictly to all architectural, security, and verification guardrails.
