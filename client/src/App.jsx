import { useState } from 'react'
import Header from './components/Header'
import Hero from './components/Hero'
import ProcessingView from './components/ProcessingView'
import ResultsView from './components/ResultsView'
import TrendingMyths from './components/TrendingMyths'
import HowItWorks from './components/HowItWorks'
import RecentMyths from './components/RecentMyths'
import ClaimDetailPage from './components/ClaimDetailPage'
import Footer from './components/Footer'
import { analyzeMessage } from './lib/api'

import IntegrationsSection from './components/IntegrationsSection'

function App() {
  const [view, setView] = useState('home')
  const [page, setPage] = useState('home')
  const [processingStage, setProcessingStage] = useState(0)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [selectedClaimId, setSelectedClaimId] = useState(null)

  const handleSubmit = async (text) => {
    setView('processing')
    setProcessingStage(0)
    setError(null)

    try {
      // Stage 1: Detecting claims
      setProcessingStage(1)
      await new Promise(r => setTimeout(r, 400))
      
      // Stage 2: Extracting propositions
      setProcessingStage(2)
      await new Promise(r => setTimeout(r, 400))
      
      // Stage 3: Checking memory graph - call API
      setProcessingStage(3)
      const apiResult = await analyzeMessage(text)
      
      // Stage 4: Verifying sources
      setProcessingStage(4)
      await new Promise(r => setTimeout(r, 300))
      
      // Stage 5: Generating rebuttal
      setProcessingStage(5)
      await new Promise(r => setTimeout(r, 300))

      setResult(apiResult)
      setView('results')
    } catch (err) {
      console.error('Analysis failed:', err)
      setError(err.message || 'Failed to analyze the message. Please try again.')
      setView('home')
    }
  }

  const handleReset = () => {
    setView('home')
    setResult(null)
    setProcessingStage(0)
    setError(null)
  }

  const navigateTo = (newPage, claimId = null) => {
    setPage(newPage)
    setView('home')
    setResult(null)
    setProcessingStage(0)
    setError(null)
    setSelectedClaimId(claimId)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const handleClaimClick = (clusterId) => {
    setSelectedClaimId(clusterId)
    setPage('claim-detail')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const scrollToCheck = () => {
    document.getElementById('check-section')?.scrollIntoView({ behavior: 'smooth' })
  }

  return (
    <div className="min-h-screen transition-colors duration-300"
      style={{ 
        background: 'var(--bg-primary)', 
        backgroundImage: 'var(--gradient-mesh)',
        color: 'var(--text-primary)' 
      }}>
      <div className="noise-overlay"></div>
      <Header onNavigate={navigateTo} currentPage={page} />
      
      {/* Error Alert */}
      {error && (
        <div className="max-w-4xl mx-auto px-6 pt-4">
          <div 
            className="flex items-center gap-3 p-4 rounded-lg"
            style={{ 
              background: 'rgba(255,71,87,0.1)', 
              border: '1px solid rgba(255,71,87,0.2)' 
            }}
          >
            <span style={{ color: 'var(--accent-red)' }}>⚠️</span>
            <p style={{ color: 'var(--accent-red)' }}>
              {error}
            </p>
            <button 
              onClick={() => setError(null)}
              className="ml-auto text-sm opacity-70 hover:opacity-100"
              style={{ color: 'var(--accent-red)' }}
            >
              ✕
            </button>
          </div>
        </div>
      )}
      
      {view === 'home' && page === 'home' && (
        <>
          <Hero onSubmit={handleSubmit} isLoading={false} />
          <IntegrationsSection />
          <TrendingMyths onClaimClick={handleClaimClick} />
          <HowItWorks />
        </>
      )}

      {page === 'recent-myths' && (
        <RecentMyths onClaimClick={handleClaimClick} />
      )}

      {page === 'claim-detail' && selectedClaimId && (
        <ClaimDetailPage 
          clusterId={selectedClaimId} 
          onBack={() => navigateTo('recent-myths')}
        />
      )}

      {view === 'processing' && (
        <ProcessingView stage={processingStage} />
      )}

      {view === 'results' && result && (
        <ResultsView 
          result={result} 
          onReset={handleReset}
          onClaimClick={handleClaimClick}
        />
      )}

      <Footer />
    </div>
  )
}

export default App
