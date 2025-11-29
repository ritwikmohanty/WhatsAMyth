import { FaXTwitter, FaReddit, FaWhatsapp, FaTelegram, FaDiscord } from "react-icons/fa6";
import { SiBluesky } from "react-icons/si";
import { Shield } from "lucide-react";
import { cn } from '../lib/utils';
import { Button } from './ui/button';
import { motion } from "framer-motion";

export default function IntegrationsSection() {
    return (
        <section className="overflow-hidden">
            <div className="py-16 md:py-16">
                <div className="mx-auto max-w-5xl px-6">
                    <div className="grid items-center sm:grid-cols-2 gap-10">
                        <motion.div 
                            initial={{ opacity: 0, scale: 0.9 }}
                            whileInView={{ opacity: 1, scale: 1 }}
                            transition={{ duration: 0.8, ease: "easeOut" }}
                            viewport={{ once: true }}
                            className="dark:bg-secondary/50 relative mx-auto w-fit"
                        >
                            <div
                                aria-hidden
                                className="bg-radial to-secondary dark:to-primary absolute inset-0 z-10 from-transparent to-75%"
                            />
                            <div className="mx-auto mb-2 flex w-fit justify-center gap-2">
                                <IntegrationCard delay={0.1}>
                                    <FaXTwitter className="size-full" />
                                </IntegrationCard>
                                <IntegrationCard delay={0.2}>
                                    <FaReddit className="size-full" />
                                </IntegrationCard>
                            </div>
                            <div className="mx-auto my-2 flex w-fit justify-center gap-2">
                                <IntegrationCard delay={0.3}>
                                    <SiBluesky className="size-full" />
                                </IntegrationCard>
                                <IntegrationCard
                                    delay={0}
                                    borderClassName="shadow-black-950/10 shadow-xl border-black/25 dark:border-white/25"
                                    className="dark:bg-white/10 z-20 scale-110"
                                >
                                    <motion.div
                                        animate={{ 
                                            boxShadow: ["0 0 0px rgba(0,214,125,0)", "0 0 20px rgba(0,214,125,0.3)", "0 0 0px rgba(0,214,125,0)"] 
                                        }}
                                        transition={{ duration: 3, repeat: Infinity }}
                                        className="rounded-full"
                                    >
                                        <Shield className="size-full text-[var(--accent-green)]" />
                                    </motion.div>
                                </IntegrationCard>
                                <IntegrationCard delay={0.3}>
                                    <FaWhatsapp className="size-full" />
                                </IntegrationCard>
                            </div>

                            <div className="mx-auto flex w-fit justify-center gap-2">
                                <IntegrationCard delay={0.4}>
                                    <FaTelegram className="size-full" />
                                </IntegrationCard>

                                <IntegrationCard delay={0.5}>
                                    <FaDiscord className="size-full" />
                                </IntegrationCard>
                            </div>
                        </motion.div>
                        
                        <motion.div 
                            initial={{ opacity: 0, x: 20 }}
                            whileInView={{ opacity: 1, x: 0 }}
                            transition={{ duration: 0.6, delay: 0.2 }}
                            viewport={{ once: true }}
                            className="mx-auto mt-6 max-w-lg space-y-6 text-center sm:mt-0 sm:text-left"
                        >
                            <h2 className="text-balance text-3xl font-semibold md:text-4xl">Integrate with your favorite tools</h2>
                            <p className="text-muted">Connect seamlessly with popular platforms and services to enhance your workflow.</p>

                            <Button
                                variant="outline"
                                size="sm"
                                asChild
                                className="transition-transform hover:scale-105 active:scale-95"
                            >
                                <a href="#">Get Started</a>
                            </Button>
                        </motion.div>
                    </div>
                </div>
            </div>
        </section>
    )
}

const IntegrationCard = ({ children, className, borderClassName, delay = 0 }) => {
    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay }}
            viewport={{ once: true }}
            whileHover={{ y: -5, transition: { duration: 0.2 } }}
            className={cn('bg-card relative flex size-20 rounded-xl dark:bg-transparent items-center justify-center', className)}
        >
            <div
                role="presentation"
                className={cn('absolute inset-0 rounded-xl border border-white/10 dark:border-white/25', borderClassName)}
            />
            <div className="relative z-20 m-auto size-fit *:size-8">{children}</div>
        </motion.div>
    )
}
