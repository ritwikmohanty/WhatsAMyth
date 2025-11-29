// API Configuration
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Submits a message for fact-checking via the backend API
 * POST /api/messages
 */
export async function submitMessage(text, source = 'web_form') {
  const response = await fetch(`${API_BASE_URL}/api/messages/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify({
      text,
      source,
      metadata: {
        platform_specific: {
          user_agent: navigator.userAgent,
          timestamp: new Date().toISOString()
        }
      }
    }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `HTTP error ${response.status}`);
  }

  return response.json();
}

/**
 * Fetches the list of claim clusters
 * GET /api/claims
 */
export async function getClaims({ limit = 20, offset = 0, status = null } = {}) {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  if (status) params.append('status', status);

  const response = await fetch(`${API_BASE_URL}/api/claims/?${params}`);
  
  if (!response.ok) {
    throw new Error(`Failed to fetch claims: ${response.status}`);
  }

  return response.json();
}

/**
 * Fetches detailed information about a specific claim cluster
 * GET /api/claims/{cluster_id}
 */
export async function getClaimDetail(clusterId) {
  const response = await fetch(`${API_BASE_URL}/api/claims/${clusterId}`);
  
  if (!response.ok) {
    if (response.status === 404) {
      throw new Error('Claim not found');
    }
    throw new Error(`Failed to fetch claim detail: ${response.status}`);
  }

  return response.json();
}

/**
 * Fetches dashboard statistics
 * GET /api/stats/overview
 */
export async function getStatsOverview() {
  const response = await fetch(`${API_BASE_URL}/api/stats/overview`);
  
  if (!response.ok) {
    throw new Error(`Failed to fetch stats: ${response.status}`);
  }

  return response.json();
}

/**
 * Fetches trend data for the specified number of days
 * GET /api/stats/trends
 */
export async function getTrends(days = 7) {
  const response = await fetch(`${API_BASE_URL}/api/stats/trends?days=${days}`);
  
  if (!response.ok) {
    throw new Error(`Failed to fetch trends: ${response.status}`);
  }

  return response.json();
}

/**
 * Helper to get the full audio URL from a relative path
 */
export function getAudioUrl(audioPath) {
  if (!audioPath) return null;
  if (audioPath.startsWith('http')) return audioPath;
  return `${API_BASE_URL}${audioPath}`;
}

/**
 * Helper to transform backend response to the format expected by ResultsView
 */
export function transformMessageResponse(backendResponse, originalText) {
  const {
    message_id,
    is_claim,
    cluster_id,
    cluster_status,
    short_reply,
    audio_url,
    needs_verification
  } = backendResponse;

  // If not a claim, return early response
  if (!is_claim) {
    return {
      isForward: originalText.toLowerCase().includes('forward') || originalText.length > 200,
      language: 'en',
      claims: [{
        text: originalText.substring(0, 150) + (originalText.length > 150 ? '...' : ''),
        verdict: 'NOT_A_CLAIM',
        confidence: 1.0,
        evidence: 'This message does not appear to contain a verifiable claim.'
      }],
      matchedCluster: null,
      sources: [],
      generatedRebuttal: 'ℹ️ This message does not appear to contain any verifiable claims.\n\nNo fact-check is needed for this content.',
      messageId: message_id,
      audioUrl: null
    };
  }

  // Map status to verdict format
  const statusMap = {
    'TRUE': 'TRUE',
    'FALSE': 'FALSE',
    'MISLEADING': 'MISLEADING',
    'UNKNOWN': 'UNKNOWN',
    'UNVERIFIABLE': 'UNVERIFIABLE',
    'PARTIALLY_TRUE': 'PARTIALLY_TRUE'
  };

  const verdict = statusMap[cluster_status] || 'UNKNOWN';
  
  // Build confidence score based on status
  const confidenceMap = {
    'TRUE': 0.95,
    'FALSE': 0.95,
    'MISLEADING': 0.85,
    'PARTIALLY_TRUE': 0.80,
    'UNKNOWN': 0.40,
    'UNVERIFIABLE': 0.50
  };

  const confidence = confidenceMap[cluster_status] || 0.5;

  return {
    isForward: originalText.toLowerCase().includes('forward') || originalText.length > 200,
    language: 'en',
    claims: [{
      text: originalText.substring(0, 150) + (originalText.length > 150 ? '...' : ''),
      verdict,
      confidence,
      evidence: short_reply || 'Analysis in progress...'
    }],
    matchedCluster: cluster_id ? {
      id: cluster_id,
      name: `Claim Cluster #${cluster_id}`,
      timesDebunked: 1,
      firstSeen: 'Just now',
      regions: ['Online']
    } : null,
    sources: [],
    generatedRebuttal: short_reply || '⚠️ This claim is being analyzed.\n\nPlease check back shortly for the full fact-check result.',
    messageId: message_id,
    clusterId: cluster_id,
    audioUrl: getAudioUrl(audio_url),
    needsVerification: needs_verification,
    clusterStatus: cluster_status
  };
}

/**
 * Enhanced result with cluster detail - to be called after getting cluster info
 */
export function enhanceResultWithClusterDetail(baseResult, clusterDetail) {
  if (!clusterDetail) return baseResult;

  const { 
    canonical_text, 
    topic, 
    status, 
    message_count, 
    first_seen_at, 
    last_seen_at,
    verdict,
    related_clusters 
  } = clusterDetail;

  // Format dates
  const formatDate = (dateStr) => {
    if (!dateStr) return 'Unknown';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-IN', { 
      month: 'short', 
      year: 'numeric' 
    });
  };

  // Extract sources from verdict
  const sources = verdict?.sources?.map(s => ({
    name: s.source_name || new URL(s.source_url).hostname,
    url: s.source_url,
    type: s.source_name?.toLowerCase().includes('gov') ? 'government' : 
          s.source_name?.toLowerCase().includes('pib') ? 'government' :
          s.source_name?.toLowerCase().includes('who') ? 'official' : 'factchecker'
  })) || [];

  return {
    ...baseResult,
    claims: [{
      text: canonical_text || baseResult.claims[0]?.text,
      verdict: status,
      confidence: verdict?.confidence_score || baseResult.claims[0]?.confidence,
      evidence: verdict?.short_reply || baseResult.claims[0]?.evidence
    }],
    matchedCluster: {
      id: baseResult.clusterId,
      name: topic ? `${topic} Claim` : `Claim Cluster #${baseResult.clusterId}`,
      timesDebunked: message_count || 1,
      firstSeen: formatDate(first_seen_at),
      regions: ['Online']
    },
    sources,
    generatedRebuttal: verdict?.short_reply || baseResult.generatedRebuttal,
    longReply: verdict?.long_reply,
    audioUrl: getAudioUrl(verdict?.audio_url) || baseResult.audioUrl,
    relatedClusters: related_clusters
  };
}

/**
 * Main function to submit and get full analysis
 * This combines the message submission with fetching cluster details
 */
export async function analyzeMessage(text) {
  // Step 1: Submit message for analysis
  const messageResponse = await submitMessage(text);
  
  // Step 2: Transform to frontend format
  let result = transformMessageResponse(messageResponse, text);
  
  // Step 3: If we have a cluster, fetch detailed info
  if (result.clusterId && !result.needsVerification) {
    try {
      const clusterDetail = await getClaimDetail(result.clusterId);
      result = enhanceResultWithClusterDetail(result, clusterDetail);
    } catch (error) {
      console.warn('Could not fetch cluster details:', error);
      // Continue with basic result
    }
  }

  return result;
}

// Export API base URL for other modules
export { API_BASE_URL };
