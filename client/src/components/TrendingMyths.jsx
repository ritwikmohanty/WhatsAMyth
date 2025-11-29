import { XCircle, ChevronRight } from 'lucide-react'
import { Badge } from './ui/badge'
import { Button } from './ui/button'
import { cn } from "@/lib/utils"

const SAMPLE_MYTHS = [
	{
		id: 1,
		text: 'WhatsApp will be off from 11:30 pm to 6:00 am daily',
		verdict: 'FALSE',
		category: 'Platform Hoax',
		debunkedCount: 2847,
		lastSeen: '2 hours ago',
	},
	{
		id: 2,
		text: 'Drinking warm water with lemon cures COVID-19',
		verdict: 'FALSE',
		category: 'Health Misinformation',
		debunkedCount: 15420,
		lastSeen: '5 hours ago',
	},
	{
		id: 3,
		text: '5G towers spread coronavirus',
		verdict: 'FALSE',
		category: 'Conspiracy Theory',
		debunkedCount: 89234,
		lastSeen: '1 day ago',
	},
]

export default function TrendingMyths() {
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
					>
						View all <ChevronRight className="w-4 h-4" />
					</Button>
				</div>

				<div 
                    className="grid grid-cols-1 md:grid-cols-3 border-t border-l"
                    style={{ borderColor: 'var(--border-subtle)' }}
                >
					{SAMPLE_MYTHS.map((myth, index) => (
						<div
							key={myth.id}
							className={cn(
								"flex flex-col p-8 relative group transition-all duration-300 hover:bg-white/2 border-b border-r",
							)}
							style={{ borderColor: 'var(--border-subtle)' }}
						>
                            <div className="opacity-0 group-hover:opacity-100 transition duration-500 absolute inset-0 h-full w-full bg-linear-to-b from-white/3 to-transparent pointer-events-none" />
                            
                            <div className="relative z-10 flex flex-col h-full">
                                <div className="flex justify-between items-start mb-6 gap-2">
                                    <Badge
                                        className="text-xs uppercase tracking-wider font-semibold shrink-0 p-0 hover:bg-transparent"
                                        style={{
                                            color: 'var(--accent-red)',
                                            background: 'transparent',
                                            border: 'none',
                                        }}
                                    >
                                        {myth.category}
                                    </Badge>
                                    <Badge
                                        className="gap-1 shrink-0 px-2.5 py-1 rounded-full text-xs font-semibold"
                                        style={{
                                            background: 'rgba(255,71,87,0.1)',
                                            border: '1px solid rgba(255,71,87,0.2)',
                                            color: 'var(--accent-red)',
                                        }}
                                    >
                                        <XCircle className="w-3 h-3" />
                                        {myth.verdict}
                                    </Badge>
                                </div>
                                
                                <p
                                    className="text-lg font-medium leading-relaxed mb-8 transition-colors group-hover:text-white"
                                    style={{ color: 'var(--text-primary)' }}
                                >
                                    "{myth.text}"
                                </p>
                                
                                <div
                                    className="flex justify-between text-xs gap-2 mt-auto pt-6 border-t"
                                    style={{ 
                                        color: 'var(--text-muted)',
                                        borderColor: 'var(--border-subtle)'
                                    }}
                                >
                                    <span>
                                        Debunked {myth.debunkedCount.toLocaleString()}×
                                    </span>
                                    <span>{myth.lastSeen}</span>
                                </div>
                            </div>
						</div>
					))}
				</div>
			</div>
		</section>
	)
}
