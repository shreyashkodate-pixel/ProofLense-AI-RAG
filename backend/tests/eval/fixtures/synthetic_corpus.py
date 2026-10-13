"""ProofLens AI — Synthetic Evaluation Corpus Fixtures.

Provides deterministic in-memory representation of the 3 synthetic benchmark documents:
1. alpha_corp_annual_report_2023.pdf (3 pages, financial & operational overview)
2. beta_industries_sustainability_2023.pdf (3 pages, ESG, emissions, workforce safety)
3. gamma_technologies_q4_brief.pdf (2 pages, financial brief, climate roadmap)

Each chunk is assigned stable UUIDs, page numbers, and index numbers to support reproducible
retrieval and citation evaluation without live external services.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
import uuid

from app.repositories.query_repo import CandidateChunk


# Deterministic Workspace & Document UUIDs
WORKSPACE_ID = uuid.UUID("11111111-1111-4111-8111-111111111111")
ALPHA_DOC_ID = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
BETA_DOC_ID = uuid.UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
GAMMA_DOC_ID = uuid.UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc")

ALPHA_FILENAME = "alpha_corp_annual_report_2023.pdf"
BETA_FILENAME = "beta_industries_sustainability_2023.pdf"
GAMMA_FILENAME = "gamma_technologies_q4_brief.pdf"


@dataclass(frozen=True)
class FixtureChunk:
    chunk_alias: str
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_filename: str
    page_id: uuid.UUID
    page_number: int
    chunk_index: int
    text_content: str


# Synthetic Corpus Chunks
SYNTHETIC_CHUNKS: List[FixtureChunk] = [
    # --- Alpha Corp Annual Report 2023 ---
    # Page 1: Financial Highlights
    FixtureChunk(
        chunk_alias="chunk_alpha_p1_0",
        chunk_id=uuid.UUID("a0000001-0000-4000-8000-000000000001"),
        document_id=ALPHA_DOC_ID,
        document_filename=ALPHA_FILENAME,
        page_id=uuid.UUID("a1000000-0000-4000-8000-000000000001"),
        page_number=1,
        chunk_index=0,
        text_content=(
            "Alpha Corp Financial Highlights: Total consolidated revenue reached "
            "$125.4 million for FY2023, representing an increase of 14.2% year-over-year. "
            "Net income stood at $18.6 million in FY2023 compared to $14.1 million in FY2022. "
            "Operating margin expanded to 19.8% driven by software licensing efficiency."
        ),
    ),
    FixtureChunk(
        chunk_alias="chunk_alpha_p1_1",
        chunk_id=uuid.UUID("a0000001-0000-4000-8000-000000000002"),
        document_id=ALPHA_DOC_ID,
        document_filename=ALPHA_FILENAME,
        page_id=uuid.UUID("a1000000-0000-4000-8000-000000000001"),
        page_number=1,
        chunk_index=1,
        text_content=(
            "Executive Remarks: Chief Executive Officer Elena Vance noted strong adoption "
            "across North America. Free cash flow generation totaled $22.1 million, enabling "
            "strategic investments in cloud infrastructure and security compliance."
        ),
    ),
    # Page 2: Operations & Workforce
    FixtureChunk(
        chunk_alias="chunk_alpha_p2_0",
        chunk_id=uuid.UUID("a0000002-0000-4000-8000-000000000001"),
        document_id=ALPHA_DOC_ID,
        document_filename=ALPHA_FILENAME,
        page_id=uuid.UUID("a1000000-0000-4000-8000-000000000002"),
        page_number=2,
        chunk_index=2,
        text_content=(
            "Workforce & Talent: Alpha Corp employed 1,420 full-time employees across "
            "8 global offices as of December 31, 2023. Voluntary turnover remained below 5%, "
            "reflecting competitive benefits and flexible workplace arrangements."
        ),
    ),
    FixtureChunk(
        chunk_alias="chunk_alpha_p2_1",
        chunk_id=uuid.UUID("a0000002-0000-4000-8000-000000000002"),
        document_id=ALPHA_DOC_ID,
        document_filename=ALPHA_FILENAME,
        page_id=uuid.UUID("a1000000-0000-4000-8000-000000000002"),
        page_number=2,
        chunk_index=3,
        text_content=(
            "Research & Engineering: Investment in research and development reached "
            "$24.8 million, or 19.8% of total revenue. Core R&D initiatives centered on "
            "real-time data indexing and automated schema validation frameworks."
        ),
    ),
    FixtureChunk(
        chunk_alias="chunk_alpha_p2_2",
        chunk_id=uuid.UUID("a0000002-0000-4000-8000-000000000003"),
        document_id=ALPHA_DOC_ID,
        document_filename=ALPHA_FILENAME,
        page_id=uuid.UUID("a1000000-0000-4000-8000-000000000002"),
        page_number=2,
        chunk_index=4,
        text_content=(
            "Corporate Facilities: The global corporate headquarters is situated in "
            "Austin, Texas. Regional operational hubs are located in London, Tokyo, and Sydney. "
            "Enterprise net retention rate stood at 118% with zero major churn incidents."
        ),
    ),
    # Page 3: ESG & Climate
    FixtureChunk(
        chunk_alias="chunk_alpha_p3_0",
        chunk_id=uuid.UUID("a0000003-0000-4000-8000-000000000001"),
        document_id=ALPHA_DOC_ID,
        document_filename=ALPHA_FILENAME,
        page_id=uuid.UUID("a1000000-0000-4000-8000-000000000003"),
        page_number=3,
        chunk_index=5,
        text_content=(
            "Environmental Governance: Scope 1 and Scope 2 greenhouse gas emissions "
            "totaled 4,200 metric tons of CO2e in 2023. 65% of electricity across corporate "
            "facilities was sourced from certified renewable grids."
        ),
    ),
    FixtureChunk(
        chunk_alias="chunk_alpha_p3_1",
        chunk_id=uuid.UUID("a0000003-0000-4000-8000-000000000002"),
        document_id=ALPHA_DOC_ID,
        document_filename=ALPHA_FILENAME,
        page_id=uuid.UUID("a1000000-0000-4000-8000-000000000003"),
        page_number=3,
        chunk_index=6,
        text_content=(
            "Board Governance: The Board of Directors consists of 7 members, of whom "
            "5 are classified as independent directors. Audit and compensation committees "
            "are composed 100% of independent members."
        ),
    ),

    # --- Beta Industries Sustainability Report 2023 ---
    # Page 1: Sustainability Framework & Energy
    FixtureChunk(
        chunk_alias="chunk_beta_p1_0",
        chunk_id=uuid.UUID("b0000001-0000-4000-8000-000000000001"),
        document_id=BETA_DOC_ID,
        document_filename=BETA_FILENAME,
        page_id=uuid.UUID("b1000000-0000-4000-8000-000000000001"),
        page_number=1,
        chunk_index=0,
        text_content=(
            "Energy & Manufacturing: Beta Industries powered 92% of manufacturing operations "
            "through on-site solar and contracted wind energy in 2023. Energy intensity decreased "
            "by 8.4% per metric ton of manufactured goods across 14 dedicated production plants."
        ),
    ),
    FixtureChunk(
        chunk_alias="chunk_beta_p1_1",
        chunk_id=uuid.UUID("b0000001-0000-4000-8000-000000000002"),
        document_id=BETA_DOC_ID,
        document_filename=BETA_FILENAME,
        page_id=uuid.UUID("b1000000-0000-4000-8000-000000000001"),
        page_number=1,
        chunk_index=1,
        text_content=(
            "Water Stewardship: Closed-loop water filtration systems recycled 1.2 million "
            "cubic meters of industrial water in 2023, minimizing freshwater withdrawal "
            "in drought-stressed production areas in Southern Europe."
        ),
    ),
    # Page 2: Greenhouse Gas Accounting & Climate Goals
    FixtureChunk(
        chunk_alias="chunk_beta_p2_0",
        chunk_id=uuid.UUID("b0000002-0000-4000-8000-000000000001"),
        document_id=BETA_DOC_ID,
        document_filename=BETA_FILENAME,
        page_id=uuid.UUID("b1000000-0000-4000-8000-000000000002"),
        page_number=2,
        chunk_index=2,
        text_content=(
            "Operational Emissions: Beta Industries emitted 4,200 metric tons of CO2e across "
            "Scope 1 and Scope 2 operations in 2023, identical to the prior year baseline. "
            "Scope 3 supply chain emissions were estimated at 18,900 metric tons of CO2e."
        ),
    ),
    FixtureChunk(
        chunk_alias="chunk_beta_p2_2",
        chunk_id=uuid.UUID("b0000002-0000-4000-8000-000000000002"),
        document_id=BETA_DOC_ID,
        document_filename=BETA_FILENAME,
        page_id=uuid.UUID("b1000000-0000-4000-8000-000000000002"),
        page_number=2,
        chunk_index=3,
        text_content=(
            "Long-Term Climate Target: Beta Industries formally committed to achieving "
            "Net Zero carbon emissions by 2040. Interim targets include a 50% absolute "
            "reduction across Scope 1 and 2 emissions by 2030."
        ),
    ),
    # Page 3: Workforce & Governance
    FixtureChunk(
        chunk_alias="chunk_beta_p3_0",
        chunk_id=uuid.UUID("b0000003-0000-4000-8000-000000000001"),
        document_id=BETA_DOC_ID,
        document_filename=BETA_FILENAME,
        page_id=uuid.UUID("b1000000-0000-4000-8000-000000000003"),
        page_number=3,
        chunk_index=4,
        text_content=(
            "Workforce Demographics: Total full-time workforce reached 3,850 employees worldwide. "
            "Female representation in management roles increased to 38%, up from 34% in 2022."
        ),
    ),
    FixtureChunk(
        chunk_alias="chunk_beta_p3_1",
        chunk_id=uuid.UUID("b0000003-0000-4000-8000-000000000002"),
        document_id=BETA_DOC_ID,
        document_filename=BETA_FILENAME,
        page_id=uuid.UUID("b1000000-0000-4000-8000-000000000003"),
        page_number=3,
        chunk_index=5,
        text_content=(
            "Safety Metrics: Lost Time Injury Frequency Rate (LTIFR) was recorded at 0.42 "
            "per million hours worked. Zero fatalities were recorded across all manufacturing facilities. "
            "The supervisory board comprises 9 directors, including 6 independent members."
        ),
    ),

    # --- Gamma Technologies Q4 Brief ---
    # Page 1: Strategy & Financials
    FixtureChunk(
        chunk_alias="chunk_gamma_p1_0",
        chunk_id=uuid.UUID("c0000001-0000-4000-8000-000000000001"),
        document_id=GAMMA_DOC_ID,
        document_filename=GAMMA_FILENAME,
        page_id=uuid.UUID("c1000000-0000-4000-8000-000000000001"),
        page_number=1,
        chunk_index=0,
        text_content=(
            "Consolidated Financials: Gamma Technologies achieved FY2023 consolidated revenue "
            "of $125.4 million, matching market consensus. Net loss for FY2023 was $(4.2) million "
            "due to restructuring charges. Executive management operates out of Seattle, Washington."
        ),
    ),
    # Page 2: Climate Commitments & Operations
    FixtureChunk(
        chunk_alias="chunk_gamma_p2_0",
        chunk_id=uuid.UUID("c0000002-0000-4000-8000-000000000001"),
        document_id=GAMMA_DOC_ID,
        document_filename=GAMMA_FILENAME,
        page_id=uuid.UUID("c1000000-0000-4000-8000-000000000002"),
        page_number=2,
        chunk_index=1,
        text_content=(
            "Climate & Transition Roadmap: Gamma Technologies adopted an accelerated climate roadmap "
            "targeting Net Zero carbon emissions by 2030. Current renewable energy adoption stands "
            "at 45% of total consumption, while operational emissions reached 8,750 metric tons of CO2e in FY2023."
        ),
    ),
]

# Lookup map by alias
CHUNKS_BY_ALIAS: Dict[str, FixtureChunk] = {c.chunk_alias: c for c in SYNTHETIC_CHUNKS}
CHUNKS_BY_ID: Dict[uuid.UUID, FixtureChunk] = {c.chunk_id: c for c in SYNTHETIC_CHUNKS}
DOCUMENTS_MAP: Dict[str, uuid.UUID] = {
    ALPHA_FILENAME: ALPHA_DOC_ID,
    BETA_FILENAME: BETA_DOC_ID,
    GAMMA_FILENAME: GAMMA_DOC_ID,
}


def to_candidate_chunk(chunk: FixtureChunk, score: float, rank: int) -> CandidateChunk:
    """Convert FixtureChunk to CandidateChunk for production validator and orchestrator."""
    return CandidateChunk(
        chunk_id=chunk.chunk_id,
        chunk_text=chunk.text_content,
        chunk_index=chunk.chunk_index,
        document_id=chunk.document_id,
        document_filename=chunk.document_filename,
        page_id=chunk.page_id,
        page_number=chunk.page_number,
        similarity_score=score,
        rank=rank,
    )


@dataclass(frozen=True)
class MockDocument:
    """Lightweight document representation for citation and comparison validation."""

    id: uuid.UUID
    filename: str
    workspace_id: uuid.UUID = WORKSPACE_ID


MOCK_DOCUMENTS: Dict[str, MockDocument] = {
    ALPHA_FILENAME: MockDocument(id=ALPHA_DOC_ID, filename=ALPHA_FILENAME),
    BETA_FILENAME: MockDocument(id=BETA_DOC_ID, filename=BETA_FILENAME),
    GAMMA_FILENAME: MockDocument(id=GAMMA_DOC_ID, filename=GAMMA_FILENAME),
}

