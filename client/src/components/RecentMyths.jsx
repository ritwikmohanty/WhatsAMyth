import { useState, useEffect } from 'react'
import { ExternalLink, RefreshCw, AlertCircle, Search, Calendar, Globe, XCircle, CheckCircle, AlertTriangle, HelpCircle, ChevronLeft, ChevronRight } from 'lucide-react'
import { Button } from './ui/button'
import { Badge } from './ui/badge'
import { Input } from './ui/input'
import { cn } from '@/lib/utils'
import { getClaims, getStatsOverview, API_BASE_URL } from '@/lib/api'

const VERDICT_CONFIG = {
  TRUE: { icon: CheckCircle, color: 'var(--accent-green)', bgColor: 'rgba(0,214,125,0.1)', borderColor: 'rgba(0,214,125,0.2)' },
  FALSE: { icon: XCircle, color: 'var(--accent-red)', bgColor: 'rgba(255,71,87,0.1)', borderColor: 'rgba(255,71,87,0.2)' },
  MISLEADING: { icon: AlertTriangle, color: '#ffc107', bgColor: 'rgba(255,193,7,0.1)', borderColor: 'rgba(255,193,7,0.2)' },
  PARTIALLY_TRUE: { icon: AlertTriangle, color: '#ffc107', bgColor: 'rgba(255,193,7,0.1)', borderColor: 'rgba(255,193,7,0.2)' },
  UNKNOWN: { icon: HelpCircle, color: 'var(--text-muted)', bgColor: 'rgba(96,96,112,0.1)', borderColor: 'rgba(96,96,112,0.2)' },
  UNVERIFIABLE: { icon: HelpCircle, color: 'var(--text-muted)', bgColor: 'rgba(96,96,112,0.1)', borderColor: 'rgba(96,96,112,0.2)' }
}

