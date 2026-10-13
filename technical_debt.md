# ProofLens AI — Technical Debt & Architectural Invariants

## 1. Core Architectural Invariants

1. **Evidence-First Principle & Provenance Integrity:**
   - All generated answers must be strictly grounded in retrieved document chunks.
   - The system must preserve complete physical provenance (`document_id`, `filename`, `page_number`) across parsing, chunking, retrieval, and answering operations.
   - Citations must be validated server-side against actual retrieved passages.

2. **Explicit Abstention over Hallucination:**
   - If retrieved passages are inadequate, irrelevant, or absent, the system must return an explicit insufficient-evidence response rather than speculating.

3. **Page-Bounded Chunking Invariant:**
   - Text chunking strictly operates within individual physical pages.
   - **Hard Invariant:** Chunks are strictly prohibited from crossing or bridging physical page boundaries. Every chunk maintains valid 1-indexed `page_number` and sequential `chunk_index` (0-indexed per document).

4. **Snapshot Tombstone Citation Pattern:**
   - In [`Citation`](file:///Users/apple/Documents/Projects/ProofLense-AI/backend/app/models/citation.py), `chunk_id` is defined with `ondelete="SET NULL"`.
   - In addition to foreign keys, the citation table stores permanent snapshot fields (`quote_text`, `page_number`, `source_filename`).
   - If a source document or chunk is deleted, historical queries and audit trails remain intact with preserved provenance.

5. **Mandatory Rule Zero & Fail-Closed Security:**
   - Never open, read, print, inspect, or expose real secret files (`.env`, `.env.*`).
   - Production settings fail fast at startup if required variables (`DEMO_ACCESS_TOKEN`, `DATABASE_URL`, `DATABASE_SSL_REQUIRED`, `GEMINI_API_KEY`) are missing, empty, or insecure.
   - Backend secrets remain strictly on the backend and must never be exposed via Next.js `NEXT_PUBLIC_*` prefixes.

6. **Minimal & Direct Dependencies:**
   - Directly invoke the official Google GenAI SDK.
   - LangChain, LangGraph, multi-agent frameworks, OCR tools, and bloated orchestration libraries are strictly excluded from MVP scope.

7. **Document Content is Untrusted Input:**
   - Uploaded PDF content is treated as untrusted user data.
   - Prompt boundaries isolate document text to prevent prompt-injection attacks.

8. **Retry Idempotency:**
   - Retrying document extraction cleanly purges pre-existing `DocumentChunk` and `DocumentPage` records before inserting fresh records, preventing duplicate key violations (`uq_document_chunk_index`, `uq_document_page`).

---

## 2. Identified Technical Debt & Known Limitations

| ID | Item | Severity | Impact | Mitigation / Roadmap |
|---|---|---|---|---|
| **TD-01** | **Physical PDF Cleanup on Workspace Deletion** | Medium | `DELETE /api/v1/workspaces/{id}` cascades relational database rows cleanly via foreign keys, but does not currently delete the workspace's physical files in `data/uploads/workspaces/{id}/` from disk. | Add an explicit background folder purge in `delete_workspace_endpoint` or introduce a storage reconciliation sweep worker. |
| **TD-02** | **Live PostgreSQL Migration & Rollback Verification** | Medium | Alembic migration DDL has been verified via static SQL compilation (`alembic upgrade --sql` / `downgrade --sql`). Live execution against an isolated PostgreSQL instance remains pending. | Spin up an isolated Docker container with PostgreSQL 15+ and pgvector to execute live DDL migrations before production deployment. |
| **TD-03** | **Scanned Image PDFs Lack OCR** | Low (By Design) | Image-only and scanned PDFs yield zero extractable text and fail with `"Document appears to be scanned or contains no extractable text (OCR not supported in MVP)"`. | Working as designed for MVP per PRD; post-MVP roadmap includes Tesseract / Google Cloud Document AI OCR pipeline. |
| **TD-04** | **In-Process BackgroundTasks vs Distributed Queue** | Low | Document ingestion currently runs via FastAPI's built-in `BackgroundTasks` within the server event loop. If the server restarts during ingestion, the job must wait for `RecoveryWatchdog` to time it out after 600s. | For enterprise scale beyond MVP, transition to a Redis-backed queue (ARQ or Celery) with persistent job states. |
| **TD-05** | **Encrypted / Password-Protected PDFs** | Low | Encrypted PDFs fail with `PDFParsingError("Malformed or unreadable PDF: ...")`. No UI modal exists to input document passwords. | Documented MVP limitation; future enhancement can support user password inputs during upload. |
| **TD-06** | **In-Memory Heuristic Rate Limiter** | Low | Sliding-window rate limiter stores request timestamps in memory per IP address. In multi-instance deployments, counters are not shared. | In production multi-pod deployments, transition rate limiting to Redis or edge CDN rate limiting (Cloudflare/Render). |
| **TD-07** | **Live Cloud Evaluation Adapters** | Low | Evaluation runner intentionally guards `--live` with `NotImplementedError` and exit code 2. Evaluations currently run deterministically against synthetic fixtures (`--offline`). | Provision live database and Gemini API evaluation adapters during Phase 11 production deployment testing. |
| **TD-08** | **Local Filesystem Storage vs Cloud Object Storage** | Medium | Ingestion pipeline currently stores PDF uploads in local `./data/uploads/` directory. | Implement Supabase Storage or S3-compatible cloud object store driver before multi-pod Render deployment. |

---

## 3. Milestone Completion Status & Upcoming Roadmap

### Completed Milestones
- **Phase 1: Backend Scaffolding, Security & Configuration [COMPLETED]**
- **Phase 2: Relational Schema & pgvector Architecture [COMPLETED]**
- **Phase 3: Workspaces, Storage & Resilient Ingestion APIs [COMPLETED]**
- **Phase 4: PDF Extraction & Page-Aware Chunking Pipeline [COMPLETED]**
- **Phase 5: Gemini Embeddings & Vector Storage [COMPLETED]**
  - Integrated official Google GenAI SDK (`gemini-embedding-2`, 768 output dimensions, MRL).
  - Bounded batch generation, mathematical vector validation, exponential backoff retries.
  - Decoupled transaction boundaries and resume-on-retry semantics.
- **Phase 6 & 6.1: Grounded Q&A & Deterministic Citation Validation [COMPLETED]**
  - Workspace-scoped cosine similarity vector retrieval (`<=>`) on `document_chunks.embedding`.
  - Structured grounded synthesis using `gemini-3.8-flash` with XML evidence isolation and prompt-injection defenses.
  - Server-authoritative `CitationValidator` (100% resolution to PostgreSQL chunks; stripped hallucinations; 0 citations forces abstention).
  - Resolved Phase 6.1 candidate alias collisions and UUID mapping.
- **Phase 7 & 7.1: Cross-Document Comparison & Evidence Sufficiency [COMPLETED]**
  - Multi-document comparison engine with dual-source validation requirement for `agreement` / `contradiction`.
  - Global evidence sufficiency evaluation and Stage 2 noise filtering (`< 0.65` discarded before LLM synthesis).
  - Safe unambiguous `not_found` document attribution.
- **Phase 10 & 10.1: Security Hardening, AI Evaluation Suite & Live Safety Guard [COMPLETED]**
  - Curated 25-case benchmark across Factual (10), Comparison (5), and Negative (10) categories.
  - Exact metric calculations, nearest-rank P95 latencies, and 5-point comparison rubric.
  - CLI runner with terminal summary tables, JSON reports, and hard quality gate exit codes.
  - 10-vector adversarial prompt injection regression suite (100% attack resistance).
  - Phase 10.1 `--live` safety guard rejecting unprovisioned live connections with actionable exit code 2.

### Upcoming Phases
- **Phase 8: Next.js Frontend Foundation & Ingestion UI**
  - Next.js (App Router, TypeScript, Vanilla CSS design tokens).
  - Workspace manager, drag-and-drop PDF upload, ingestion progress indicators.
- **Phase 9: Grounded Q&A & Cross-Document Comparison UI**
  - Evidence & Citation inspector drawer with source text highlight.
  - Multi-document comparison matrix view.
- **Phase 11: Deployment Preparation & Production Hardening**
  - Render backend configuration and Vercel frontend deployment.
  - Supabase PostgreSQL + pgvector live connection verification.

