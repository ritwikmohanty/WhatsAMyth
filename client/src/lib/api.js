export async function simulateAPICall(text) {
  await new Promise(r => setTimeout(r, 1500))

  const isWhatsAppHoax = text.toLowerCase().includes('whatsapp') && 
    (text.toLowerCase().includes('off') || text.toLowerCase().includes('shut') || 
     text.toLowerCase().includes('499') || text.toLowerCase().includes('delete'))

  const claims = []
  if (isWhatsAppHoax) {
    if (text.toLowerCase().includes('off') || text.toLowerCase().includes('shut')) {
      claims.push({
        text: "WhatsApp will shut down daily from 11:30 PM to 6:00 AM",
        verdict: "FALSE",
        confidence: 0.98,
        evidence: "WhatsApp operates 24/7 globally. No government has authority to mandate shutdown times for the platform."
      })
    }
    if (text.toLowerCase().includes('delete') || text.toLowerCase().includes('invalid')) {
      claims.push({
        text: "Accounts will be deleted if users don't forward this message",
        verdict: "FALSE",
        confidence: 0.99,
        evidence: "WhatsApp's official FAQ explicitly states they never delete accounts based on forwarding behavior."
      })
    }
    if (text.toLowerCase().includes('499') || text.toLowerCase().includes('charge') || text.toLowerCase().includes('fee')) {
      claims.push({
        text: "Users will be charged ₹499 to reactivate deleted accounts",
        verdict: "FALSE",
        confidence: 0.97,
        evidence: "WhatsApp is free to use. There are no reactivation fees mentioned in any official documentation."
      })
    }
    if (text.toLowerCase().includes('modi') || text.toLowerCase().includes('pm') || text.toLowerCase().includes('government')) {
      claims.push({
        text: "This message is from PM Narendra Modi / Government of India",
        verdict: "FALSE",
        confidence: 0.99,
        evidence: "Neither PMO nor any government ministry has issued such a statement. Official communications are made through PIB."
      })
    }
  }

  if (claims.length === 0) {
    claims.push({
      text: text.substring(0, 100) + (text.length > 100 ? "..." : ""),
      verdict: "UNKNOWN",
      confidence: 0.4,
      evidence: "This claim hasn't been verified yet. Please check official sources or wait for fact-checkers to review."
    })
  }

  return {
    isForward: text.toLowerCase().includes('forward') || text.length > 200,
    language: "en",
    claims,
    matchedCluster: isWhatsAppHoax ? {
      id: 42,
      name: "WhatsApp Shutdown & Account Deletion Scam",
      timesDebunked: 15847,
      firstSeen: "March 2019",
      regions: ["India", "Brazil", "Nigeria", "Indonesia"]
    } : null,
    sources: isWhatsAppHoax ? [
      { name: "WhatsApp FAQ", url: "https://faq.whatsapp.com/", type: "official" },
      { name: "PIB Fact Check", url: "https://factcheck.pib.gov.in/", type: "government" },
      { name: "Alt News", url: "https://altnews.in/", type: "factchecker" }
    ] : [],
    generatedRebuttal: isWhatsAppHoax ? 
      `❌ This WhatsApp message is FAKE.\n\n❌ There is no order from the Government of India or PM Modi to shut WhatsApp from 11:30 pm to 6:00 am.\n❌ WhatsApp does not delete accounts or charge ₹499 based on forwards.\n✅ If any such rule existed, it would be announced on the official WhatsApp website or PIB / MyGov – not via random forwards.\n\n🔁 Please STOP forwarding this message and share this clarification instead.` :
      `⚠️ We couldn't verify this claim with high confidence.\n\nPlease check official sources before sharing. If you believe this is misinformation, it will be reviewed by our fact-checkers.`
  }
}
