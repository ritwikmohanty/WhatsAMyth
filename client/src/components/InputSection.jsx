import { useState } from 'react'
import { Search, Loader } from 'lucide-react'
import { Button } from './ui/button'
import { Textarea } from './ui/textarea'
import { Card, CardContent } from './ui/card'

const SAMPLE_TEXT = `Forwarded
WhatsApp will be off from 11:30 pm to 6:00 am daily as central government declared. We are requesting all users to forward this message to as many as you can to let everyone know about this new rule by the Government of India.

If you don't forward this message your WhatsApp account will be treated as invalid and your account will be deleted within 48 hours.

For reactivation, a charge of 499.00 will be added to your monthly bill.

Message from Narendra Modi (PM)`;

export default function InputSection({ onSubmit, isLoading }) {
  const [text, setText] = useState('')

  const handleSubmit = () => {
    if (text.trim() && !isLoading) {
      onSubmit(text)
    }
  }

  return (
    <section id="check-section" className="px-6 md:px-10 py-16 max-w-4xl mx-auto">
      <label className="block text-sm font-medium mb-3"
        style={{ color: 'var(--text-secondary)' }}>
        Paste the suspicious message below
      </label>
      
      <Card className="rounded-2xl overflow-hidden transition-all"
        style={{ 
          background: 'var(--bg-card)', 
          border: '1px solid var(--border-medium)' 
        }}>
        <CardContent className="p-0">
          <Textarea
            className="min-h-[180px] border-0 text-base resize-vertical focus-visible:ring-0 rounded-b-none p-5 font-inherit leading-relaxed"
            style={{ 
              background: 'transparent',
              color: 'var(--text-primary)'
            }}
            placeholder="Paste the forwarded message here..."
            value={text}
            onChange={e => setText(e.target.value)}
            disabled={isLoading}
          />
          
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 px-5 py-3"
            style={{ 
              borderTop: '1px solid var(--border-subtle)', 
              background: 'rgba(0,0,0,0.2)' 
            }}>
            <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
              {text.length} characters
            </span>
            
            <div className="flex gap-3 items-center w-full sm:w-auto">
              <Button
                onClick={() => setText(SAMPLE_TEXT)}
                disabled={isLoading}
                variant="ghost"
                size="sm"
                className="flex-1 sm:flex-none px-4 py-3 rounded-xl text-sm font-semibold transition-all"
                style={{ 
                  background: 'transparent',
                  color: 'var(--text-secondary)',
                  border: 'none'
                }}
              >
                Try sample
              </Button>
              
              <Button
                onClick={handleSubmit}
                disabled={!text.trim() || isLoading}
                size="sm"
                className="flex-1 sm:flex-none px-6 py-3 rounded-xl text-sm font-semibold transition-all"
                style={{
                  background: text.trim() ? 'var(--accent-green)' : 'var(--bg-secondary)',
                  color: text.trim() ? 'var(--bg-primary)' : 'var(--text-muted)',
                  opacity: isLoading ? 0.7 : 1,
                  cursor: text.trim() && !isLoading ? 'pointer' : 'not-allowed'
                }}
              >
                {isLoading ? <Loader className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                {isLoading ? 'Analyzing...' : 'Fact Check'}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </section>
  )
}
