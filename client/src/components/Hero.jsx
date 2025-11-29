import { useState } from 'react'
import { Zap, ArrowRight, Search, Loader } from 'lucide-react'
import { Button } from './ui/button'
import { Badge } from './ui/badge'
import { Textarea } from './ui/textarea'

const SAMPLE_TEXT = `Forwarded
WhatsApp will be off from 11:30 pm to 6:00 am daily as central government declared. We are requesting all users to forward this message to as many as you can to let everyone know about this new rule by the Government of India.

If you don't forward this message your WhatsApp account will be treated as invalid and your account will be deleted within 48 hours.

For reactivation, a charge of 499.00 will be added to your monthly bill.

Message from Narendra Modi (PM)`;

export default function Hero({ onSubmit, isLoading }) {
  const [text, setText] = useState('')

  const handleSubmit = () => {
    if (text.trim() && !isLoading) {
      onSubmit(text)
    }
  }

  return (
    <section 
      id="check-section"
      className="px-6 md:px-10 pt-20 pb-20 text-center relative min-h-[90vh] flex flex-col justify-center">
      
      {/* Hero Content */}
      <div className="mb-12">
        <Badge 
          className="mb-6 animate-in inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium"
          style={{
            background: 'rgba(0,214,125,0.1)',
            border: '1px solid rgba(0,214,125,0.2)',
            color: 'var(--accent-green)'
          }}
        >
          <Zap className="w-4 h-4" />
          <span>Instant fact-checking for viral forwards</span>
        </Badge>
        
        <h1 className="font-serif text-4xl md:text-5xl lg:text-6xl font-bold leading-tight mb-5 tracking-tight animate-slide-up max-w-4xl mx-auto"
          style={{ color: 'var(--text-primary)' }}>
          Stop misinformation<br />
          <span style={{ color: 'var(--accent-green)' }}>before it spreads</span>
        </h1>
        
        <p className="text-base md:text-lg max-w-2xl mx-auto mb-10 leading-relaxed animate-slide-up px-4"
          style={{ color: 'var(--text-secondary)' }}>
          Paste any suspicious WhatsApp forward and get an instant, 
          shareable fact-check powered by AI and authoritative sources.
        </p>
      </div>

      {/* Input Section */}
      <div className="max-w-4xl mx-auto w-full">
        <div className="rounded-2xl p-1.5 pt-4 transition-all backdrop-blur-sm"
          style={{ 
            background: 'rgba(255, 255, 255, 0.03)',
            border: '1px solid var(--border-subtle)'
          }}>
          
          <div className="mx-2 mb-2.5 flex items-center gap-2">
            <span className="text-xs font-medium tracking-tight" style={{ color: 'var(--text-secondary)' }}>
              Paste the suspicious message below
            </span>
          </div>

          <div className="relative flex flex-col">
            <Textarea
              className="w-full min-h-[180px] resize-none rounded-xl rounded-b-none border-none px-4 py-4 focus-visible:ring-0 focus-visible:ring-offset-0 text-base shadow-none font-inherit leading-relaxed"
              style={{ 
                background: 'rgba(0, 0, 0, 0.2)',
                color: 'var(--text-primary)'
              }}
              placeholder="Paste the forwarded message here..."
              value={text}
              onChange={e => setText(e.target.value)}
              disabled={isLoading}
            />
            
            <div className="flex h-14 items-center justify-between rounded-b-xl px-3"
              style={{ 
                background: 'rgba(0, 0, 0, 0.2)',
                borderTop: '1px solid var(--border-subtle)'
              }}>
              <span className="text-xs pl-2" style={{ color: 'var(--text-muted)' }}>
                {text.length} characters
              </span>
              
              <div className="flex items-center gap-2">
                <Button
                  onClick={() => setText(SAMPLE_TEXT)}
                  disabled={isLoading}
                  variant="ghost"
                  size="sm"
                  className="h-8 text-xs font-medium hover:bg-white/5 transition-colors"
                  style={{ color: 'var(--text-secondary)' }}
                >
                  Try sample
                </Button>
                
                <Button
                  onClick={handleSubmit}
                  disabled={!text.trim() || isLoading}
                  size="sm"
                  className="h-8 px-4 gap-2 text-xs font-semibold transition-all hover:opacity-90"
                  style={{
                    background: text.trim() ? 'var(--accent-green)' : 'var(--bg-secondary)',
                    color: text.trim() ? 'var(--bg-primary)' : 'var(--text-muted)',
                    cursor: text.trim() && !isLoading ? 'pointer' : 'not-allowed'
                  }}
                >
                  {isLoading ? <Loader className="w-3.5 h-3.5 animate-spin" /> : <Search className="w-3.5 h-3.5" />}
                  {isLoading ? 'Analyzing...' : 'Fact Check'}
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
