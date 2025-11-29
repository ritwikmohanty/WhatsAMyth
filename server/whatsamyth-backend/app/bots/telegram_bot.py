"""
Telegram Bot Integration
Receives messages from Telegram and forwards them to the backend API.
Uses python-telegram-bot v20+ with async support and long polling.
"""

import asyncio
import logging
from typing import Optional
import os

import httpx
from telegram import Update, Bot
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    ContextTypes, filters
)

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


class TelegramBot:
    """
    Telegram bot that forwards messages to the WhatsAMyth backend.
    
    Features:
    - Receives messages from groups and private chats
    - Detects forwarded messages (common for misinformation)
    - Sends verification results back to users
    - Attaches audio files for TTS responses
    """
    
    def __init__(
        self,
        token: str,
        backend_url: str = "http://localhost:8000",
        internal_token: str = ""
    ):
        """
        Initialize the Telegram bot.
        
        Args:
            token: Telegram bot token from BotFather
            backend_url: URL of the WhatsAMyth backend
            internal_token: Secret token for authenticating with backend
        """
        self.token = token
        self.backend_url = backend_url.rstrip("/")
        self.internal_token = internal_token
        
        self.application: Optional[Application] = None
        self._running = False
        
        # HTTP client for backend calls
        self._client: Optional[httpx.AsyncClient] = None
        
        # Rate limiting
        self._rate_limit: dict = {}  # chat_id -> last_request_time
        self._rate_limit_seconds = 2  # Min seconds between requests per chat
    
    async def setup(self) -> None:
        """Set up the bot application and handlers."""
        logger.info("Setting up Telegram bot...")
        
        # Create application
        self.application = Application.builder().token(self.token).build()
        
        # Add handlers
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("help", self.cmd_help))
        self.application.add_handler(CommandHandler("check", self.cmd_check))
        self.application.add_handler(CommandHandler("stats", self.cmd_stats))
        
        # Message handler for all text messages
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )
        
        # Create HTTP client
        self._client = httpx.AsyncClient(timeout=60.0)
        
        logger.info("Telegram bot setup complete")
    
    async def start(self) -> None:
        """Start the bot with long polling."""
        if not self.application:
            await self.setup()
        
        logger.info("Starting Telegram bot with long polling...")
        self._running = True
        
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
        
        logger.info("Telegram bot is running")
    
    async def stop(self) -> None:
        """Stop the bot gracefully."""
        logger.info("Stopping Telegram bot...")
        self._running = False
        
        if self.application:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
        
        if self._client:
            await self._client.aclose()
        
        logger.info("Telegram bot stopped")
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        welcome_message = """
🔍 *Welcome to WhatsAMyth Bot!*

I help you verify claims and combat misinformation.

*How to use:*
• Simply forward or send me any message you want to verify
• I'll analyze it and tell you if it's true, false, or needs more investigation

*Commands:*
/check <text> - Check a specific claim
/help - Show help message
/stats - Show statistics

Stay informed, stay safe! 🛡️
"""
        await update.message.reply_text(welcome_message, parse_mode="Markdown")
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        help_message = """
📚 *WhatsAMyth Bot Help*

*Checking Claims:*
• Forward any message to me
• Or paste text directly
• Or use `/check <your claim>`

*Understanding Results:*
🟢 TRUE - Verified as accurate
🔴 FALSE - Confirmed misinformation
🟡 MISLEADING - Partially true but context is wrong
⚪ UNKNOWN - Couldn't verify yet

*Tips:*
• Include the full message for better results
• Works best with factual claims
• I can't verify opinions or predictions

*Privacy:*
I don't store personal information. Only the claim text is analyzed.
"""
        await update.message.reply_text(help_message, parse_mode="Markdown")
    
    async def cmd_check(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /check command."""
        if not context.args:
            await update.message.reply_text(
                "Please provide a claim to check.\nUsage: `/check <your claim here>`",
                parse_mode="Markdown"
            )
            return
        
        claim_text = " ".join(context.args)
        await self.process_and_respond(update, claim_text)
    
    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /stats command."""
        try:
            response = await self._client.get(
                f"{self.backend_url}/api/stats/overview",
                headers={"X-Internal-Token": self.internal_token}
            )
            
            if response.status_code == 200:
                data = response.json()
                stats_message = f"""
📊 *WhatsAMyth Statistics*

Total Messages: {data.get('total_messages', 0):,}
Total Claims: {data.get('total_claims', 0):,}
Total Clusters: {data.get('total_clusters', 0):,}

*Claims Today:* {data.get('claims_today', 0):,}

*By Status:*
🟢 True: {data.get('clusters_by_status', {}).get('true', 0)}
🔴 False: {data.get('clusters_by_status', {}).get('false', 0)}
🟡 Misleading: {data.get('clusters_by_status', {}).get('misleading', 0)}
⚪ Unknown: {data.get('clusters_by_status', {}).get('unknown', 0)}
"""
                await update.message.reply_text(stats_message, parse_mode="Markdown")
            else:
                await update.message.reply_text("Could not fetch statistics. Please try again later.")
                
        except Exception as e:
            logger.error(f"Stats command failed: {e}")
            await update.message.reply_text("Error fetching statistics.")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle incoming text messages."""
        if not update.message or not update.message.text:
            return
        
        # Rate limiting
        chat_id = update.effective_chat.id
        if not self._check_rate_limit(chat_id):
            return
        
        text = update.message.text
        
        # Check if message is too short
        if len(text.strip()) < 10:
            return  # Ignore very short messages
        
        # Check if it's a forwarded message (more likely to be misinformation)
        is_forwarded = update.message.forward_date is not None
        
        # Process and respond
        await self.process_and_respond(update, text, is_forwarded=is_forwarded)
    
    def _check_rate_limit(self, chat_id: int) -> bool:
        """Check if request is within rate limits."""
        import time
        current_time = time.time()
        
        last_time = self._rate_limit.get(chat_id, 0)
        if current_time - last_time < self._rate_limit_seconds:
            return False
        
        self._rate_limit[chat_id] = current_time
        return True
    
    async def process_and_respond(
        self,
        update: Update,
        text: str,
        is_forwarded: bool = False
    ) -> None:
        """
        Process a message through the backend and respond.
        
        Args:
            update: Telegram update object
            text: Message text to process
            is_forwarded: Whether the message was forwarded
        """
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id if update.effective_user else None
        
        # Send typing indicator
        await update.effective_chat.send_action("typing")
        
        try:
            # Call backend API
            response = await self._client.post(
                f"{self.backend_url}/api/messages",
                json={
                    "text": text,
                    "source": "telegram",
                    "metadata": {
                        "chat_id": str(chat_id),
                        "user_id": str(user_id) if user_id else None,
                        "is_forwarded": is_forwarded
                    }
                },
                headers={"X-Internal-Token": self.internal_token}
            )
            
            if response.status_code != 200:
                logger.error(f"Backend returned {response.status_code}: {response.text}")
                await update.message.reply_text(
                    "Sorry, I couldn't process your message. Please try again later."
                )
                return
            
            data = response.json()
            
            # Check if it's a claim
            if not data.get("is_claim"):
                # Not a claim - optionally respond or stay silent
                return
            
            # Build response message
            status = data.get("cluster_status", "UNKNOWN")
            status_emoji = {
                "TRUE": "🟢",
                "FALSE": "🔴",
                "MISLEADING": "🟡",
                "UNKNOWN": "⚪",
                "UNVERIFIABLE": "⚫",
                "PARTIALLY_TRUE": "🟠"
            }.get(status, "⚪")
            
            short_reply = data.get("short_reply")
            
            if short_reply:
                reply_text = f"{status_emoji} *{status}*\n\n{short_reply}"
            else:
                reply_text = f"{status_emoji} *{status}*\n\nThis claim is being verified. Check back later for results."
            
            # Send text response
            await update.message.reply_text(reply_text, parse_mode="Markdown")
            
            # Send audio if available
            audio_url = data.get("audio_url")
            if audio_url:
                try:
                    full_audio_url = f"{self.backend_url}{audio_url}"
                    audio_response = await self._client.get(full_audio_url)
                    
                    if audio_response.status_code == 200:
                        await update.message.reply_voice(
                            voice=audio_response.content,
                            caption="🔊 Audio explanation"
                        )
                except Exception as e:
                    logger.error(f"Failed to send audio: {e}")
            
        except httpx.TimeoutException:
            logger.error("Backend request timed out")
            await update.message.reply_text(
                "Request timed out. The claim is being processed - please try again in a moment."
            )
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await update.message.reply_text(
                "An error occurred. Please try again later."
            )


def create_telegram_bot() -> Optional[TelegramBot]:
    """
    Create and configure a Telegram bot instance.
    
    Returns:
        TelegramBot instance or None if token not configured
    """
    token = settings.telegram_bot_token
    
    if not token:
        logger.warning("Telegram bot token not configured")
        return None
    
    bot = TelegramBot(
        token=token,
        backend_url=f"http://localhost:{settings.app_port}",
        internal_token=settings.internal_token
    )
    
    return bot


async def run_telegram_bot() -> None:
    """Run the Telegram bot (for standalone execution)."""
    bot = create_telegram_bot()
    
    if not bot:
        logger.error("Could not create Telegram bot")
        return
    
    try:
        await bot.start()
        
        # Keep running until interrupted
        while bot._running:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        await bot.stop()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    asyncio.run(run_telegram_bot())
