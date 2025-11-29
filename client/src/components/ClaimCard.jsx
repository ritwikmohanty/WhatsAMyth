import { CheckCircle, XCircle, AlertTriangle, HelpCircle } from 'lucide-react'
import { Badge } from './ui/badge'

const VERDICT_COLORS = {
  TRUE: { bg: 'rgba(0,214,125,0.1)', border: 'rgba(0,214,125,0.3)', text: '#00d67d' },
  FALSE: { bg: 'rgba(255,71,87,0.1)', border: 'rgba(255,71,87,0.3)', text: '#ff4757' },
  MISLEADING: { bg: 'rgba(255,193,7,0.1)', border: 'rgba(255,193,7,0.3)', text: '#ffc107' },
  UNKNOWN: { bg: 'rgba(96,96,112,0.1)', border: 'rgba(96,96,112,0.3)', text: '#9090a0' }
}

export default function ClaimCard({ claim, index }) {
  const colors = VERDICT_COLORS[claim.verdict] || VERDICT_COLORS.UNKNOWN

  const VerdictIcon = claim.verdict === 'TRUE' ? CheckCircle : 
                      claim.verdict === 'FALSE' ? XCircle :
                      claim.verdict === 'MISLEADING' ? AlertTriangle : HelpCircle

  return (
    <div
      className="bg-card p-6 md:p-8 animate-slide-up group hover:bg-white/2 transition-colors"
      style={{ animationDelay: `${index * 0.1}s` }}
    >
      <div className="flex flex-col gap-6">
        <div className="flex items-start justify-between gap-4">
          <p className="text-lg font-medium leading-relaxed text-primary">{claim.text}</p>
          <Badge
            className="shrink-0 gap-1.5 rounded-none px-3 py-1.5"
            style={{ background: colors.bg, border: `1px solid ${colors.border}`, color: colors.text }}
          >
            <VerdictIcon className="w-3.5 h-3.5" />
            {claim.verdict}
          </Badge>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-[1fr_auto] gap-6 md:gap-12 items-end">
            <div>
                <div className="text-xs text-muted uppercase tracking-wider mb-2 font-medium">Evidence</div>
                <p className="text-sm leading-relaxed text-secondary">{claim.evidence}</p>
            </div>

            <div className="flex items-center gap-3 min-w-[140px]">
                <span className="text-xs text-muted uppercase tracking-wider">Confidence</span>
                <div className="flex-1 h-1 bg-subtle overflow-hidden">
                    <div
                    className="h-full transition-all duration-500"
                    style={{ width: `${claim.confidence * 100}%`, backgroundColor: colors.text }}
                    ></div>
                </div>
                <span className="text-xs text-secondary font-medium min-w-fit tabular-nums">
                    {Math.round(claim.confidence * 100)}%
                </span>
            </div>
        </div>
      </div>
    </div>
  )
}
