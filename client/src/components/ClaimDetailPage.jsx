import { useState, useEffect, useRef } from 'react'
import { 
  ArrowLeft, 
  XCircle, 
  CheckCircle, 
  AlertTriangle, 
  HelpCircle,
  Calendar,
  Database,
  ExternalLink,
  Copy,
  Share2,
  Volume2,
  VolumeX,
  Loader,
  Link as LinkIcon
} from 'lucide-react'
import { Button } from './ui/button'
import { Badge } from './ui/badge'
import { getClaimDetail, getAudioUrl } from '@/lib/api'

const VERDICT_CONFIG = {
  TRUE: { 
    icon: CheckCircle, 
    color: 'var(--accent-green)', 
    bgColor: 'rgba(0,214,125,0.1)', 
    borderColor: 'rgba(0,214,125,0.2)',
    label: 'Verified True'
  },
  FALSE: { 
    icon: XCircle, 
    color: 'var(--accent-red)', 
    bgColor: 'rgba(255,71,87,0.1)', 
    borderColor: 'rgba(255,71,87,0.2)',
    label: 'False'
  },
  MISLEADING: { 
    icon: AlertTriangle, 
    color: '#ffc107', 
    bgColor: 'rgba(255,193,7,0.1)', 
    borderColor: 'rgba(255,193,7,0.2)',
    label: 'Misleading'
  },
  PARTIALLY_TRUE: { 
    icon: AlertTriangle, 
    color: '#ffc107', 
    bgColor: 'rgba(255,193,7,0.1)', 
    borderColor: 'rgba(255,193,7,0.2)',
    label: 'Partially True'
  },
  UNKNOWN: { 
    icon: HelpCircle, 
    color: 'var(--text-muted)', 
    bgColor: 'rgba(96,96,112,0.1)', 
    borderColor: 'rgba(96,96,112,0.2)',
    label: 'Under Review'
  },
  UNVERIFIABLE: { 
    icon: HelpCircle, 
    color: 'var(--text-muted)', 
    bgColor: 'rgba(96,96,112,0.1)', 
    borderColor: 'rgba(96,96,112,0.2)',
    label: 'Unverifiable'
  }
}

