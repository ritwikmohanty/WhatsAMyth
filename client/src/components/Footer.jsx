import { Twitter, Linkedin, Github, Instagram } from 'lucide-react'
import { Button } from './ui/button'

export default function Footer() {
  const currentYear = new Date().getFullYear()
  
  const links = [
    { label: 'Home', href: '#' },
    { label: 'How it works', href: '#how-it-works' },
    { label: 'Recent Debunks', href: '#recent-debunks' },
    { label: 'API', href: '#' },
    { label: 'Privacy Policy', href: '#' },
    { label: 'Terms of Service', href: '#' },
  ]

  const socials = [
    { icon: Twitter, href: '#', label: 'Twitter' },
    { icon: Linkedin, href: '#', label: 'LinkedIn' },
    { icon: Github, href: '#', label: 'GitHub' },
    { icon: Instagram, href: '#', label: 'Instagram' },
  ]

  return (
    <footer className="py-12 md:py-16 border-t transition-colors duration-300"
      style={{ borderTopColor: 'var(--border-subtle)' }}>
      <div className="max-w-6xl mx-auto px-6 md:px-10 flex flex-col items-center gap-8 md:gap-10">
        
        {/* Navigation Links */}
        <nav className="flex flex-wrap justify-center gap-x-8 gap-y-4">
          {links.map((link) => (
            <a
              key={link.label}
              href={link.href}
              className="text-sm font-medium transition-colors hover:text-(--text-primary)"
              style={{ color: 'var(--text-secondary)' }}
            >
              {link.label}
            </a>
          ))}
        </nav>

        {/* Social Icons */}
        <div className="flex items-center gap-6">
          {socials.map((social) => {
            const Icon = social.icon
            return (
              <a
                key={social.label}
                href={social.href}
                target="_blank"
                rel="noopener noreferrer"
                className="transition-colors hover:text-(--text-primary) hover:scale-110 transform duration-200"
                style={{ color: 'var(--text-muted)' }}
                aria-label={social.label}
              >
                <Icon className="w-5 h-5" />
              </a>
            )
          })}
        </div>

        {/* Copyright */}
        <div className="text-center space-y-2">
          <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
            &copy; {currentYear} WhatsAMyth. All rights reserved.
          </p>
          <p className="text-xs" style={{ color: 'var(--text-muted)', opacity: 0.7 }}>
            Built for the Mumbai Hacks Hackathon 2025
          </p>
        </div>
      </div>
    </footer>
  )
}
