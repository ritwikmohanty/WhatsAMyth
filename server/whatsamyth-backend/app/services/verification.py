"""
Verification Service
Searches for evidence from authoritative sources and uses LLM to generate verdicts.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone  # <-- timezone-aware

import requests
from bs4 import BeautifulSoup

from app.config import get_settings
from app.models import ClaimStatus
from app.services.llm_client import summarize, get_llm_client

logger = logging.getLogger(__name__)

settings = get_settings()


@dataclass
class EvidenceResult:
    """A single piece of evidence from web search."""
    url: str
    title: str
    snippet: str
    source_name: str
    relevance_score: float = 0.0
    retrieved_at: datetime = None

    def __post_init__(self):
        if self.retrieved_at is None:
            # Use timezone-aware UTC timestamp (avoids deprecation warnings)
            self.retrieved_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_url": self.url,
            "source_name": self.source_name,
            "title": self.title,
            "snippet": self.snippet,
            "relevance_score": self.relevance_score,
            "retrieved_at": self.retrieved_at.isoformat() if self.retrieved_at else None
        }


@dataclass
class VerificationResult:
    """Result of claim verification."""
    status: ClaimStatus
    confidence_score: float
    short_reply: str
    long_reply: str
    sources: List[Dict[str, Any]]
    evidence_snippets: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "confidence_score": self.confidence_score,
            "short_reply": self.short_reply,
            "long_reply": self.long_reply,
            "sources": self.sources,
            "evidence_snippets": self.evidence_snippets
        }


class VerificationService:
    """
    Service for verifying claims by searching authoritative sources.

    Workflow:
    1. Search DuckDuckGo for the claim
    2. Filter results to authoritative domains
    3. Extract relevant snippets
    4. Use LLM to analyze evidence and generate verdict
    """

    # Authoritative domains for fact-checking
    AUTHORITATIVE_DOMAINS = [
        # Health organizations
        "who.int",
        "cdc.gov",
        "nih.gov",
        "fda.gov",
        "icmr.gov.in",
        "mohfw.gov.in",

        # Indian government
        "gov.in",
        "pib.gov.in",
        "ndma.gov.in",
        "imd.gov.in",
        "india.gov.in",
        "mygov.in",

        # Fact-checkers
        "factcheck.org",
        "snopes.com",
        "politifact.com",
        "fullfact.org",
        "altnews.in",
        "boomlive.in",
        "thequint.com",
        "vishvasnews.com",
        "factly.in",
        "newschecker.in",

        # News agencies (global)
        "reuters.com",
        "apnews.com",
        "afp.com",
        "bbc.com",
        "bbc.co.uk",

        # Scientific sources
        "nature.com",
        "science.org",
        "thelancet.com",
        "nejm.org",
        "pubmed.ncbi.nlm.nih.gov",

        # NEW: high-signal general sources
        "wikipedia.org",

        # NEW: major Indian news orgs (for deaths, politics, etc.)
        "hindustantimes.com",
        "timesofindia.com",
        "indiatoday.in",
        "indianexpress.com",
        "ndtv.com",
        "thehindu.com",
    ]

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

    # ----------------------------
    # SEARCH & EVIDENCE RETRIEVAL
    # ----------------------------

    def search_evidence(
        self,
        claim_text: str,
        max_results: int = 10
    ) -> List[EvidenceResult]:
        """
        Search for evidence related to a claim.

        Uses DuckDuckGo search and filters to authoritative domains.

        Args:
            claim_text: The claim to search for
            max_results: Maximum number of results to return

        Returns:
            List of EvidenceResult objects
        """
        results: List[EvidenceResult] = []

        # Try DuckDuckGo search
        ddg_results = self._search_duckduckgo(claim_text, max_results * 3)

        # Assign relevance scores based on domain
        for result in ddg_results:
            if self._is_authoritative_domain(result.url):
                result.relevance_score = 1.0
            else:
                result.relevance_score = 0.5
            results.append(result)

        # Deduplicate by URL
        seen_urls = set()
        unique_results: List[EvidenceResult] = []
        for r in results:
            if r.url not in seen_urls:
                seen_urls.add(r.url)
                unique_results.append(r)

        # Sort by relevance_score (authoritative first), fallback to original order
        unique_results.sort(key=lambda r: r.relevance_score, reverse=True)

        return unique_results[:max_results]

    def _search_duckduckgo(
        self,
        query: str,
        max_results: int = 20
    ) -> List[EvidenceResult]:
        """
        Search DuckDuckGo for the query.

        Uses the duckduckgo_search / ddgs package if available, otherwise HTML scraping.
        Applies a recency bias when supported.
        """
        results: List[EvidenceResult] = []

        # Try using duckduckgo_search or ddgs package first
        try:
            try:
                # Newer package name
                from ddgs import DDGS  # type: ignore
                logger.info("Using ddgs.DDGS for DuckDuckGo search")
            except ImportError:
                from duckduckgo_search import DDGS  # type: ignore
                logger.info("Using duckduckgo_search.DDGS for DuckDuckGo search")

            with DDGS() as ddgs:
                try:
                    # Prefer: recency + India-English region if supported
                    search_results = list(ddgs.text(
                        query,
                        max_results=max_results,
                        region="in-en",
                        safesearch="moderate",
                        timelimit="w",  # last week – important for death/hoax conflicts
                    ))
                except TypeError:
                    # Older versions may not support region/timelimit
                    search_results = list(ddgs.text(query, max_results=max_results))

                for item in search_results:
                    url = item.get("href", item.get("link", ""))
                    title = item.get("title", "")
                    snippet = item.get("body", item.get("snippet", ""))
                    results.append(EvidenceResult(
                        url=url,
                        title=title,
                        snippet=snippet,
                        source_name=self._extract_domain(url)
                    ))

            logger.info(f"DuckDuckGo search returned {len(results)} results")
            return results

        except ImportError:
            logger.warning("duckduckgo_search / ddgs not available, using HTML scraping")
        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {e}")

        # Fallback: HTML scraping
        return self._search_duckduckgo_html(query, max_results)

    def _search_duckduckgo_html(
        self,
        query: str,
        max_results: int = 20
    ) -> List[EvidenceResult]:
        """Fallback: search DuckDuckGo by scraping HTML."""
        results: List[EvidenceResult] = []

        try:
            url = "https://html.duckduckgo.com/html/"
            response = self.session.post(
                url,
                data={"q": query},
                timeout=15
            )

            if response.status_code != 200:
                logger.error(f"DuckDuckGo HTML search failed: {response.status_code}")
                return results

            soup = BeautifulSoup(response.text, "html.parser")

            for result in soup.select(".result"):
                title_elem = result.select_one(".result__title")
                link_elem = result.select_one(".result__url")
                snippet_elem = result.select_one(".result__snippet")

                if title_elem and link_elem:
                    # Extract actual URL from DuckDuckGo redirect
                    href = title_elem.find("a")
                    if href and href.get("href"):
                        # DuckDuckGo uses redirects, extract actual URL
                        actual_url = self._extract_ddg_url(href.get("href"))
                    else:
                        actual_url = link_elem.get_text(strip=True)

                    results.append(EvidenceResult(
                        url=actual_url,
                        title=title_elem.get_text(strip=True),
                        snippet=snippet_elem.get_text(strip=True) if snippet_elem else "",
                        source_name=self._extract_domain(actual_url)
                    ))

                if len(results) >= max_results:
                    break

            logger.info(f"DuckDuckGo HTML search returned {len(results)} results")

        except Exception as e:
            logger.error(f"DuckDuckGo HTML scraping failed: {e}")

        return results

    def _extract_ddg_url(self, ddg_url: str) -> str:
        """Extract actual URL from DuckDuckGo redirect URL."""
        import urllib.parse

        if "uddg=" in ddg_url:
            parsed = urllib.parse.parse_qs(urllib.parse.urlparse(ddg_url).query)
            if "uddg" in parsed:
                return urllib.parse.unquote(parsed["uddg"][0])

        return ddg_url

    def _extract_domain(self, url: str) -> str:
        """Extract domain name from URL."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc or parsed.path.split("/")[0]
            # Remove www prefix
            if domain.startswith("www."):
                domain = domain[4:]
            return domain
        except Exception:
            return url

    def _is_authoritative_domain(self, url: str) -> bool:
        """Check if URL is from an authoritative domain."""
        domain = self._extract_domain(url).lower()

        for auth_domain in self.AUTHORITATIVE_DOMAINS:
            if domain == auth_domain or domain.endswith("." + auth_domain):
                return True

        return False

    def fetch_page_content(self, url: str, max_chars: int = 5000) -> str:
        """
        Fetch and extract main text content from a URL.

        Args:
            url: URL to fetch
            max_chars: Maximum characters to extract

        Returns:
            Extracted text content
        """
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code != 200:
                return ""

            soup = BeautifulSoup(response.text, "html.parser")

            # Remove script and style elements
            for script in soup(["script", "style", "nav", "header", "footer", "aside"]):
                script.decompose()

            # Get text
            text = soup.get_text(separator=" ", strip=True)

            # Clean up whitespace
            text = re.sub(r'\s+', ' ', text)

            return text[:max_chars]

        except Exception as e:
            logger.error(f"Failed to fetch page content: {e}")
            return ""

    # ----------------------------
    # CLAIM VERIFICATION
    # ----------------------------

    def _maybe_add_death_query(self, claim_text: str, queries: List[str]) -> List[str]:
        """
        If the claim looks like a 'X is dead / died / passed away' statement,
        try to add a focused 'Name death' query.

        This is specifically to avoid the Dharmendra-style problem where
        generic queries lose the main entity and retrieve only old hoax debunks.
        """
        death_pattern = re.compile(
            r"\b(died|is dead|was found dead|passed away|death)\b",
            re.IGNORECASE
        )

        if not death_pattern.search(claim_text):
            return queries

        # crude heuristic: grab capitalized tokens as "name"
        name_tokens = re.findall(r"\b[A-Z][a-zA-Z]+\b", claim_text)
        if name_tokens:
            name = " ".join(name_tokens)
            death_query = f"{name} death"
            if death_query not in queries:
                queries.append(death_query)

        return queries

    def verify_claim(
        self,
        claim_text: str,
        existing_evidence: Optional[List[str]] = None
    ) -> VerificationResult:
        """
        Verify a claim by searching for evidence and using LLM analysis.

        Uses keyword extraction for smarter evidence search.

        Args:
            claim_text: The claim to verify
            existing_evidence: Optional pre-collected evidence

        Returns:
            VerificationResult with verdict and explanation
        """
        # Collect evidence
        if existing_evidence:
            evidence_snippets = existing_evidence
            sources: List[Dict[str, Any]] = []
        else:
            # Use keyword extraction to build better search queries
            from app.services.keywords import get_keyword_extractor

            keyword_extractor = get_keyword_extractor()
            search_queries = keyword_extractor.build_search_queries(
                claim_text,
                max_queries=2
            )

            # Ensure we don't lose the raw claim
            if claim_text not in search_queries:
                search_queries.append(claim_text)

            # Add a focused "Name death" query for death-type claims
            search_queries = self._maybe_add_death_query(claim_text, search_queries)

            # Deduplicate while preserving order
            seen_q = set()
            deduped_queries: List[str] = []
            for q in search_queries:
                if q not in seen_q:
                    seen_q.add(q)
                    deduped_queries.append(q)
            search_queries = deduped_queries

            logger.info(f"Search queries: {search_queries}")

            # Search with each query and combine results
            all_evidence_results: List[EvidenceResult] = []
            for query in search_queries:
                results = self.search_evidence(query, max_results=5)
                all_evidence_results.extend(results)

            # Fallback to original claim if no results
            if not all_evidence_results:
                all_evidence_results = self.search_evidence(claim_text, max_results=10)

            # Deduplicate by URL
            seen_urls = set()
            unique_results: List[EvidenceResult] = []
            for r in all_evidence_results:
                if r.url not in seen_urls:
                    seen_urls.add(r.url)
                    unique_results.append(r)

            evidence_snippets = [r.snippet for r in unique_results if r.snippet]
            sources = [r.to_dict() for r in unique_results]

            logger.info(
                f"Found {len(evidence_snippets)} evidence snippets from {len(sources)} sources"
            )

            # Optional: log a few sources/snippets for debugging
            for i, src in enumerate(sources[:5]):
                logger.info("SRC[%d] %s - %s", i, src["source_name"], src["title"])
                if i < len(evidence_snippets):
                    logger.info("SNIPPET[%d]: %s", i, evidence_snippets[i][:300])

        # Use LLM to analyze evidence
        llm_response = summarize(claim_text, evidence_snippets)

        # Parse LLM response
        return self._parse_llm_response(llm_response, sources, evidence_snippets)

    def _parse_llm_response(
        self,
        response: str,
        sources: List[Dict[str, Any]],
        evidence_snippets: List[str]
    ) -> VerificationResult:
        """Parse structured response from LLM."""
        # Default values
        status = ClaimStatus.UNKNOWN
        confidence = 0.5
        short_reply = "We could not verify this claim. Please check official sources."
        long_reply = "This claim requires further verification."

        if not response:
            return VerificationResult(
                status=status,
                confidence_score=confidence,
                short_reply=short_reply,
                long_reply=long_reply,
                sources=sources,
                evidence_snippets=evidence_snippets
            )

        # Parse STATUS
        status_match = re.search(r'STATUS:\s*(\w+)', response, re.IGNORECASE)
        if status_match:
            status_str = status_match.group(1).upper()
            status_mapping = {
                "TRUE": ClaimStatus.TRUE,
                "FALSE": ClaimStatus.FALSE,
                "MISLEADING": ClaimStatus.MISLEADING,
                "UNKNOWN": ClaimStatus.UNKNOWN,
                "UNVERIFIABLE": ClaimStatus.UNVERIFIABLE,
                "PARTIALLY_TRUE": ClaimStatus.PARTIALLY_TRUE,
            }
            status = status_mapping.get(status_str, ClaimStatus.UNKNOWN)

        # Parse CONFIDENCE
        conf_match = re.search(r'CONFIDENCE:\s*([\d.]+)', response, re.IGNORECASE)
        if conf_match:
            try:
                confidence = float(conf_match.group(1))
                confidence = max(0.0, min(1.0, confidence))
            except ValueError:
                pass

        # Parse SHORT_REPLY
        short_match = re.search(
            r'SHORT_REPLY:\s*(.+?)(?=\n[A-Z_]+:|$)',
            response,
            re.IGNORECASE | re.DOTALL
        )
        if short_match:
            short_reply = short_match.group(1).strip()
            # Truncate for WhatsApp
            if len(short_reply) > 200:
                short_reply = short_reply[:197] + "..."

        # Parse LONG_REPLY
        long_match = re.search(
            r'LONG_REPLY:\s*(.+?)(?=\n[A-Z_]+:|$)',
            response,
            re.IGNORECASE | re.DOTALL
        )
        if long_match:
            long_reply = long_match.group(1).strip()

        return VerificationResult(
            status=status,
            confidence_score=confidence,
            short_reply=short_reply,
            long_reply=long_reply,
            sources=sources,
            evidence_snippets=evidence_snippets
        )

    def summarize_evidence_with_llm(
        self,
        claim_text: str,
        snippets: List[str]
    ) -> Tuple[ClaimStatus, str, str, List[Dict[str, Any]]]:
        """
        Legacy interface: Summarize evidence using LLM.

        Returns:
            Tuple of (status, short_reply, long_reply, sources)
        """
        result = self.verify_claim(claim_text, existing_evidence=snippets)
        return (
            result.status,
            result.short_reply,
            result.long_reply,
            result.sources
        )


# Global singleton
_verification_service: Optional[VerificationService] = None


def get_verification_service() -> VerificationService:
    """Get the global verification service instance."""
    global _verification_service

    if _verification_service is None:
        _verification_service = VerificationService()

    return _verification_service
