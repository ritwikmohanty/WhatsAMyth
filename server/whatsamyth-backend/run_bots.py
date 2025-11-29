#!/usr/bin/env python3
"""
Standalone Bot Runner
Run Telegram and Discord bots independently of the main API server.

Usage:
    python run_bots.py [--telegram] [--discord] [--all]
"""

import asyncio
import argparse
import logging
import signal
import sys
from typing import Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global bot references
telegram_bot = None
discord_bot = None
shutdown_event = asyncio.Event()


def signal_handler(sig, frame):
    """Handle shutdown signals."""
    logger.info(f"Received signal {sig}, initiating shutdown...")
    shutdown_event.set()


async def run_telegram():
    """Run the Telegram bot."""
    global telegram_bot
    
    from app.bots.telegram_bot import create_telegram_bot
    from app.config import get_settings
    
    settings = get_settings()
    
    if not settings.telegram_bot_token:
        logger.error("TELEGRAM_BOT_TOKEN not configured")
        return
    
    telegram_bot = create_telegram_bot()
    if not telegram_bot:
        logger.error("Failed to create Telegram bot")
        return
    
    logger.info("Starting Telegram bot...")
    await telegram_bot.start()
    
    # Wait for shutdown signal
    await shutdown_event.wait()
    
    logger.info("Stopping Telegram bot...")
    await telegram_bot.stop()


async def run_discord():
    """Run the Discord bot."""
    global discord_bot
    
    from app.bots.discord_bot import create_discord_bot
    from app.config import get_settings
    
    settings = get_settings()
    
    if not settings.discord_bot_token:
        logger.error("DISCORD_BOT_TOKEN not configured")
        return
    
    discord_bot = create_discord_bot()
    if not discord_bot:
        logger.error("Failed to create Discord bot")
        return
    
    logger.info("Starting Discord bot...")
    
    try:
        await discord_bot.start_bot()
    except asyncio.CancelledError:
        pass
    finally:
        await discord_bot.close()


async def run_all():
    """Run both bots concurrently."""
    tasks = []
    
    from app.config import get_settings
    settings = get_settings()
    
    if settings.telegram_bot_token:
        tasks.append(asyncio.create_task(run_telegram()))
        logger.info("Telegram bot task created")
    else:
        logger.warning("Telegram bot token not configured, skipping")
    
    if settings.discord_bot_token:
        tasks.append(asyncio.create_task(run_discord()))
        logger.info("Discord bot task created")
    else:
        logger.warning("Discord bot token not configured, skipping")
    
    if not tasks:
        logger.error("No bot tokens configured!")
        return
    
    # Wait for shutdown or completion
    done, pending = await asyncio.wait(
        tasks,
        return_when=asyncio.FIRST_COMPLETED
    )
    
    # Cancel remaining tasks
    for task in pending:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


async def main(run_telegram_flag: bool, run_discord_flag: bool, run_all_flag: bool):
    """Main entry point."""
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("WhatsAMyth Bot Runner starting...")
    
    if run_all_flag or (run_telegram_flag and run_discord_flag):
        await run_all()
    elif run_telegram_flag:
        await run_telegram()
    elif run_discord_flag:
        await run_discord()
    else:
        # Default to running all
        await run_all()
    
    logger.info("Bot runner shutdown complete")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WhatsAMyth Bot Runner")
    parser.add_argument("--telegram", action="store_true", help="Run Telegram bot only")
    parser.add_argument("--discord", action="store_true", help="Run Discord bot only")
    parser.add_argument("--all", action="store_true", help="Run all bots")
    
    args = parser.parse_args()
    
    try:
        asyncio.run(main(args.telegram, args.discord, args.all))
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
