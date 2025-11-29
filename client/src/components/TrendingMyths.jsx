import { useState, useEffect } from 'react'
import { XCircle, CheckCircle, AlertTriangle, HelpCircle, ChevronRight, Loader } from 'lucide-react'
import { Badge } from './ui/badge'
import { Button } from './ui/button'
import { cn } from "@/lib/utils"
import { getStatsOverview, getClaims } from '@/lib/api'

const VERDICT_CONFIG = {
	TRUE: { icon: CheckCircle, color: 'var(--accent-green)', bgColor: 'rgba(0,214,125,0.1)', borderColor: 'rgba(0,214,125,0.2)' },
	FALSE: { icon: XCircle, color: 'var(--accent-red)', bgColor: 'rgba(255,71,87,0.1)', borderColor: 'rgba(255,71,87,0.2)' },
	MISLEADING: { icon: AlertTriangle, color: '#ffc107', bgColor: 'rgba(255,193,7,0.1)', borderColor: 'rgba(255,193,7,0.2)' },
	PARTIALLY_TRUE: { icon: AlertTriangle, color: '#ffc107', bgColor: 'rgba(255,193,7,0.1)', borderColor: 'rgba(255,193,7,0.2)' },
	UNKNOWN: { icon: HelpCircle, color: 'var(--text-muted)', bgColor: 'rgba(96,96,112,0.1)', borderColor: 'rgba(96,96,112,0.2)' },
	UNVERIFIABLE: { icon: HelpCircle, color: 'var(--text-muted)', bgColor: 'rgba(96,96,112,0.1)', borderColor: 'rgba(96,96,112,0.2)' }
}

// Fallback sample data for when API is unavailable
const SAMPLE_MYTHS = [
	{
		cluster_id: 1,
		canonical_text: 'WhatsApp will be off from 11:30 pm to 6:00 am daily',
		status: 'FALSE',
		topic: 'Platform Hoax',
		message_count: 2847,
		last_seen_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
	},
	{
		cluster_id: 2,
		canonical_text: 'Drinking warm water with lemon cures COVID-19',
		status: 'FALSE',
		topic: 'Health Misinformation',
		message_count: 15420,
		last_seen_at: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(),
	},
	{
		cluster_id: 3,
		canonical_text: '5G towers spread coronavirus',
		status: 'FALSE',
		topic: 'Conspiracy Theory',
		message_count: 89234,
		last_seen_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
	},
]

export default function TrendingMyths({ onClaimClick }) {
	const [myths, setMyths] = useState(SAMPLE_MYTHS)
	const [loading, setLoading] = useState(true)
	const [error, setError] = useState(null)

	useEffect(() => {
		async function fetchTrendingMyths() {
			try {
				setLoading(true)
				// Try to get stats overview first (has top_clusters)
				const stats = await getStatsOverview()
				
				if (stats.top_clusters && stats.top_clusters.length > 0) {
					// Map top clusters to our format
					const topMyths = stats.top_clusters.slice(0, 3).map(cluster => ({
						cluster_id: cluster.cluster_id,
						canonical_text: cluster.canonical_text,
						status: cluster.status,
						topic: 'Trending',
						message_count: cluster.message_count,
						last_seen_at: new Date().toISOString()
					}))
					setMyths(topMyths)
				} else {
					// Fallback to getting recent claims
					const claimsResponse = await getClaims({ limit: 3 })
					if (claimsResponse.claims && claimsResponse.claims.length > 0) {
						setMyths(claimsResponse.claims)
					}
				}
				setError(null)
			} catch (err) {
				console.warn('Failed to fetch trending myths, using sample data:', err.message)
				setError(err.message)
				// Keep using sample data
			} finally {
				setLoading(false)
			}
		}

		fetchTrendingMyths()
	}, [])

	const formatTimeAgo = (dateStr) => {
		if (!dateStr) return 'Recently'
		const date = new Date(dateStr)
		const now = new Date()
		const diffMs = now - date
		const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
		const diffDays = Math.floor(diffHours / 24)
		
		if (diffHours < 1) return 'Just now'
		if (diffHours < 24) return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`
		if (diffDays < 7) return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`
		return date.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })
	}

	return (
		<section
			id="recent-debunks"
			className="px-6 md:px-10 py-16"
		>
			<div className="max-w-6xl mx-auto">
				<div className="flex justify-between items-center mb-12">
					<h2
						className="font-serif text-2xl md:text-3xl font-semibold"
						style={{ color: 'var(--text-primary)' }}
					>
						Recently Debunked
					</h2>
					<Button
						variant="link"
						className="p-0 h-auto gap-1 text-sm no-underline"
						style={{ color: 'var(--accent-green)' }}
						onClick={() => onClaimClick && window.location.assign('#recent-myths')}
					>
						View all <ChevronRight className="w-4 h-4" />
					</Button>
				</div>

				{loading ? (
					<div className="flex items-center justify-center py-12">
						<Loader className="w-8 h-8 animate-spin" style={{ color: 'var(--accent-green)' }} />
					</div>
				) : (
					<div 
						className="grid grid-cols-1 md:grid-cols-3 border-t border-l"
						style={{ borderColor: 'var(--border-subtle)' }}
					>
						{myths.map((myth, index) => {
							const verdictConfig = VERDICT_CONFIG[myth.status] || VERDICT_CONFIG.UNKNOWN
							const VerdictIcon = verdictConfig.icon

							return (
								<div
									key={myth.cluster_id}
									className={cn(
										"flex flex-col p-8 relative group transition-all duration-300 hover:bg-white/2 border-b border-r cursor-pointer",
									)}
									style={{ borderColor: 'var(--border-subtle)' }}
									onClick={() => onClaimClick && onClaimClick(myth.cluster_id)}
								>
									<div className="opacity-0 group-hover:opacity-100 transition duration-500 absolute inset-0 h-full w-full bg-linear-to-b from-white/3 to-transparent pointer-events-none" />
									
									<div className="relative z-10 flex flex-col h-full">
										<div className="flex justify-between items-start mb-6 gap-2">
											<Badge
												className="text-xs uppercase tracking-wider font-semibold shrink-0 p-0 hover:bg-transparent"
												style={{
													color: verdictConfig.color,
													background: 'transparent',
													border: 'none',
												}}
											>
												{myth.topic || 'Claim'}
											</Badge>
											<Badge
												className="gap-1 shrink-0 px-2.5 py-1 rounded-full text-xs font-semibold"
												style={{
													background: verdictConfig.bgColor,
													border: `1px solid ${verdictConfig.borderColor}`,
													color: verdictConfig.color,
												}}
											>
												<VerdictIcon className="w-3 h-3" />
												{myth.status}
											</Badge>
										</div>
										
										<p
											className="text-lg font-medium leading-relaxed mb-8 transition-colors group-hover:text-white line-clamp-3"
											style={{ color: 'var(--text-primary)' }}
										>
											"{myth.canonical_text}"
										</p>
										
										<div
											className="flex justify-between text-xs gap-2 mt-auto pt-6 border-t"
											style={{ 
												color: 'var(--text-muted)',
												borderColor: 'var(--border-subtle)'
											}}
										>
											<span>
												Debunked {(myth.message_count || 1).toLocaleString()}×
											</span>
											<span>{formatTimeAgo(myth.last_seen_at)}</span>
										</div>
									</div>
								</div>
							)
						})}
					</div>
				)}
			</div>
		</section>
	)
}
