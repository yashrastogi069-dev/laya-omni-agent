"""
omni_engine.contracts.research
==============================
Typed contracts and schemas for Phase R1: Deep Research Engine.

Adheres to Prime Directive & Repository Invariants:
- Evidence-Based Completion (Invariant 6): Every research claim must be backed
  by cryptographically hashed evidence passages in an immutable evidence ledger.
- Signals are First-Class (Invariant 7): Tracks relevance, stance (SUPPORTS, CONTRADICTS),
  and saturation signals explicitly.
- Strongly Typed Contracts (Invariant 4): Strict Pydantic validation forbidding undeclared fields.
- Prompt-Injection Immunity: All external web evidence is encapsulated with provenance hashes.
"""

from enum import Enum
import hashlib
from typing import Any, Dict, List, Optional
import unicodedata
from pydantic import Field, field_validator
from omni_engine.contracts.base import BaseContractModel


class EvidenceStance(str, Enum):
    """Semantic stance of evidence passage relative to query or hypothesis."""
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    NEUTRAL = "neutral"


class ClaimVerificationStatus(str, Enum):
    """Cryptographic and semantic verification state of an individual claim."""
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    CONTRADICTED = "contradicted"
    HALLUCINATED = "hallucinated"


class FetchMethod(str, Enum):
    """Mechanism used to retrieve external web content."""
    TAVILY_SEARCH = "tavily_search"
    TAVILY_EXTRACT = "tavily_extract"
    SCRAPLING = "scrapling"
    BS4 = "bs4"
    PLAYWRIGHT = "playwright"
    MOCK_FIXTURE = "mock_fixture"


class EvidenceItem(BaseContractModel):
    """A bounded, immutable passage of evidence extracted from a web source."""
    evidence_id: str = Field(..., description="Unique evidence ID (ev_<hash[:10]>)")
    canonical_url: str = Field(..., description="Normalized URL where content was retrieved")
    title: str = Field(default="", description="Source page title")
    publisher: str = Field(default="", description="Domain or publisher name")
    retrieval_timestamp: float = Field(..., description="Epoch timestamp of retrieval")
    fetch_method: FetchMethod = Field(default=FetchMethod.SCRAPLING, description="Fetch mechanism used")
    content_hash: str = Field(..., description="SHA-256 hash of NFKC-normalized passage text")
    passage_text: str = Field(..., description="Exact textual excerpt (200-1200 characters)")
    relevance_score: float = Field(default=0.5, ge=0.0, le=1.0, description="System 1 relevance score")
    stance: EvidenceStance = Field(default=EvidenceStance.NEUTRAL, description="Evidence stance relative to query")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="Confidence in relevance assessment")
    notes: Optional[str] = Field(default=None, description="Additional extraction notes")

    @classmethod
    def create(
        cls,
        canonical_url: str,
        passage_text: str,
        title: str = "",
        publisher: str = "",
        retrieval_timestamp: Optional[float] = None,
        fetch_method: FetchMethod = FetchMethod.SCRAPLING,
        relevance_score: float = 0.5,
        stance: EvidenceStance = EvidenceStance.NEUTRAL,
        confidence: float = 0.5,
        notes: Optional[str] = None,
    ) -> "EvidenceItem":
        """Factory helper creating an immutable EvidenceItem with deterministic SHA-256 ID."""
        import time
        norm_text = unicodedata.normalize("NFKC", passage_text.strip())
        h = hashlib.sha256(norm_text.encode("utf-8")).hexdigest()
        ev_id = f"ev_{h[:10]}"
        ts = retrieval_timestamp if retrieval_timestamp is not None else time.time()

        return cls(
            evidence_id=ev_id,
            canonical_url=canonical_url,
            title=title,
            publisher=publisher,
            retrieval_timestamp=ts,
            fetch_method=fetch_method,
            content_hash=h,
            passage_text=norm_text,
            relevance_score=relevance_score,
            stance=stance,
            confidence=confidence,
            notes=notes,
        )


class ResearchClaim(BaseContractModel):
    """An atomic factual claim extracted from synthesis with cited evidence IDs."""
    claim_id: str = Field(..., description="Unique claim identifier, e.g. 'claim_001'")
    claim_text: str = Field(..., description="Statement of fact")
    cited_evidence_ids: List[str] = Field(default_factory=list, description="Evidence IDs cited by this claim")
    verification_status: ClaimVerificationStatus = Field(
        default=ClaimVerificationStatus.UNVERIFIED,
        description="Verification outcome against evidence ledger",
    )
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="Verification confidence")
    rationale: Optional[str] = Field(default=None, description="Verification rationale")


class ResearchBudget(BaseContractModel):
    """Strict resource constraints and saturation criteria governing research execution."""
    max_search_queries: int = Field(default=5, ge=1, le=10, description="Maximum search queries executed")
    max_urls: int = Field(default=20, ge=1, le=50, description="Maximum candidate URLs discovered")
    max_pages_per_domain: int = Field(default=3, ge=1, le=5, description="Maximum pages crawled per domain")
    max_total_pages: int = Field(default=10, ge=1, le=20, description="Maximum total pages fetched")
    max_crawl_depth: int = Field(default=1, ge=0, le=1, description="Maximum crawl depth hops (0=search only, 1=direct links)")
    max_wall_time_sec: float = Field(default=60.0, ge=5.0, le=120.0, description="Hard deadline in seconds")
    evidence_saturation_threshold: float = Field(
        default=0.85,
        ge=0.5,
        le=1.0,
        description="Saturation score threshold (1.0 - novel_yield) stopping criteria",
    )


class ResearchTelemetry(BaseContractModel):
    """Observability telemetry capturing research execution metrics."""
    queries_executed: int = Field(default=0, ge=0)
    urls_discovered: int = Field(default=0, ge=0)
    urls_fetched: int = Field(default=0, ge=0)
    pages_crawled: int = Field(default=0, ge=0)
    passages_extracted: int = Field(default=0, ge=0)
    passages_deduplicated: int = Field(default=0, ge=0)
    evidence_retained: int = Field(default=0, ge=0)
    hallucinated_citations_count: int = Field(default=0, ge=0)
    wall_time_sec: float = Field(default=0.0, ge=0.0)
    saturation_reached: bool = Field(default=False)
    fetch_methods_used: Dict[str, int] = Field(default_factory=dict)


class ResearchDossier(BaseContractModel):
    """Complete, verified research output envelope."""
    query: str = Field(..., description="Original user research objective")
    sub_queries: List[str] = Field(default_factory=list, description="Decomposed research queries")
    summary: str = Field(..., description="Synthesized dossier with bracketed citations [ev_...]")
    claims: List[ResearchClaim] = Field(default_factory=list, description="Verified claims with citations")
    evidence_ledger: Dict[str, EvidenceItem] = Field(
        default_factory=dict,
        description="Immutable evidence registry mapped by evidence_id",
    )
    telemetry: ResearchTelemetry = Field(default_factory=ResearchTelemetry, description="Execution telemetry")
