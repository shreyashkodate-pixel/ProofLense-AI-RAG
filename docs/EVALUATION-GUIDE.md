# ProofLens AI — Evaluation and Quality Guide (`EVALUATION-GUIDE.md`)

**Document Type:** Engineering & QA Operations Guide  
**Governing Technical Design:** [docs/TECHNICAL-DESIGN.md](file:///Users/apple/Documents/Projects/ProofLense-AI/docs/TECHNICAL-DESIGN.md#L542) Section 7  
**Applies To:** Phase 10 Evaluation Framework  

---

## 1. Overview & Purpose

ProofLens AI employs an evidence-first document intelligence architecture. The Phase 10 evaluation framework provides a reproducible, regression-testing baseline for measuring the quality, reliability, citation provenance, abstention accuracy, comparison quality, and prompt-injection resilience across the entire RAG pipeline.

---

## 2. Benchmark Structure & Category Distribution

The initial curated regression benchmark is defined in [`backend/tests/eval/curated_benchmark.json`](file:///Users/apple/Documents/Projects/ProofLense-AI/backend/tests/eval/curated_benchmark.json) and comprises exactly **25 curated cases**:

### Category A: Factual Grounded Queries (10 cases)
- **IDs:** `factual_01` through `factual_10`
- **Objective:** Evaluates retrieval precision, top-score sufficiency, answer synthesis, and citation accuracy.
- **Requirements:** Each case defines `expected_document`, `expected_page_number` (1-indexed physical page), `expected_target_chunk_id`, `expected_quote`, and `expected_answer_contains`.
- **Target:** Retrieval Recall@5 $\ge 85\%$, False-Abstention Rate $\le 10\%$, Citation Integrity $100\%$.

### Category B: Cross-Document Comparisons (5 cases)
- **IDs:** `comparison_01` through `comparison_05`
- **Objective:** Evaluates balanced multi-document vector retrieval, two-stage noise filtering, relationship classification, and dual-source verification.
- **Relationships:** `agreement`, `contradiction`, `difference`, `not_found`.
- **Rubric:** Evaluated against an explicit 5-point rubric (Target: $\ge 80\%$, i.e. $\ge 4/5$).

### Category C: Negative & Out-of-Scope Queries (10 cases)
- **IDs:** `negative_01` through `negative_10`
- **Objective:** Evaluates deterministic vector abstention (`top_score < 0.65`), semantic abstention, and prevention of hallucinated citations.
- **Coverage:** Includes both completely unrelated queries (e.g. rocket propellants, clinical trials) and superficially matching queries that lack answering facts (e.g. unrecorded historical years or unrecorded jurisdictions).
- **Target:** Abstention Accuracy $\ge 90\%$.

> [!NOTE]
> **Sample Size & Limitations:**  
> The 25 curated cases serve as an automated **regression baseline** to catch code, threshold, or prompt regressions during continuous development. It is not statistical proof of open-ended real-world accuracy across arbitrary document domains. The suite should be expanded as edge cases or real failure modes are discovered.

---

## 3. Objective Metrics & Acceptance Targets

| Metric Name | Target | Formula / Definition | Required Interpretation |
| :--- | :---: | :--- | :--- |
| **Structural Citation Integrity** | **100%** | $\frac{\text{Cases with Valid Citations}}{\text{Total Cases Returning Citations}}$ | Every citation maps to an authorized chunk and ground-truth DB metadata. |
| **Negative-Set Abstention Accuracy** | **$\ge 90\%$** | $\frac{\text{Correctly Abstained Cases}}{\text{10 Negative Cases}}$ | Correct abstention across negative/out-of-scope cases. |
| **Factual-Set False-Abstention Rate** | **$\le 10\%$** | $\frac{\text{Falsely Abstained Factual Cases}}{\text{10 Factual Cases}}$ | Answerable factual queries incorrectly rejected. |
| **Retrieval Recall@5** | **$\ge 85\%$** | $\frac{\text{Factual Cases with Ground Truth in Top 5}}{\text{10 Factual Cases}}$ | Target chunk present in top-5 retrieved candidates. |
| **Comparison Quality Rubric** | **$\ge 80\%$** | $\frac{\text{Comparison Cases with Rubric Score } \ge 4/5}{\text{5 Comparison Cases}}$ | Accurate per-doc evidence, citations, classification, and limitations. |
| **Adversarial Prompt Resistance** | **$\ge 90\%$** | $\frac{\text{Neutralized Injection Attacks}}{\text{Total Injection Attempts}}$ | Jailbreaks failing to breach system instructions or extract secrets. |
| **Stage-Level Latency (P95)** | **$< 2,500\text{ ms}$** | 95th percentile of end-to-end execution | Logged across embedding, retrieval, generation, and validation. |

### Critical Distinction: Structural Citation Integrity vs. Semantic Claim Entailment
- **Structural Citation Integrity (100% Verified):** Mathematically guarantees that model citations resolve to real, authorized chunks in PostgreSQL with correct physical page numbers. Fabricated or cross-tenant IDs are completely eradicated.
- **Semantic Claim Entailment:** Structural citation validity does not mathematically prove that the cited excerpt logically entails the claim. Semantic entailment is evaluated via human review against the comparison rubric or exploratory LLM-as-judge scoring.

---

## 4. Cross-Document Comparison Quality Rubric

Each comparison case is evaluated on a 5-point repeatable rubric:
1. **Document Identification (1 pt):** Correctly identifies and scopes authorized target documents.
2. **Evidence Accuracy (1 pt):** Accurately represents each document's stated position or metrics without distortion.
3. **Citation Validity (1 pt):** Supported findings include verified citations from authorized candidate chunks.
4. **Classification Correctness (1 pt):** Correctly categorizes the relationship (`agreement`, `contradiction`, `difference`, or `not_found`).
5. **Limitations Handled (1 pt):** Explicitly notes scope differences, reporting year variations, unit discrepancies, or missing information.

**Scoring Threshold:** A comparison case passes if it achieves $\ge 4/5$ points ($80\%$). The overall suite passes if $\ge 4$ of the 5 comparison cases pass ($\ge 80\%$).

---

## 5. Execution Commands

### A. Run Deterministic Offline Evaluation (Recommended for CI & Local Development)
Runs instantly using deterministic synthetic fixtures, verifying all schema rules, metrics, validators, and XML escaping without external cloud dependencies:

```bash
cd backend
.venv/bin/python -m app.services.evaluation.runner --offline --output eval_report.json
```

### B. Run Dedicated Evaluation Test Suite
Executes all unit, schema, rubric, live-guard, and adversarial injection tests:

```bash
cd backend
.venv/bin/python -m pytest -v tests/eval/
```

### C. Run Full Backend Test Suite
Executes all 192 backend unit, integration, and evaluation tests across Phases 1–10.1:

```bash
cd backend
.venv/bin/python -m pytest -v
```

### D. Live Evaluation Mode Safety Guard (`--live`)
> [!IMPORTANT]
> **Live Mode Safety Guard:** Live evaluation mode (`--live`) against live PostgreSQL/pgvector instances and Google Gemini API is intentionally guarded and not yet provisioned. Passing `--live` will explicitly reject execution with an actionable error:
> ```
> Live evaluation against PostgreSQL/pgvector and Gemini is not yet provisioned; run with --offline.
> ```
> and terminate with exit code 2 without writing or printing any report. This guarantees that synthetic fixture results are never masqueraded or emitted as live cloud measurements. Genuine live evaluation adapters will be introduced in subsequent infrastructure testing milestones.

---

## 6. How to Add a New Benchmark Case

To add a new case to `backend/tests/eval/curated_benchmark.json`:
1. Open `curated_benchmark.json`.
2. Ensure you add the corresponding synthetic chunk or text to `backend/tests/eval/fixtures/synthetic_corpus.py` if testing offline.
3. Define the case object following the schema in [`app/services/evaluation/schemas.py`](file:///Users/apple/Documents/Projects/ProofLense-AI/backend/app/services/evaluation/schemas.py).
4. Run schema validation:
   ```bash
   .venv/bin/pytest -v tests/eval/test_benchmark_schema.py
   ```
