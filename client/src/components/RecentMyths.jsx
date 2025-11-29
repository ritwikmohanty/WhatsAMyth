import { useState, useEffect } from 'react'
import { ExternalLink, RefreshCw, AlertCircle, Search, Calendar, Globe } from 'lucide-react'
import { Button } from './ui/button'
import { Badge } from './ui/badge'
import { Input } from './ui/input'
import { cn } from '@/lib/utils'

const API_BASE_URL = 'http://localhost:8000'

export default function RecentMyths() {
  const [claims, setClaims] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [refreshing, setRefreshing] = useState(false)

  const fetchClaims = async (search = '') => {
    try {
      setLoading(true)
      setError(null)
      const endpoint = search 
        ? `${API_BASE_URL}/search?q=${encodeURIComponent(search)}&limit=50`
        : `${API_BASE_URL}/claims?limit=20`
      const response = await fetch(endpoint)
      if (!response.ok) throw new Error('Failed to fetch claims')
      const data = await response.json()
      setClaims(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleRefreshData = async () => {
    setRefreshing(true)
    try {
      // Trigger RSS fetch
      await fetch(`${API_BASE_URL}/fetch/rss`, { method: 'POST' })
      // Refetch claims
      await fetchClaims(searchQuery)
    } catch (err) {
      setError('Failed to refresh data')
    } finally {
      setRefreshing(false)
    }
  }

  useEffect(() => {
    fetchClaims()
  }, [])

  const handleSearch = (e) => {
    e.preventDefault()
    fetchClaims(searchQuery)
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

  const getSourceName = (source) => {
    if (!source) return 'Unknown'
    if (source === 'google') return 'Google Fact Check'
    if (source.includes('altnews')) return 'Alt News'
    if (source.includes('factly')) return 'Factly'
    if (source.includes('boomlive')) return 'Boom Live'
    if (source.includes('indiatoday')) return 'India Today'
    if (source.includes('thequint')) return 'The Quint'
    if (source.includes('newschecker')) return 'News Checker'
    if (source.includes('pib')) return 'PIB Fact Check'
    return 'Fact Checker'
  }

  return (
    <div className="min-h-screen py-12 px-6 md:px-10">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-12">
          <h1 className="font-serif text-3xl md:text-4xl lg:text-5xl font-semibold mb-4" style={{ color: 'var(--text-primary)' }}>
            Recent Myths & Debunks
          </h1>
          <p className="text-lg max-w-2xl" style={{ color: 'var(--text-secondary)' }}>
            Browse through the latest fact-checked claims from trusted sources across India. 
            Stay informed and help stop the spread of misinformation.
          </p>
        </div>

        {/* Search and Refresh */}
        <div className="flex flex-col md:flex-row gap-4 mb-8">
          <form onSubmit={handleSearch} className="flex-1 flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4" style={{ color: 'var(--text-muted)' }} />
              <Input
                type="text"
                placeholder="Search claims..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10 bg-card border-border"
              />
            </div>
            <Button type="submit" variant="outline">
              Search
            </Button>
          </form>
          <Button 
            onClick={handleRefreshData} 
            disabled={refreshing}
            variant="outline"
            className="gap-2"
          >
            <RefreshCw className={cn("w-4 h-4", refreshing && "animate-spin")} />
            {refreshing ? 'Refreshing...' : 'Refresh Data'}
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
              {error}. Make sure the backend server is running on port 8000.
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
        {!loading && claims.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {claims.map((claim, index) => (
              <ClaimItem key={index} claim={claim} formatDate={formatDate} getSourceName={getSourceName} />
            ))}
          </div>
        )}

        {/* Empty State */}
        {!loading && !error && claims.length === 0 && (
          <div className="text-center py-16">
            <AlertCircle className="w-12 h-12 mx-auto mb-4" style={{ color: 'var(--text-muted)' }} />
            <h3 className="text-xl font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>
              No claims found
            </h3>
            <p style={{ color: 'var(--text-secondary)' }}>
              {searchQuery 
                ? `No results for "${searchQuery}". Try a different search term.`
                : 'No claims in the database yet. Click "Refresh Data" to fetch latest fact-checks.'}
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

function ClaimItem({ claim, formatDate, getSourceName }) {
  return (
    <div 
      className="group p-6 rounded-lg transition-all duration-300 hover:scale-[1.01]"
      style={{ 
        background: 'var(--bg-card)', 
        border: '1px solid var(--border-subtle)',
      }}
    >
      {/* Source Badge */}
      <div className="flex items-center justify-between mb-4">
        <Badge 
          variant="outline" 
          className="text-xs uppercase tracking-wider"
          style={{ 
            color: 'var(--accent-green)',
            borderColor: 'rgba(0,214,125,0.3)',
            background: 'rgba(0,214,125,0.1)'
          }}
        >
          <Globe className="w-3 h-3 mr-1" />
          {getSourceName(claim.source)}
        </Badge>
        <div className="flex items-center gap-1 text-xs" style={{ color: 'var(--text-muted)' }}>
          <Calendar className="w-3 h-3" />
          {formatDate(claim.date)}
        </div>
      </div>

      {/* Misinformation */}
      <h3 
        className="font-medium text-lg mb-3 line-clamp-2 group-hover:text-white transition-colors"
        style={{ color: 'var(--text-primary)' }}
      >
        {claim.misinformation}
      </h3>

      {/* Rebuttal */}
      {claim.rebuttal && (
        <p 
          className="text-sm mb-4 line-clamp-2"
          style={{ color: 'var(--text-secondary)' }}
        >
          <span className="font-semibold" style={{ color: 'var(--accent-green)' }}>Verdict: </span>
          {claim.rebuttal}
        </p>
      )}

      {/* Link */}
      {claim.link && claim.link.startsWith('http') && (
        <a 
          href={claim.link} 
          target="_blank" 
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 text-sm font-medium transition-colors hover:opacity-80"
          style={{ color: 'var(--accent-green)' }}
        >
          Read full fact-check
          <ExternalLink className="w-3.5 h-3.5" />
        </a>
      )}
    </div>
  )
}
