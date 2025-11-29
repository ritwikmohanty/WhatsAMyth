"""
Common Hoax Library
Pre-written rebuttals for frequently circulating WhatsApp forwards.
Pattern-matched for instant, accurate responses.
"""

import re
from typing import Optional, Dict
from app.models import ClaimStatus


class HoaxLibrary:
    """
    Library of common WhatsApp hoaxes with pre-written, deadly rebuttals.
    """

    # Common hoaxes database
    COMMON_HOAXES = [
        {
            "patterns": [
                r"whatsapp.*(?:shut|off|down).*(?:11:?30|12:?00|midnight)",
                r"whatsapp.*(?:account|delete).*(?:forward|48 hours)",
                r"pm modi.*whatsapp.*forward",
            ],
            "category": "whatsapp_shutdown",
            "status": ClaimStatus.FALSE,
            "myth": "WhatsApp will shut down if you don't forward messages",
            "fact": "WhatsApp has NEVER announced shutdowns or asked users to forward messages to keep accounts active. This is a recurring hoax that has been debunked by WhatsApp Official and PIB Fact Check multiple times.",
            "why_dangerous": "This spreads unnecessary panic and wastes people's time forwarding fake messages.",
            "what_to_do": "Delete this message immediately. Do not forward. Check PIB Fact Check (pib.gov.in) for verified information.",
            "sources": ["PIB Fact Check", "WhatsApp Official", "Government of India"]
        },
        {
            "patterns": [
                r"(?:covid|corona).*vaccine.*(?:microchip|track|bill gates)",
                r"vaccine.*(?:chip|5g|control|dna)",
            ],
            "category": "vaccine_microchip",
            "status": ClaimStatus.FALSE,
            "myth": "COVID-19 vaccines contain microchips for tracking",
            "fact": "COVID-19 vaccines do NOT contain microchips, tracking devices, or any nanotechnology. They contain standard medical ingredients: mRNA (or inactivated virus), lipids, salts, and sugars. This has been confirmed by CDC, WHO, and independent fact-checkers worldwide.",
            "why_dangerous": "This discourages vaccination and puts lives at risk during a pandemic.",
            "what_to_do": "Get vaccinated from authorized centers. Verify health information only from WHO, CDC, or your country's health ministry.",
            "sources": ["WHO", "CDC", "Ministry of Health"]
        },
        {
            "patterns": [
                r"onion.*(?:pocket|heat|prevent|sun)",
                r"onion.*heatstroke",
            ],
            "category": "onion_heatstroke",
            "status": ClaimStatus.FALSE,
            "myth": "Keeping onions in your pocket prevents heatstroke",
            "fact": "There is NO scientific evidence that onions in pockets prevent heatstroke. Medical experts recommend: drinking plenty of water, staying in shade, wearing light clothes, and consuming ORS. Onions have no proven benefit for heatstroke prevention.",
            "why_dangerous": "Relying on unproven remedies can delay proper medical treatment during heat emergencies.",
            "what_to_do": "Stay hydrated, avoid direct sun during peak hours (12-3 PM), and seek medical help if you feel dizzy or nauseous.",
            "sources": ["NDMA", "Health Ministry", "Medical Association"]
        },
        {
            "patterns": [
                r"government.*arrest.*whatsapp.*(?:anti-national|political)",
                r"police.*track.*whatsapp.*(?:tonight|12 am)",
                r"home ministry.*whatsapp.*(?:jail|fine|penalty)",
            ],
            "category": "whatsapp_police_tracking",
            "status": ClaimStatus.FALSE,
            "myth": "Government will arrest people for sharing political messages on WhatsApp",
            "fact": "No such order exists from the Home Ministry or Government of India. Police do not monitor WhatsApp messages without proper legal warrants and court orders. PIB Fact Check has confirmed this is completely false.",
            "why_dangerous": "This creates fear and suppresses legitimate freedom of expression.",
            "what_to_do": "Verify all government announcements from official sources like PIB.gov.in or MyGov.in. Do not trust unverified forwards.",
            "sources": ["PIB Fact Check", "Home Ministry", "Government of India"]
        },
        {
            "patterns": [
                r"5g.*(?:corona|covid|virus)",
                r"5g.*(?:cancer|brain|radiation|health|danger)",
                r"5g tower.*(?:bird|death|immune)",
            ],
            "category": "5g_health_risks",
            "status": ClaimStatus.FALSE,
            "myth": "5G technology causes COVID-19, cancer, or other health issues",
            "fact": "5G technology does NOT cause COVID-19, cancer, or other health problems. WHO and international health organizations confirm that 5G networks operating within international guidelines pose no health risks. COVID-19 spread even in countries without 5G. Radio waves cannot cause viral infections.",
            "why_dangerous": "This has led to vandalism of telecom infrastructure and delays in connectivity improvements.",
            "what_to_do": "Trust WHO and scientific organizations for health information. 5G is safe technology used worldwide.",
            "sources": ["WHO", "International Health Organizations", "Scientific Studies"]
        },
        {
            "patterns": [
                r"aadhaar.*(?:deactivat|block|suspend).*(?:deadline|last date)",
                r"link.*aadhaar.*(?:bank|mobile).*(?:urgent|today|deadline)",
            ],
            "category": "aadhaar_deadline",
            "status": ClaimStatus.FALSE,
            "myth": "Aadhaar will be deactivated if not linked by deadline",
            "fact": "UIDAI (Unique Identification Authority of India) announces all genuine deadlines through official channels: uidai.gov.in. Fake deadline messages circulate regularly. Always verify from UIDAI official website before taking action.",
            "why_dangerous": "Creates panic and leads people to share personal information with fraudsters.",
            "what_to_do": "Check uidai.gov.in for authentic information. Never share Aadhaar details via WhatsApp or unknown links.",
            "sources": ["UIDAI", "Government of India", "PIB"]
        },
    ]

    def match_hoax(self, claim_text: str) -> Optional[Dict]:
        """
        Check if claim matches any known hoax pattern.

        Args:
            claim_text: The claim to check

        Returns:
            Hoax details if matched, None otherwise
        """
        claim_lower = claim_text.lower()

        for hoax in self.COMMON_HOAXES:
            for pattern in hoax["patterns"]:
                if re.search(pattern, claim_lower, re.IGNORECASE):
                    return hoax

        return None

    def generate_rebuttal(self, hoax: Dict) -> Dict[str, str]:
        """
        Generate a deadly rebuttal for a matched hoax.

        Args:
            hoax: Hoax dictionary from COMMON_HOAXES

        Returns:
            Dict with short_reply and long_reply
        """
        status_emoji = "❌" if hoax["status"] == ClaimStatus.FALSE else "✅"

        # Short reply (WhatsApp-optimized)
        short_reply = f"""{status_emoji} *FALSE - This is a HOAX!*

*Myth:* {hoax['myth']}

*Fact:* {hoax['fact']}

*Why this is dangerous:* {hoax['why_dangerous']}

⚠️ *DO NOT FORWARD*

✅ *Verified by:* {', '.join(hoax['sources'])}"""

        # Long reply (detailed)
        long_reply = f"""{status_emoji} *FACT CHECK: FALSE*
{'='*30}

*Claim:*
{hoax['myth']}

*Verdict:*
This claim is FALSE. {hoax['fact']}

*Why this matters:*
{hoax['why_dangerous']}

*What you should do:*
{hoax['what_to_do']}

*Official Sources:*
{', '.join(hoax['sources'])}

⚠️ *This is misinformation. Do not share.*

_Fact-checked by WhatsAMyth_"""

        return {
            "short_reply": short_reply,
            "long_reply": long_reply,
            "status": hoax["status"],
            "sources": hoax["sources"]
        }


# Global singleton
_hoax_library: Optional[HoaxLibrary] = None


def get_hoax_library() -> HoaxLibrary:
    """Get the global hoax library instance."""
    global _hoax_library

    if _hoax_library is None:
        _hoax_library = HoaxLibrary()

    return _hoax_library