export default function RecentMyths({ onClaimClick }) {
  const [claims, setClaims] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [refreshing, setRefreshing] = useState(false)
  const [stats, setStats] = useState(null)
  const [pagination, setPagination] = useState({ limit: 20, offset: 0, total: 0 })
  const [statusFilter, setStatusFilter] = useState(null)

  const fetchClaims = async (offset = 0, status = null) => {
    try {
      setLoading(true)
      setError(null)
      
      const response = await getClaims({ 
        limit: pagination.limit, 
        offset, 
        status 
      })
      
      setClaims(response.claims || [])
      setPagination(prev => ({
        ...prev,
        offset,
        total: response.total_count || 0
      }))
    } catch (err) {
      setError(err.message)
      setClaims([])
    } finally {
      setLoading(false)
    }
  }

  const fetchStats = async () => {
    try {
      const statsData = await getStatsOverview()
      setStats(statsData)
    } catch (err) {
      console.warn('Could not fetch stats:', err)
    }
  }

  const handleRefreshData = async () => {
    setRefreshing(true)
    try {
      await fetchClaims(0, statusFilter)
      await fetchStats()
    } catch (err) {
      setError('Failed to refresh data')
    } finally {
      setRefreshing(false)
    }
  }

  useEffect(() => {
    fetchClaims(0, statusFilter)
    fetchStats()
  }, [statusFilter])

  const handleSearch = (e) => {
    e.preventDefault()
    // For now, we'll filter client-side since the backend doesn't have search
    // In production, you'd add a search endpoint
  }

  const handlePageChange = (newOffset) => {
    fetchClaims(newOffset, statusFilter)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return 'Unknown'
    try {
      const date = new Date(dateStr)
      return date.toLocaleDateString('en-IN', { 
        day: 'numeric', 
        month: 'short', 
        year: 'numeric' 
      })
    } catch {
      return dateStr
    }
  }

  const formatTimeAgo = (dateStr) => {
    if (!dateStr) return 'Recently'
    const date = new Date(dateStr)
    const now = new Date()
    const diffMs = now - date
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
    const diffDays = Math.floor(diffHours / 24)
    
    if (diffHours < 1) return 'Just now'
    if (diffHours < 24) return `${diffHours}h ago`
    if (diffDays < 7) return `${diffDays}d ago`
    return formatDate(dateStr)
  }

  // Filter claims based on search query (client-side)
  const filteredClaims = searchQuery 
    ? claims.filter(c => 
        c.canonical_text?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        c.topic?.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : claims

  const totalPages = Math.ceil(pagination.total / pagination.limit)
  const currentPage = Math.floor(pagination.offset / pagination.limit) + 1

  return (
    <div className="min-h-screen py-12 px-6 md:px-10">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-12">
          <h1 className="font-serif text-3xl md:text-4xl lg:text-5xl font-semibold mb-4" style={{ color: 'var(--text-primary)' }}>
            Recent Myths & Debunks
          </h1>
          <p className="text-lg max-w-2xl" style={{ color: 'var(--text-secondary)' }}>
            Browse through verified claims from our database. 
            Click on any claim to see detailed fact-check information.
          </p>
        </div>

        {/* Stats Overview */}
        {stats && (
          <div 
            className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8 p-6 rounded-lg"
            style={{ background: 'var(--bg-card)', border: '1px solid var(--border-subtle)' }}
          >
            <div className="text-center">
              <div className="text-2xl font-bold" style={{ color: 'var(--accent-green)' }}>
                {stats.total_messages?.toLocaleString() || 0}
              </div>
              <div className="text-xs uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
                Messages Analyzed
              </div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold" style={{ color: 'var(--accent-green)' }}>
                {stats.total_clusters?.toLocaleString() || 0}
              </div>
              <div className="text-xs uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
                Unique Claims
              </div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold" style={{ color: 'var(--accent-red)' }}>
                {stats.clusters_by_status?.false || 0}
              </div>
              <div className="text-xs uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
                False Claims
              </div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
                {stats.messages_today || 0}
              </div>
              <div className="text-xs uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
                Today
              </div>
            </div>
          </div>
        )}

        {/* Search and Filters */}
        <div className="flex flex-col md:flex-row gap-4 mb-8">
          <form onSubmit={handleSearch} className="flex-1 flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4" style={{ color: 'var(--text-muted)' }} />
              <Input
                type="text"
                placeholder="Search claims..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
                style={{ background: 'var(--bg-card)', borderColor: 'var(--border-subtle)' }}
              />
            </div>
          </form>
          
          {/* Status Filter */}
          <div className="flex gap-2 flex-wrap">
            <Button 
              variant={statusFilter === null ? 'default' : 'outline'}
              size="sm"
              onClick={() => setStatusFilter(null)}
              className="text-xs"
            >
              All
            </Button>
            <Button 
              variant={statusFilter === 'FALSE' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setStatusFilter('FALSE')}
              className="text-xs"
              style={statusFilter === 'FALSE' ? { background: 'var(--accent-red)' } : {}}
            >
              False
            </Button>
            <Button 
              variant={statusFilter === 'TRUE' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setStatusFilter('TRUE')}
              className="text-xs"
              style={statusFilter === 'TRUE' ? { background: 'var(--accent-green)' } : {}}
            >
              True
            </Button>
            <Button 
              variant={statusFilter === 'MISLEADING' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setStatusFilter('MISLEADING')}
              className="text-xs"
            >
              Misleading
            </Button>
          </div>

          <Button 
            onClick={handleRefreshData} 
            disabled={refreshing}
            variant="outline"
            className="gap-2"
          >
            <RefreshCw className={cn("w-4 h-4", refreshing && "animate-spin")} />
            {refreshing ? 'Refreshing...' : 'Refresh'}
          </Button>
        </div>

        {/* Error State */}
        {error && (
          <div 
            className="flex items-center gap-3 p-4 rounded-lg mb-8"
            style={{ 
              background: 'rgba(255,71,87,0.1)', 
              border: '1px solid rgba(255,71,87,0.2)' 
            }}
          >
            <AlertCircle className="w-5 h-5" style={{ color: 'var(--accent-red)' }} />
            <p style={{ color: 'var(--accent-red)' }}>
              {error}. Make sure the backend server is running at {API_BASE_URL}
            </p>
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div 
                key={i} 
                className="p-6 rounded-lg animate-pulse"
                style={{ background: 'var(--bg-card)', border: '1px solid var(--border-subtle)' }}
              >
                <div className="h-4 bg-muted rounded w-1/4 mb-4"></div>
                <div className="h-6 bg-muted rounded w-full mb-2"></div>
                <div className="h-4 bg-muted rounded w-3/4"></div>
              </div>
            ))}
          </div>
        )}

        {/* Claims Grid */}
        {!loading && filteredClaims.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filteredClaims.map((claim) => (
              <ClaimItem 
                key={claim.cluster_id} 
                claim={claim} 
                formatDate={formatDate}
                formatTimeAgo={formatTimeAgo}
                onClick={() => onClaimClick && onClaimClick(claim.cluster_id)}
              />
            ))}
          </div>
        )}

        {/* Empty State */}
        {!loading && !error && filteredClaims.length === 0 && (
          <div className="text-center py-16">
            <AlertCircle className="w-12 h-12 mx-auto mb-4" style={{ color: 'var(--text-muted)' }} />
            <h3 className="text-xl font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>
              No claims found
            </h3>
            <p style={{ color: 'var(--text-secondary)' }}>
              {searchQuery 
                ? `No results for "${searchQuery}". Try a different search term.`
                : 'No claims in the database yet. Submit a message to start fact-checking!'}
            </p>
          </div>
        )}

        {/* Pagination */}
        {!loading && pagination.total > pagination.limit && (
          <div className="flex items-center justify-center gap-4 mt-8">
            <Button
              variant="outline"
              size="sm"
              disabled={currentPage === 1}
              onClick={() => handlePageChange(pagination.offset - pagination.limit)}
            >
              <ChevronLeft className="w-4 h-4 mr-1" />
              Previous
            </Button>
            
            <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              Page {currentPage} of {totalPages}
            </span>
            
            <Button
              variant="outline"
              size="sm"
              disabled={currentPage >= totalPages}
              onClick={() => handlePageChange(pagination.offset + pagination.limit)}
            >
              Next
              <ChevronRight className="w-4 h-4 ml-1" />
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}

function ClaimItem({ claim, formatDate, formatTimeAgo, onClick }) {
  const verdictConfig = VERDICT_CONFIG[claim.status] || VERDICT_CONFIG.UNKNOWN
  const VerdictIcon = verdictConfig.icon

  return (
    <div 
      className="group p-6 rounded-lg transition-all duration-300 hover:scale-[1.01] cursor-pointer"
      style={{ 
        background: 'var(--bg-card)', 
        border: '1px solid var(--border-subtle)',
      }}
      onClick={onClick}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <Badge 
          variant="outline" 
          className="text-xs uppercase tracking-wider gap-1"
          style={{ 
            color: verdictConfig.color,
            borderColor: verdictConfig.borderColor,
            background: verdictConfig.bgColor
          }}
        >
          <VerdictIcon className="w-3 h-3" />
          {claim.status}
        </Badge>
        <div className="flex items-center gap-1 text-xs" style={{ color: 'var(--text-muted)' }}>
          <Calendar className="w-3 h-3" />
          {formatTimeAgo(claim.last_seen_at)}
        </div>
      </div>

      {/* Claim Text */}
      <h3 
        className="font-medium text-lg mb-3 line-clamp-2 group-hover:text-white transition-colors"
        style={{ color: 'var(--text-primary)' }}
      >
        "{claim.canonical_text}"
      </h3>

      {/* Topic */}
      {claim.topic && (
        <p className="text-sm mb-3" style={{ color: 'var(--text-muted)' }}>
          Topic: {claim.topic}
        </p>
      )}

      {/* Footer */}
      <div 
        className="flex items-center justify-between pt-4 border-t text-xs"
        style={{ borderColor: 'var(--border-subtle)', color: 'var(--text-muted)' }}
      >
        <span>
          Seen {claim.message_count?.toLocaleString() || 1}× 
        </span>
        <span>
          First: {formatDate(claim.first_seen_at)}
        </span>
      </div>
    </div>
  )
}