export default function ClaimDetailPage({ clusterId, onBack }) {
  const [claim, setClaim] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [copied, setCopied] = useState(false)
  const [isPlaying, setIsPlaying] = useState(false)
  const audioRef = useRef(null)

  useEffect(() => {
    async function fetchClaimDetail() {
      if (!clusterId) return
      
      try {
        setLoading(true)
        setError(null)
        const data = await getClaimDetail(clusterId)
        setClaim(data)
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    fetchClaimDetail()
  }, [clusterId])

  const handleCopy = () => {
    const textToCopy = claim?.verdict?.short_reply || claim?.canonical_text || ''
    navigator.clipboard.writeText(textToCopy)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handlePlayAudio = () => {
    const audioUrl = getAudioUrl(claim?.verdict?.audio_url)
    if (!audioUrl) return
    
    if (!audioRef.current) {
      audioRef.current = new Audio(audioUrl)
      audioRef.current.onended = () => setIsPlaying(false)
      audioRef.current.onerror = () => {
        setIsPlaying(false)
        console.error('Failed to play audio')
      }
    }
    
    if (isPlaying) {
      audioRef.current.pause()
      audioRef.current.currentTime = 0
      setIsPlaying(false)
    } else {
      audioRef.current.play()
      setIsPlaying(true)
    }
  }

  const handleShare = async () => {
    const textToShare = claim?.verdict?.short_reply || claim?.canonical_text || ''
    if (navigator.share) {
      try {
        await navigator.share({
          title: 'WhatsAMyth Fact Check',
          text: textToShare,
          url: window.location.href
        })
      } catch (err) {
        console.log('Share cancelled')
      }
    } else {
      handleCopy()
    }
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return 'Unknown'
    const date = new Date(dateStr)
    return date.toLocaleDateString('en-IN', { 
      day: 'numeric', 
      month: 'long', 
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  if (loading) {
    return (
      <div className="min-h-screen py-12 px-6 md:px-10">
        <div className="max-w-4xl mx-auto">
          <Button
            onClick={onBack}
            variant="ghost"
            className="mb-8 hover:bg-transparent p-0 h-auto gap-2"
            style={{ color: 'var(--text-muted)' }}
          >
            <ArrowLeft className="w-4 h-4" />
            Back to claims
          </Button>
          
          <div className="flex items-center justify-center py-20">
            <Loader className="w-8 h-8 animate-spin" style={{ color: 'var(--accent-green)' }} />
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen py-12 px-6 md:px-10">
        <div className="max-w-4xl mx-auto">
          <Button
            onClick={onBack}
            variant="ghost"
            className="mb-8 hover:bg-transparent p-0 h-auto gap-2"
            style={{ color: 'var(--text-muted)' }}
          >
            <ArrowLeft className="w-4 h-4" />
            Back to claims
          </Button>
          
          <div 
            className="p-8 rounded-lg text-center"
            style={{ 
              background: 'rgba(255,71,87,0.1)', 
              border: '1px solid rgba(255,71,87,0.2)' 
            }}
          >
            <XCircle className="w-12 h-12 mx-auto mb-4" style={{ color: 'var(--accent-red)' }} />
            <h2 className="text-xl font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>
              Failed to load claim
            </h2>
            <p style={{ color: 'var(--text-secondary)' }}>{error}</p>
          </div>
        </div>
      </div>
    )
  }

  if (!claim) return null

  const verdictConfig = VERDICT_CONFIG[claim.status] || VERDICT_CONFIG.UNKNOWN
  const VerdictIcon = verdictConfig.icon

  return (
    <div className="min-h-screen py-12 px-6 md:px-10">
      <div className="max-w-4xl mx-auto">
        {/* Back Button */}
        <Button
          onClick={onBack}
          variant="ghost"
          className="mb-8 hover:bg-transparent p-0 h-auto gap-2 transition-colors"
          style={{ color: 'var(--text-muted)' }}
        >
          <ArrowLeft className="w-4 h-4" />
          Back to claims
        </Button>

        {/* Verdict Header */}
        <div 
          className="p-8 rounded-lg mb-8"
          style={{ 
            background: verdictConfig.bgColor,
            border: `2px solid ${verdictConfig.borderColor}`
          }}
        >
          <div className="flex items-center gap-4 mb-4">
            <div 
              className="w-16 h-16 rounded-full flex items-center justify-center"
              style={{ background: verdictConfig.borderColor }}
            >
              <VerdictIcon className="w-8 h-8" style={{ color: verdictConfig.color }} />
            </div>
            <div>
              <Badge 
                className="text-lg px-4 py-1.5 font-bold"
                style={{ 
                  background: verdictConfig.color,
                  color: 'white'
                }}
              >
                {claim.status}
              </Badge>
              <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
                {verdictConfig.label}
              </p>
            </div>
          </div>
          
          {claim.verdict?.confidence_score && (
            <div className="flex items-center gap-3 mt-4">
              <span className="text-sm" style={{ color: 'var(--text-muted)' }}>Confidence:</span>
              <div className="flex-1 h-2 rounded-full overflow-hidden" style={{ background: 'rgba(0,0,0,0.2)' }}>
                <div 
                  className="h-full rounded-full transition-all duration-500"
                  style={{ 
                    width: `${(claim.verdict.confidence_score * 100)}%`,
                    background: verdictConfig.color
                  }}
                />
              </div>
              <span className="text-sm font-medium" style={{ color: verdictConfig.color }}>
                {Math.round(claim.verdict.confidence_score * 100)}%
              </span>
            </div>
          )}
        </div>

        {/* Claim Text */}
        <div 
          className="p-6 rounded-lg mb-8"
          style={{ background: 'var(--bg-card)', border: '1px solid var(--border-subtle)' }}
        >
          <h2 className="text-sm uppercase tracking-wider mb-3 font-semibold" style={{ color: 'var(--text-muted)' }}>
            Claim
          </h2>
          <p className="text-xl font-medium leading-relaxed" style={{ color: 'var(--text-primary)' }}>
            "{claim.canonical_text}"
          </p>
          
          {claim.topic && (
            <Badge 
              variant="outline" 
              className="mt-4"
              style={{ borderColor: 'var(--border-subtle)', color: 'var(--text-secondary)' }}
            >
              Topic: {claim.topic}
            </Badge>
          )}
        </div>

        {/* Verdict Details */}
        {claim.verdict && (
          <div 
            className="p-6 rounded-lg mb-8"
            style={{ background: 'var(--bg-card)', border: '1px solid var(--border-subtle)' }}
          >
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm uppercase tracking-wider font-semibold" style={{ color: 'var(--text-muted)' }}>
                Fact Check Response
              </h2>
              <div className="flex gap-2">
                {claim.verdict.audio_url && (
                  <Button
                    onClick={handlePlayAudio}
                    variant="outline"
                    size="sm"
                    className="h-8 text-xs gap-1"
                  >
                    {isPlaying ? <VolumeX className="w-3.5 h-3.5" /> : <Volume2 className="w-3.5 h-3.5" />}
                    {isPlaying ? 'Stop' : 'Listen'}
                  </Button>
                )}
                <Button
                  onClick={handleCopy}
                  variant="outline"
                  size="sm"
                  className="h-8 text-xs gap-1"
                >
                  <Copy className="w-3.5 h-3.5" />
                  {copied ? 'Copied!' : 'Copy'}
                </Button>
                <Button
                  onClick={handleShare}
                  variant="outline"
                  size="sm"
                  className="h-8 text-xs gap-1"
                >
                  <Share2 className="w-3.5 h-3.5" />
                  Share
                </Button>
              </div>
            </div>
            
            {/* Short Reply */}
            {claim.verdict.short_reply && (
              <div className="mb-6">
                <h3 className="text-sm font-medium mb-2" style={{ color: 'var(--text-secondary)' }}>
                  Quick Response
                </h3>
                <pre 
                  className="whitespace-pre-wrap font-sans text-base leading-relaxed p-4 rounded-lg"
                  style={{ 
                    background: 'rgba(0,0,0,0.2)',
                    color: 'var(--text-primary)'
                  }}
                >
                  {claim.verdict.short_reply}
                </pre>
              </div>
            )}
            
            {/* Long Reply */}
            {claim.verdict.long_reply && (
              <div>
                <h3 className="text-sm font-medium mb-2" style={{ color: 'var(--text-secondary)' }}>
                  Detailed Explanation
                </h3>
                <pre 
                  className="whitespace-pre-wrap font-sans text-sm leading-relaxed p-4 rounded-lg"
                  style={{ 
                    background: 'rgba(0,0,0,0.2)',
                    color: 'var(--text-secondary)',
                    borderLeft: `3px solid ${verdictConfig.color}`
                  }}
                >
                  {claim.verdict.long_reply}
                </pre>
              </div>
            )}
          </div>
        )}

        {/* Sources */}
        {claim.verdict?.sources && claim.verdict.sources.length > 0 && (
          <div 
            className="p-6 rounded-lg mb-8"
            style={{ background: 'var(--bg-card)', border: '1px solid var(--border-subtle)' }}
          >
            <h2 className="text-sm uppercase tracking-wider mb-4 font-semibold" style={{ color: 'var(--text-muted)' }}>
              Sources
            </h2>
            <div className="space-y-3">
              {claim.verdict.sources.map((source, index) => (
                <a
                  key={index}
                  href={source.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-start gap-3 p-3 rounded-lg transition-colors hover:bg-white/5"
                  style={{ border: '1px solid var(--border-subtle)' }}
                >
                  <LinkIcon className="w-4 h-4 mt-0.5 flex-shrink-0" style={{ color: 'var(--accent-green)' }} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-sm" style={{ color: 'var(--text-primary)' }}>
                        {source.source_name || new URL(source.source_url).hostname}
                      </span>
                      <ExternalLink className="w-3 h-3" style={{ color: 'var(--text-muted)' }} />
                    </div>
                    {source.snippet && (
                      <p className="text-xs mt-1 line-clamp-2" style={{ color: 'var(--text-muted)' }}>
                        {source.snippet}
                      </p>
                    )}
                  </div>
                  {source.relevance_score && (
                    <Badge variant="outline" className="text-xs flex-shrink-0">
                      {Math.round(source.relevance_score * 100)}% match
                    </Badge>
                  )}
                </a>
              ))}
            </div>
          </div>
        )}

        {/* Metadata */}
        <div 
          className="p-6 rounded-lg"
          style={{ background: 'var(--bg-card)', border: '1px solid var(--border-subtle)' }}
        >
          <h2 className="text-sm uppercase tracking-wider mb-4 font-semibold" style={{ color: 'var(--text-muted)' }}>
            Claim Statistics
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center p-4 rounded-lg" style={{ background: 'rgba(0,0,0,0.2)' }}>
              <Database className="w-5 h-5 mx-auto mb-2" style={{ color: 'var(--accent-green)' }} />
              <div className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
                {claim.message_count?.toLocaleString() || 1}
              </div>
              <div className="text-xs" style={{ color: 'var(--text-muted)' }}>Times Seen</div>
            </div>
            <div className="text-center p-4 rounded-lg" style={{ background: 'rgba(0,0,0,0.2)' }}>
              <Calendar className="w-5 h-5 mx-auto mb-2" style={{ color: 'var(--accent-green)' }} />
              <div className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
                {formatDate(claim.first_seen_at).split(',')[0]}
              </div>
              <div className="text-xs" style={{ color: 'var(--text-muted)' }}>First Seen</div>
            </div>
            <div className="text-center p-4 rounded-lg" style={{ background: 'rgba(0,0,0,0.2)' }}>
              <Calendar className="w-5 h-5 mx-auto mb-2" style={{ color: 'var(--text-secondary)' }} />
              <div className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
                {formatDate(claim.last_seen_at).split(',')[0]}
              </div>
              <div className="text-xs" style={{ color: 'var(--text-muted)' }}>Last Seen</div>
            </div>
            <div className="text-center p-4 rounded-lg" style={{ background: 'rgba(0,0,0,0.2)' }}>
              <div className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
                #{claim.cluster_id}
              </div>
              <div className="text-xs" style={{ color: 'var(--text-muted)' }}>Cluster ID</div>
            </div>
          </div>
        </div>

        {/* Related Clusters */}
        {claim.related_clusters && claim.related_clusters.length > 0 && (
          <div 
            className="p-6 rounded-lg mt-8"
            style={{ background: 'var(--bg-card)', border: '1px solid var(--border-subtle)' }}
          >
            <h2 className="text-sm uppercase tracking-wider mb-4 font-semibold" style={{ color: 'var(--text-muted)' }}>
              Related Claims
            </h2>
            <div className="flex flex-wrap gap-2">
              {claim.related_clusters.map((relatedId) => (
                <Badge 
                  key={relatedId}
                  variant="outline"
                  className="cursor-pointer hover:bg-white/5"
                  onClick={() => window.location.reload()} // Would navigate to that claim
                >
                  Cluster #{relatedId}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
