"""
Test multiple WhatsApp forwards with deadly rebuttal system
"""

from app.services.detection import is_claim, extract_canonical_claim, get_claim_topics
from app.services.llm_client import summarize
from app.services.keywords import get_keyword_extractor

# Test cases: various WhatsApp forwards
test_cases = [
    {
        "name": "WhatsApp Shutdown Hoax (Short)",
        "message": "WhatsApp will be off from tonight. PM Modi declared. Forward to all contacts or account will be deleted in 48 hours.",
        "evidence": [
            "WhatsApp has never announced shutdowns or account deletion for not forwarding messages.",
            "PIB Fact Check has debunked this hoax multiple times.",
        ]
    },
    {
        "name": "Vaccine Microchip (Long)",
        "message": """URGENT: COVID-19 vaccines contain tracking microchips!

Bill Gates and WHO are using vaccines to track everyone. Scientists have discovered that the vaccines have nanotechnology that can monitor your location 24/7.

They don't want you to know the truth! Share this message with everyone before it gets deleted by the government.

This is confirmed by multiple doctors who were silenced by big pharma.""",
        "evidence": [
            "CDC and WHO confirm COVID-19 vaccines do not contain microchips or tracking devices.",
            "Vaccines contain standard medical ingredients: mRNA, lipids, salts, and sugars.",
            "Bill Gates microchip conspiracy has been repeatedly debunked by fact-checkers.",
        ]
    },
    {
        "name": "Onion Heatstroke Prevention (Short)",
        "message": "Keep onion in your pocket to prevent heatstroke. Works 100%. Doctors confirmed. Forward urgently!",
        "evidence": [
            "NDMA and health authorities recommend hydration and shade to prevent heatstroke.",
            "There is no scientific evidence that onions in pockets prevent heatstroke.",
            "Medical experts advise drinking water and ORS, not onions.",
        ]
    },
    {
        "name": "False Arrest Notification (Medium)",
        "message": """BREAKING NEWS: Government has ordered arrest of anyone sharing anti-national messages on WhatsApp.

Police will track your messages from tonight 12 AM.

Penalty: 5 years jail + Rs 10 lakh fine

This order is from Home Ministry. Delete all political forwards immediately.

Share to save your friends!""",
        "evidence": [
            "No such order has been issued by the Home Ministry or Government of India.",
            "PIB Fact Check confirms this is fake news circulating on social media.",
            "Police do not monitor WhatsApp messages without proper legal procedures.",
        ]
    },
    {
        "name": "5G Tower Health Risk (Long)",
        "message": """ATTENTION: 5G towers are being installed in your area and causing serious health issues!

Scientists have proven that 5G radiation causes:
- Cancer
- Brain damage
- COVID-19 spread
- Bird deaths
- Weakened immune system

The government is hiding this information because they get paid by telecom companies.

In other countries, people are removing 5G towers. We should do the same.

Forward this to create awareness. Our health is in danger!""",
        "evidence": [
            "WHO states 5G technology does not pose health risks within international guidelines.",
            "Scientific studies have found no evidence linking 5G to COVID-19 or cancer.",
            "International health organizations confirm 5G is safe.",
        ]
    }
]


def test_forward(test_case):
    """Test a single WhatsApp forward"""
    print("\n" + "="*100)
    print(f"TEST: {test_case['name']}")
    print("="*100)

    message = test_case['message']
    evidence = test_case['evidence']

    # Detection
    is_a_claim = is_claim(message)
    print(f"\n[Detection] Is claim: {is_a_claim}")

    if not is_a_claim:
        print("   ❌ Not detected as claim - PROBLEM!")
        return

    # Canonical extraction
    canonical = extract_canonical_claim(message)
    print(f"\n[Canonical] {canonical[:100]}...")

    # Topics
    topics = get_claim_topics(canonical)
    print(f"\n[Topics] {topics}")

    # Keywords
    extractor = get_keyword_extractor()
    keywords = extractor.extract_keywords(canonical)
    print(f"\n[Keywords] {keywords[:5]}")

    # Generate deadly rebuttal
    result = summarize(canonical, evidence)

    # Extract sections
    if 'SHORT_REPLY:' in result:
        short = result.split('SHORT_REPLY:')[1].split('LONG_REPLY:')[0].strip()
        print("\n" + "="*100)
        print("SHORT REPLY (WhatsApp-ready):")
        print("="*100)
        print(short)

        # Check for deadly features
        has_emoji = any(char in short for char in ['❌', '✅', '⚠️', '❓'])
        has_bold = '*' in short
        has_warning = 'DO NOT' in short.upper() or 'WARNING' in short.upper()
        has_source = 'Verified by' in short or 'VERIFIED' in short

        print("\n[Quality Check]")
        print(f"  ✓ Has emoji: {has_emoji}")
        print(f"  ✓ Has bold: {has_bold}")
        print(f"  ✓ Has warning: {has_warning}")
        print(f"  ✓ Has source: {has_source}")

        if has_emoji and has_bold:
            print("  ✅ DEADLY REBUTTAL WORKING!")
        else:
            print("  ⚠️ Missing deadly features")
    else:
        print("\n❌ NO SHORT_REPLY FOUND - PROBLEM!")
        print(f"Raw result: {result[:200]}...")


if __name__ == "__main__":
    import sys

    # Write to file instead of console to avoid emoji encoding issues
    output_file = "test_results_detailed.txt"

    with open(output_file, 'w', encoding='utf-8') as f:
        # Redirect output
        original_stdout = sys.stdout
        sys.stdout = f

        print("#"*100)
        print("# TESTING DEADLY REBUTTAL SYSTEM WITH MULTIPLE WHATSAPP FORWARDS")
        print("#"*100)

        for test_case in test_cases:
            try:
                test_forward(test_case)
            except Exception as e:
                print(f"\nERROR: {e}")
                import traceback
                traceback.print_exc()

        print("\n\n" + "#"*100)
        print("# TEST COMPLETE")
        print("#"*100)

        # Restore stdout
        sys.stdout = original_stdout

    print(f"Results saved to {output_file}")
    print("Processing complete!")
