import { FileText, Brain, Database, Globe, MessageCircle, CheckCircle, Loader } from 'lucide-react'
import { Card } from './ui/card'

const STAGES = [
  { id: 'detect', label: 'Detecting claims', icon: FileText },
  { id: 'extract', label: 'Extracting propositions', icon: Brain },
  { id: 'cluster', label: 'Checking memory graph', icon: Database },
  { id: 'verify', label: 'Verifying sources', icon: Globe },
  { id: 'generate', label: 'Generating rebuttal', icon: MessageCircle }
]

export default function ProcessingView({ stage }) {
  return (
    <section className="px-6 md:px-10 py-12 md:py-20 max-w-2xl mx-auto text-center">
      <h2 className="font-serif text-3xl md:text-4xl mb-10 font-semibold" 
        style={{ color: 'var(--text-primary)' }}>
        Analyzing message...
      </h2>
      
      <div className="flex flex-col gap-4">
        {STAGES.map((s, i) => {
          const isActive = i === stage
          const isComplete = i < stage
          const Icon = s.icon

          return (
            <Card
              key={s.id}
              className="flex items-center gap-4 p-4 transition-all rounded-xl"
              style={{
                background: isActive ? 'rgba(0,214,125,0.1)' : 'var(--bg-card)',
                border: `1px solid ${isActive ? 'rgba(0,214,125,0.3)' : 'var(--border-subtle)'}`,
                opacity: isComplete || isActive ? 1 : 0.4
              }}
            >
              <div
                className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
                style={{
                  background: isComplete 
                    ? 'var(--accent-green)' 
                    : isActive 
                    ? 'rgba(0,214,125,0.2)' 
                    : 'var(--bg-secondary)',
                  color: isComplete 
                    ? 'var(--bg-primary)' 
                    : isActive 
                    ? 'var(--accent-green)' 
                    : 'var(--text-muted)'
                }}
              >
                {isComplete ? <CheckCircle className="w-5 h-5" /> : isActive ? <Loader className="w-5 h-5 animate-spin" /> : <Icon className="w-5 h-5" />}
              </div>
              <span
                className="text-sm md:text-base font-medium"
                style={{
                  color: isActive ? 'var(--accent-green)' : 'var(--text-primary)',
                  fontWeight: isActive ? 600 : 400
                }}
              >
                {s.label}
              </span>
            </Card>
          )
        })}
      </div>
    </section>
  )
}
