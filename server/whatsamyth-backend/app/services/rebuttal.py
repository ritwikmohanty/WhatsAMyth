"""
Deadly Rebuttal Generator
Creates punchy, shareable WhatsApp rebuttals with emojis and formatting.
"""

import re
import logging
from typing import List, Optional, Dict, Any
from app.models import ClaimStatus

logger = logging.getLogger(__name__)


class RebuttalGenerator:
    """
    Generates WhatsApp-optimized rebuttals with:
    - Emojis (❌ ✅ ⚠️)
    - WhatsApp markdown (*bold*, _italic_)
    - DO NOT FORWARD warnings
    - Authoritative tone
    - Source citations
    """

    # Status emojis
    STATUS_EMOJIS = {
        ClaimStatus.FALSE: "❌",
        ClaimStatus.TRUE: "✅",
        ClaimStatus.MISLEADING: "⚠️",
        ClaimStatus.PARTIALLY_TRUE: "⚠️",
        ClaimStatus.UNVERIFIABLE: "❓",
        ClaimStatus.UNKNOWN: "❓"
    }

    # Authority markers for different domains
    AUTHORITATIVE_SOURCES = {
        "pib.gov.in": "PIB Fact Check",
        "who.int": "WHO",
        "cdc.gov": "CDC",
        "mohfw.gov.in": "Ministry of Health",
        "ndma.gov.in": "NDMA",
        "factcheck.org": "FactCheck.org",
        "snopes.com": "Snopes",
        "altnews.in": "Alt News",
        "boomlive.in": "BOOM",
        "vishvasnews.com": "Vishvas News"
    }

    def generate_deadly_rebuttal(
        self,
        status: ClaimStatus,
        claim_text: str,
        evidence_snippets: List[str],
        llm_explanation: str,
        confidence: float = 0.8
    ) -> Dict[str, str]:
        """
        Generate a deadly, shareable WhatsApp rebuttal.

        Args:
            status: Verdict status (TRUE/FALSE/etc)
            claim_text: Original claim text
            evidence_snippets: Evidence used
            llm_explanation: LLM-generated explanation
            confidence: Confidence score

        Returns:
            Dict with 'short_reply' and 'long_reply'
        """
        # Extract authoritative sources
        sources = self._extract_sources(evidence_snippets)

        # Generate short reply
        short_reply = self._generate_short_reply(
            status, claim_text, llm_explanation, sources, confidence
        )

        # Generate long reply
        long_reply = self._generate_long_reply(
            status, claim_text, llm_explanation, evidence_snippets, sources
        )

        return {
            "short_reply": short_reply,
            "long_reply": long_reply
        }

    def _generate_short_reply(
        self,
        status: ClaimStatus,
        claim_text: str,
        explanation: str,
        sources: List[str],
        confidence: float
    ) -> str:
        """Generate substantive, persuasive short reply for WhatsApp in Myth/Fact format."""
        emoji = self.STATUS_EMOJIS.get(status, "❓")

        # Status line
        if status == ClaimStatus.FALSE:
            status_line = f"{emoji} *FALSE - This is a HOAX!*"
            warning = "\n\n⚠️ *DO NOT FORWARD*"
        elif status == ClaimStatus.TRUE:
            status_line = f"{emoji} *TRUE - This is accurate*"
            warning = ""
        elif status == ClaimStatus.MISLEADING:
            status_line = f"{emoji} *MISLEADING - Partly incorrect*"
            warning = "\n\n⚠️ *Verify before sharing*"
        else:
            status_line = f"{emoji} *UNVERIFIED*"
            warning = "\n\n⚠️ *Check official sources*"

        # Extract claim summary (first 1000 chars)
        claim_summary = claim_text

        # Build Myth/Fact section
        if status == ClaimStatus.FALSE:
            myth_fact = f"*Myth:* {claim_summary}\n\n*Fact:* {explanation}"

            # Add "Why this matters" for hoaxes
            if any(word in claim_text.lower() for word in ['forward', 'share', 'urgent', 'breaking']):
                myth_fact += "\n\n*Why this is dangerous:* Spreading such messages creates panic and helps misinformation spread."

        elif status == ClaimStatus.TRUE:
            myth_fact = f"*Claim:* {claim_summary}\n\n*Verification:* {explanation}"
        else:
            myth_fact = f"*Claim:* {claim_summary}\n\n*Status:* {explanation}"

        # Source attribution
        if sources:
            source_line = f"\n\n✅ *Verified by:* {', '.join(sources[:3])}"
        else:
            source_line = ""

        # Assemble full reply
        short_reply = f"{status_line}\n\n{myth_fact}{warning}{source_line}"

        return short_reply

    def _generate_long_reply(
        self,
        status: ClaimStatus,
        claim_text: str,
        explanation: str,
        evidence_snippets: List[str],
        sources: List[str]
    ) -> str:
        """Generate detailed explanation."""
        emoji = self.STATUS_EMOJIS.get(status, "❓")

        # Header
        if status == ClaimStatus.FALSE:
            header = f"{emoji} *FACT CHECK: FALSE*\n{'='*30}"
        elif status == ClaimStatus.TRUE:
            header = f"{emoji} *FACT CHECK: TRUE*\n{'='*30}"
        else:
            header = f"{emoji} *FACT CHECK: {status.value}*\n{'='*30}"

        # Claim section
        claim_summary = self._summarize_claim(claim_text)
        claim_section = f"\n\n*Claim:*\n{claim_summary}"

        # Verdict section
        verdict_section = f"\n\n*Verdict:*\n{explanation}"

        # Evidence section
        if evidence_snippets:
            evidence_text = "\n\n".join([f"• {e[:200]}..." if len(e) > 200 else f"• {e}" for e in evidence_snippets[:3]])
            evidence_section = f"\n\n*Evidence:*\n{evidence_text}"
        else:
            evidence_section = ""

        # Sources section
        if sources:
            sources_section = f"\n\n*Official Sources:*\n{', '.join(sources)}"
        else:
            sources_section = ""

        # Footer
        if status == ClaimStatus.FALSE:
            footer = f"\n\n⚠️ *This is misinformation. Do not share.*\n\n_Fact-checked by WhatsAMyth_"
        else:
            footer = f"\n\n_Fact-checked by WhatsAMyth_"

        return f"{header}{claim_section}{verdict_section}{evidence_section}{sources_section}{footer}"

    def _make_punchy_false(self, message: str, claim_text: str) -> str:
        """Make FALSE verdicts more punchy and commanding."""
        # Common false claim patterns
        if "never" in message.lower():
            return message.upper() + "!"

        # Detect hoax patterns
        if any(word in claim_text.lower() for word in ["forward", "share", "whatsapp will", "account will be deleted"]):
            return f"*This is a common hoax!* {message}"

        # Authority misattribution
        if any(word in claim_text.lower() for word in ["pm", "minister", "government said", "official"]):
            return f"*No official statement was made.* {message}"

        # Health misinfo
        if any(word in claim_text.lower() for word in ["vaccine", "cure", "covid", "treatment"]):
            return f"*DANGEROUS MISINFORMATION!* {message}"

        return message

    def _summarize_claim(self, claim_text: str) -> str:
        """Summarize claim to 1-2 sentences."""
        # Take first 2 sentences
        sentences = re.split(r'[.!?]+', claim_text)
        summary = '. '.join(sentences[:2]).strip()

        if len(summary) > 2000:
            summary = summary

        return summary

    def _extract_sources(self, evidence_snippets: List[str]) -> List[str]:
        """Extract authoritative source names from evidence."""
        sources = set()

        for snippet in evidence_snippets:
            snippet_lower = snippet.lower()
            for domain, name in self.AUTHORITATIVE_SOURCES.items():
                if domain in snippet_lower or name.lower() in snippet_lower:
                    sources.add(name)

            # Also check for common authority mentions
            if "who" in snippet_lower and "world health" in snippet_lower:
                sources.add("WHO")
            if "cdc" in snippet_lower:
                sources.add("CDC")
            if "pib" in snippet_lower or "press information bureau" in snippet_lower:
                sources.add("PIB Fact Check")
            if "government" in snippet_lower and "india" in snippet_lower:
                sources.add("Government of India")

        return sorted(list(sources))


# Global singleton
_rebuttal_generator: Optional[RebuttalGenerator] = None


def get_rebuttal_generator() -> RebuttalGenerator:
    """Get the global rebuttal generator instance."""
    global _rebuttal_generator

    if _rebuttal_generator is None:
        _rebuttal_generator = RebuttalGenerator()

    return _rebuttal_generator
