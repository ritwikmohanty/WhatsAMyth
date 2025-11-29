import { useState } from 'react'
import Header from './components/Header'
import Hero from './components/Hero'
import ProcessingView from './components/ProcessingView'
import ResultsView from './components/ResultsView'
import TrendingMyths from './components/TrendingMyths'
import HowItWorks from './components/HowItWorks'
import RecentMyths from './components/RecentMyths'
import Footer from './components/Footer'
import { simulateAPICall } from './lib/api'

function App() {
  const [view, setView] = useState('home')
  const [page, setPage] = useState('home')
  const [processingStage, setProcessingStage] = useState(0)
  const [result, setResult] = useState(null)

  const handleSubmit = async (text) => {
    setView('processing')
    setProcessingStage(0)

    for (let i = 0; i < 5; i++) {
      await new Promise(r => setTimeout(r, 800 + Math.random() * 400))
      setProcessingStage(i + 1)
    }

    const apiResult = await simulateAPICall(text)
    setResult(apiResult)
    setView('results')
  }

  const handleReset = () => {
    setView('home')
    setResult(null)
    setProcessingStage(0)
  }

  const navigateTo = (newPage) => {
    setPage(newPage)
    setView('home')
    setResult(null)
    setProcessingStage(0)
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
      
      {view === 'home' && page === 'home' && (
        <>
          <Hero onSubmit={handleSubmit} isLoading={false} />
          <TrendingMyths />
          <HowItWorks />
        </>
      )}

      {page === 'recent-myths' && (
        <RecentMyths />
      )}

      {view === 'processing' && (
        <ProcessingView stage={processingStage} />
      )}

      {view === 'results' && result && (
        <ResultsView result={result} onReset={handleReset} />
      )}

      <Footer />
    </div>
  )
}

export default App
