"""
Discord Bot Integration
Receives messages from Discord servers and forwards them to the backend API.
Uses discord.py v2+ with intents.
"""

import asyncio
import logging
from typing import Optional
import io

import httpx
import discord
from discord.ext import commands

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


class DiscordBot(commands.Bot):
    """
    Discord bot that forwards messages to the WhatsAMyth backend.
    
    Features:
    - Monitors channels for potential misinformation
    - Responds to mentions and commands
    - Posts verification results
    - Uploads audio files for TTS responses
    """
    
    def __init__(
        self,
        token: str,
        backend_url: str = "http://localhost:8000",
        internal_token: str = "",
        command_prefix: str = "!myth "
    ):
        """
        Initialize the Discord bot.
        
        Args:
            token: Discord bot token
            backend_url: URL of the WhatsAMyth backend
            internal_token: Secret token for authenticating with backend
            command_prefix: Prefix for bot commands
        """
        # Set up intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.messages = True
        
        super().__init__(
            command_prefix=command_prefix,
            intents=intents,
            help_command=None  # We'll implement our own
        )
        
        self.bot_token = token
        self.backend_url = backend_url.rstrip("/")
        self.internal_token = internal_token
        
        self._http_client: Optional[httpx.AsyncClient] = None
        
        # Rate limiting per channel
        self._rate_limit: dict = {}
        self._rate_limit_seconds = 3
        
        # Setup commands
        self._setup_commands()
    
    def _setup_commands(self) -> None:
        """Set up bot commands."""
        
        @self.command(name="check")
        async def check_command(ctx: commands.Context, *, claim: str):
            """Check a claim for misinformation."""
            await self.process_and_respond(ctx, claim)
        
        @self.command(name="help")
        async def help_command(ctx: commands.Context):
            """Show help message."""
            embed = discord.Embed(
                title="🔍 WhatsAMyth Bot Help",
                description="I help verify claims and combat misinformation.",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="Commands",
                value="""
`!myth check <claim>` - Verify a claim
`!myth help` - Show this message
`!myth stats` - Show statistics
                """,
                inline=False
            )
            
            embed.add_field(
                name="How to Use",
                value="""
• Use the check command with any claim
• Mention me with text to check
• React with 🔍 to messages to check them
                """,
                inline=False
            )
            
            embed.add_field(
                name="Status Meanings",
                value="""
🟢 TRUE - Verified accurate
🔴 FALSE - Confirmed misinformation
🟡 MISLEADING - Partially true
⚪ UNKNOWN - Not yet verified
                """,
                inline=False
            )
            
            await ctx.send(embed=embed)
        
        @self.command(name="stats")
        async def stats_command(ctx: commands.Context):
            """Show bot statistics."""
            try:
                response = await self._http_client.get(
                    f"{self.backend_url}/api/stats/overview",
                    headers={"X-Internal-Token": self.internal_token}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    embed = discord.Embed(
                        title="📊 WhatsAMyth Statistics",
                        color=discord.Color.green()
                    )
                    
                    embed.add_field(
                        name="Total Messages",
                        value=f"{data.get('total_messages', 0):,}",
                        inline=True
                    )
                    embed.add_field(
                        name="Total Claims",
                        value=f"{data.get('total_claims', 0):,}",
                        inline=True
                    )
                    embed.add_field(
                        name="Claims Today",
                        value=f"{data.get('claims_today', 0):,}",
                        inline=True
                    )
                    
                    status = data.get('clusters_by_status', {})
                    embed.add_field(
                        name="Verification Status",
                        value=f"""
🟢 True: {status.get('true', 0)}
🔴 False: {status.get('false', 0)}
🟡 Misleading: {status.get('misleading', 0)}
⚪ Unknown: {status.get('unknown', 0)}
                        """,
                        inline=False
                    )
                    
                    await ctx.send(embed=embed)
                else:
                    await ctx.send("Could not fetch statistics.")
                    
            except Exception as e:
                logger.error(f"Stats command failed: {e}")
                await ctx.send("Error fetching statistics.")
    
    async def setup_hook(self) -> None:
        """Called when the bot is starting up."""
        logger.info("Discord bot setup hook called")
        self._http_client = httpx.AsyncClient(timeout=60.0)
    
    async def on_ready(self) -> None:
        """Called when the bot is fully connected."""
        logger.info(f"Discord bot connected as {self.user.name} ({self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guilds")
        
        # Set presence
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="for misinformation | !myth help"
            )
        )
    
    async def on_message(self, message: discord.Message) -> None:
        """Handle incoming messages."""
        # Ignore bot messages
        if message.author.bot:
            return
        
        # Process commands first
        await self.process_commands(message)
        
        # Check if bot was mentioned
        if self.user in message.mentions:
            # Remove mention from text
            text = message.content
            for mention in message.mentions:
                text = text.replace(f"<@{mention.id}>", "").replace(f"<@!{mention.id}>", "")
            text = text.strip()
            
            if text:
                ctx = await self.get_context(message)
                await self.process_and_respond(ctx, text)
    
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        """Handle reactions - check messages when 🔍 is added."""
        if str(payload.emoji) != "🔍":
            return
        
        # Get the channel and message
        try:
            channel = self.get_channel(payload.channel_id)
            if not channel:
                return
            
            message = await channel.fetch_message(payload.message_id)
            if not message or message.author.bot:
                return
            
            # Rate limit check
            if not self._check_rate_limit(payload.channel_id):
                return
            
            # Process the message
            ctx = await self.get_context(message)
            await self.process_and_respond(ctx, message.content, reply_to=message)
            
        except Exception as e:
            logger.error(f"Reaction handler error: {e}")
    
    def _check_rate_limit(self, channel_id: int) -> bool:
        """Check if request is within rate limits."""
        import time
        current_time = time.time()
        
        last_time = self._rate_limit.get(channel_id, 0)
        if current_time - last_time < self._rate_limit_seconds:
            return False
        
        self._rate_limit[channel_id] = current_time
        return True
    
    async def process_and_respond(
        self,
        ctx: commands.Context,
        text: str,
        reply_to: Optional[discord.Message] = None
    ) -> None:
        """
        Process a claim through the backend and respond.
        
        Args:
            ctx: Command context
            text: Claim text to process
            reply_to: Optional message to reply to
        """
        if len(text.strip()) < 10:
            await ctx.send("Please provide a longer claim to check.")
            return
        
        # Rate limit
        if not self._check_rate_limit(ctx.channel.id):
            return
        
        # Send typing indicator
        async with ctx.typing():
            try:
                # Call backend API
                response = await self._http_client.post(
                    f"{self.backend_url}/api/messages",
                    json={
                        "text": text,
                        "source": "discord",
                        "metadata": {
                            "chat_id": str(ctx.channel.id),
                            "user_id": str(ctx.author.id),
                            "guild_id": str(ctx.guild.id) if ctx.guild else None
                        }
                    },
                    headers={"X-Internal-Token": self.internal_token}
                )
                
                if response.status_code != 200:
                    logger.error(f"Backend returned {response.status_code}")
                    await ctx.send("Sorry, I couldn't process that claim. Please try again.")
                    return
                
                data = response.json()
                
                if not data.get("is_claim"):
                    await ctx.send("This doesn't appear to be a verifiable claim.")
                    return
                
                # Build embed response
                status = data.get("cluster_status", "UNKNOWN")
                status_colors = {
                    "TRUE": discord.Color.green(),
                    "FALSE": discord.Color.red(),
                    "MISLEADING": discord.Color.gold(),
                    "UNKNOWN": discord.Color.light_grey(),
                    "UNVERIFIABLE": discord.Color.dark_grey(),
                    "PARTIALLY_TRUE": discord.Color.orange()
                }
                status_emoji = {
                    "TRUE": "🟢",
                    "FALSE": "🔴",
                    "MISLEADING": "🟡",
                    "UNKNOWN": "⚪",
                    "UNVERIFIABLE": "⚫",
                    "PARTIALLY_TRUE": "🟠"
                }
                
                embed = discord.Embed(
                    title=f"{status_emoji.get(status, '⚪')} Claim Verification: {status}",
                    color=status_colors.get(status, discord.Color.light_grey())
                )
                
                # Truncate claim for display
                display_claim = text[:200] + "..." if len(text) > 200 else text
                embed.add_field(name="Claim", value=display_claim, inline=False)
                
                short_reply = data.get("short_reply")
                if short_reply:
                    embed.add_field(name="Verdict", value=short_reply, inline=False)
                else:
                    embed.add_field(
                        name="Status",
                        value="This claim is being verified. Check back later.",
                        inline=False
                    )
                
                embed.set_footer(text=f"Cluster ID: {data.get('cluster_id', 'N/A')}")
                
                # Send embed
                target = reply_to or ctx.message
                await target.reply(embed=embed)
                
                # Send audio if available
                audio_url = data.get("audio_url")
                if audio_url:
                    try:
                        full_audio_url = f"{self.backend_url}{audio_url}"
                        audio_response = await self._http_client.get(full_audio_url)
                        
                        if audio_response.status_code == 200:
                            audio_file = discord.File(
                                io.BytesIO(audio_response.content),
                                filename="verdict.mp3"
                            )
                            await ctx.send("🔊 Audio explanation:", file=audio_file)
                    except Exception as e:
                        logger.error(f"Failed to send audio: {e}")
                
            except httpx.TimeoutException:
                await ctx.send("Request timed out. Please try again.")
            except Exception as e:
                logger.error(f"Error processing claim: {e}")
                await ctx.send("An error occurred. Please try again later.")
    
    async def start_bot(self) -> None:
        """Start the Discord bot."""
        logger.info("Starting Discord bot...")
        await self.start(self.bot_token)
    
    async def close(self) -> None:
        """Close the bot and cleanup."""
        logger.info("Closing Discord bot...")
        if self._http_client:
            await self._http_client.aclose()
        await super().close()


def create_discord_bot() -> Optional[DiscordBot]:
    """
    Create and configure a Discord bot instance.
    
    Returns:
        DiscordBot instance or None if token not configured
    """
    token = settings.discord_bot_token
    
    if not token:
        logger.warning("Discord bot token not configured")
        return None
    
    bot = DiscordBot(
        token=token,
        backend_url=f"http://localhost:{settings.app_port}",
        internal_token=settings.internal_token
    )
    
    return bot


async def run_discord_bot() -> None:
    """Run the Discord bot (for standalone execution)."""
    bot = create_discord_bot()
    
    if not bot:
        logger.error("Could not create Discord bot")
        return
    
    try:
        await bot.start_bot()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        await bot.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    asyncio.run(run_discord_bot())
