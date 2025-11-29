import { useState } from 'react'
import { FileText, Globe, MessageCircle, Copy, Share2, ExternalLink, Database } from 'lucide-react'
import { Button } from './ui/button'
import { Badge } from './ui/badge'
import ClaimCard from './ClaimCard'

export default function ResultsView({ result, onReset }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(result.generatedRebuttal)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <section className="px-6 md:px-10 py-12 md:py-20 max-w-6xl mx-auto">
      <Button
        onClick={onReset}
        variant="ghost"
        className="mb-8 hover:bg-transparent p-0 h-auto gap-2 text-muted hover:text-primary transition-colors"
      >
        ← Check another message
      </Button>

      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-12">
        <div>
            <h2 className="font-serif text-3xl md:text-4xl lg:text-5xl mb-4 font-semibold text-primary">Fact-Check Results</h2>
            <div className="flex flex-wrap gap-3">
                <Badge variant="outline" className="gap-2 rounded-none border-subtle bg-transparent text-secondary font-normal">
                <FileText className="w-3.5 h-3.5" />
                {result.claims.length} claim{result.claims.length !== 1 ? 's' : ''} detected
                </Badge>
                <Badge variant="outline" className="gap-2 rounded-none border-subtle bg-transparent text-secondary font-normal">
                <Globe className="w-3.5 h-3.5" />
                Language: {result.language.toUpperCase()}
                </Badge>
                {result.isForward && (
                <Badge variant="outline" className="gap-2 rounded-none border-subtle bg-transparent text-secondary font-normal">
                    <MessageCircle className="w-3.5 h-3.5" />
                    Forwarded message
                </Badge>
                )}
            </div>
        </div>
      </div>

      {result.matchedCluster && (
        <div className="mb-16 border border-l-4 border-subtle bg-card/30 backdrop-blur-sm"
             style={{ borderLeftColor: 'var(--accent-green)' }}>
          <div className="p-6 md:p-8 border-b border-subtle">
            <div className="flex items-center gap-3 mb-3 text-accent-green">
              <Database className="w-5 h-5" />
              <span className="text-sm font-semibold tracking-wider uppercase">Known Myth Cluster Matched</span>
            </div>
            <p className="text-xl md:text-2xl font-medium text-primary">"{result.matchedCluster.name}"</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 divide-y md:divide-y-0 md:divide-x divide-subtle">
            <div className="p-6 text-center">
                <div className="text-3xl font-bold text-accent-green mb-1">{result.matchedCluster.timesDebunked.toLocaleString()}</div>
                <div className="text-xs text-muted uppercase tracking-wider">Times debunked</div>
            </div>
            <div className="p-6 text-center">
                <div className="text-3xl font-bold text-accent-green mb-1">{result.matchedCluster.firstSeen}</div>
                <div className="text-xs text-muted uppercase tracking-wider">First seen</div>
            </div>
            <div className="p-6 text-center">
                <div className="text-3xl font-bold text-accent-green mb-1">{result.matchedCluster.regions.length}</div>
                <div className="text-xs text-muted uppercase tracking-wider">Regions affected</div>
            </div>
          </div>
        </div>
      )}

      <div className="mb-16">
        <h3 className="font-serif text-2xl md:text-3xl mb-8 font-semibold text-primary">Individual Claims</h3>
        <div className="flex flex-col gap-px bg-subtle border border-subtle">
            {result.claims.map((claim, i) => (
            <ClaimCard key={i} claim={claim} index={i} />
            ))}
        </div>
      </div>

      <div>
        <h3 className="font-serif text-2xl md:text-3xl mb-8 font-semibold text-primary">Shareable Rebuttal</h3>
        <div className="border border-subtle bg-card/30 backdrop-blur-sm">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 p-4 border-b border-subtle bg-black/20">
            <span className="text-sm text-muted">Copy this and share in your group chats</span>
            <div className="flex gap-2 w-full sm:w-auto">
                <Button
                onClick={handleCopy}
                variant="outline"
                size="sm"
                className="flex-1 sm:flex-none h-8 text-xs rounded-none border-subtle hover:bg-white/5 hover:text-primary"
                >
                <Copy className="w-3.5 h-3.5 mr-2" />
                {copied ? 'Copied!' : 'Copy'}
                </Button>
                <Button variant="outline" size="sm" className="flex-1 sm:flex-none h-8 text-xs rounded-none border-subtle hover:bg-white/5 hover:text-primary">
                <Share2 className="w-3.5 h-3.5 mr-2" />
                Share
                </Button>
            </div>
            </div>
            <div className="p-6 md:p-8">
            <pre className="text-base leading-relaxed text-primary whitespace-pre-wrap font-sans">
                {result.generatedRebuttal}
            </pre>
            </div>
        </div>
      </div>

      {result.sources.length > 0 && (
        <div className="flex flex-wrap gap-4 mt-12 pt-8 border-t border-subtle">
          <span className="text-sm text-muted self-center uppercase tracking-wider font-medium">Sources</span>
          {result.sources.map((source, i) => (
            <a 
              key={i}
              href={source.url} 
              target="_blank" 
              rel="noopener noreferrer"
              className="flex items-center gap-2 text-sm text-secondary hover:text-accent-green transition-colors border border-subtle px-3 py-1.5 hover:border-accent-green/30 bg-white/5 hover:bg-accent-green/5"
            >
                {source.name}
                <ExternalLink className="w-3 h-3" />
            </a>
          ))}
        </div>
      )}
    </section>
  )
}
