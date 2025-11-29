import { Shield } from 'lucide-react'
import { Button } from './ui/button'
import ThemeToggle from './ThemeToggle'

export default function Header() {
  const scrollToSection = (sectionId) => {
    const element = document.getElementById(sectionId)
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }

  return (
    <header className="sticky top-0 z-50 border-b backdrop-blur-xl transition-all duration-300"
      style={{ 
        borderBottomColor: 'var(--border-subtle)', 
        backgroundColor: 'color-mix(in srgb, var(--bg-primary), transparent 20%)'
      }}>
      <div className="flex justify-between items-center px-6 md:px-10 py-4 max-w-6xl mx-auto w-full">
        <a 
          href="#" 
          onClick={(e) => { e.preventDefault(); window.scrollTo({ top: 0, behavior: 'smooth' }) }} 
          className="flex items-center gap-3 no-underline group"
        >
          <div className="w-9 h-9 rounded-lg flex items-center justify-center transition-colors group-hover:bg-accent/10"
            style={{ 
              border: '1px solid var(--border-subtle)',
              background: 'rgba(255,255,255,0.03)'
            }}>
            <Shield className="w-5 h-5" style={{ color: 'var(--accent-green)' }} />
          </div>
          <span className="font-serif text-xl font-semibold tracking-tight" style={{ color: 'var(--text-primary)' }}>
            WhatsAMyth
          </span>
        </a>
        
        <div className="flex items-center gap-8">
          <nav className="hidden md:flex gap-6 items-center">
            {['How it works', 'Recent Debunks', 'API'].map((item) => (
              <Button 
                key={item}
                variant="ghost" 
                className="h-auto p-0 text-sm font-medium hover:bg-transparent transition-colors relative group"
                style={{ color: 'var(--text-secondary)' }}
                onClick={() => {
                  const id = item.toLowerCase().replace(/ /g, '-')
                  if (id !== 'api') scrollToSection(id)
                }}
              >
                <span className="group-hover:text-(--text-primary) transition-colors">{item}</span>
                <span className="absolute -bottom-1 left-0 w-0 h-px bg-(--text-primary) transition-all group-hover:w-full" />
              </Button>
            ))}
          </nav>
          
          <div className="h-6 w-px" style={{ background: 'var(--border-subtle)' }} />
          
          <ThemeToggle />
        </div>
      </div>
    </header>
  )
}
