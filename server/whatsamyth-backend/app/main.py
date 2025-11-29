"""
WhatsAMyth Backend - Main Application
FastAPI application with routers, background tasks, and bot integration.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import get_settings
from app.db import init_db, check_db_connection
from app.routers import messages_router, claims_router, stats_router
from app.services.embedding import get_embedding_service
from app.services.memory_graph import get_memory_graph_service
from app.services.verification import get_verification_service
from app.services.tts import get_tts_service
from app.crud import get_unknown_clusters, update_verdict
from app.models import ClaimStatus

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

settings = get_settings()

# Global references for cleanup
scheduler: Optional[AsyncIOScheduler] = None
telegram_bot = None
discord_bot = None


async def verification_worker():
    """
    Background worker that verifies UNKNOWN clusters.
    Runs periodically to process claims that haven't been verified yet.
    """
    from app.db import SessionLocal
    
    logger.info("Running verification worker...")
    
    db = SessionLocal()
    try:
        # Get clusters needing verification
        unknown_clusters = get_unknown_clusters(db, limit=5)
        
        if not unknown_clusters:
            logger.debug("No clusters need verification")
            return
        
        verification_service = get_verification_service()
        tts_service = get_tts_service()
        
        for cluster in unknown_clusters:
            try:
                logger.info(f"Verifying cluster {cluster.id}: {cluster.canonical_text[:50]}...")
                
                # Run verification
                result = verification_service.verify_claim(cluster.canonical_text)
                
                # Update verdict
                verdict = update_verdict(
                    db=db,
                    cluster_id=cluster.id,
                    status=result.status,
                    short_reply=result.short_reply,
                    long_reply=result.long_reply,
                    sources=result.sources,
                    evidence_snippets=result.evidence_snippets,
                    confidence_score=result.confidence_score
                )
                
                # Generate TTS
                if result.short_reply:
                    audio_path = tts_service.generate(
                        text=result.short_reply,
                        message_id=cluster.id
                    )
                    if audio_path and verdict:
                        verdict.audio_path = audio_path
                        db.commit()
                
                logger.info(f"Cluster {cluster.id} verified as {result.status.value}")
                
            except Exception as e:
                logger.error(f"Failed to verify cluster {cluster.id}: {e}")
        
    except Exception as e:
        logger.error(f"Verification worker error: {e}")
    finally:
        db.close()


async def start_background_tasks():
    """Start background scheduler and tasks."""
    global scheduler
    
    if not settings.enable_background_verification:
        logger.info("Background verification disabled")
        return
    
    scheduler = AsyncIOScheduler()
    
    # Add verification job
    scheduler.add_job(
        verification_worker,
        'interval',
        seconds=settings.verification_interval_seconds,
        id='verification_worker',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info(f"Background scheduler started (interval: {settings.verification_interval_seconds}s)")


async def stop_background_tasks():
    """Stop background scheduler."""
    global scheduler
    
    if scheduler:
        scheduler.shutdown(wait=False)
        logger.info("Background scheduler stopped")


async def start_bots():
    """Start Telegram and Discord bots if enabled."""
    global telegram_bot, discord_bot
    
    if not settings.enable_bots:
        logger.info("Bots disabled")
        return
    
    # Start Telegram bot
    if settings.telegram_bot_token:
        try:
            from app.bots.telegram_bot import create_telegram_bot
            telegram_bot = create_telegram_bot()
            if telegram_bot:
                asyncio.create_task(telegram_bot.start())
                logger.info("Telegram bot started")
        except Exception as e:
            logger.error(f"Failed to start Telegram bot: {e}")
    
    # Start Discord bot
    if settings.discord_bot_token:
        try:
            from app.bots.discord_bot import create_discord_bot
            discord_bot = create_discord_bot()
            if discord_bot:
                asyncio.create_task(discord_bot.start_bot())
                logger.info("Discord bot started")
        except Exception as e:
            logger.error(f"Failed to start Discord bot: {e}")


async def stop_bots():
    """Stop running bots."""
    global telegram_bot, discord_bot
    
    if telegram_bot:
        try:
            await telegram_bot.stop()
            logger.info("Telegram bot stopped")
        except Exception as e:
            logger.error(f"Error stopping Telegram bot: {e}")
    
    if discord_bot:
        try:
            await discord_bot.close()
            logger.info("Discord bot stopped")
        except Exception as e:
            logger.error(f"Error stopping Discord bot: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown tasks.
    """
    # ===== STARTUP =====
    logger.info("Starting WhatsAMyth Backend...")
    
    # Check database connection
    if not check_db_connection():
        logger.error("Database connection failed!")
        # Continue anyway - might be initializing
    
    # Initialize database tables
    init_db()
    logger.info("Database initialized")
    
    # Initialize embedding service and FAISS index
    try:
        embedding_service = get_embedding_service()
        embedding_service.initialize()
        logger.info(f"Embedding service initialized (index size: {embedding_service.index_size})")
    except Exception as e:
        logger.error(f"Failed to initialize embedding service: {e}")
    
    # Initialize memory graph
    try:
        memory_graph = get_memory_graph_service()
        memory_graph.initialize()
        logger.info("Memory graph initialized")
    except Exception as e:
        logger.error(f"Failed to initialize memory graph: {e}")
    
    # Start background tasks
    await start_background_tasks()
    
    # Start bots
    await start_bots()
    
    logger.info("WhatsAMyth Backend started successfully")
    
    yield
    
    # ===== SHUTDOWN =====
    logger.info("Shutting down WhatsAMyth Backend...")
    
    # Stop bots
    await stop_bots()
    
    # Stop background tasks
    await stop_background_tasks()
    
    # Save FAISS index
    try:
        embedding_service = get_embedding_service()
        embedding_service.save_index()
        logger.info("FAISS index saved")
    except Exception as e:
        logger.error(f"Failed to save FAISS index: {e}")
    
    # Save memory graph
    try:
        memory_graph = get_memory_graph_service()
        memory_graph.save()
        logger.info("Memory graph saved")
    except Exception as e:
        logger.error(f"Failed to save memory graph: {e}")
    
    logger.info("WhatsAMyth Backend shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="WhatsAMyth API",
    description="Misinformation detection and verification API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for media
import os
media_dir = settings.media_path
os.makedirs(media_dir, exist_ok=True)
app.mount("/media", StaticFiles(directory=media_dir), name="media")

# Include routers
app.include_router(messages_router)
app.include_router(claims_router)
app.include_router(stats_router)


# ===== Health and utility endpoints =====

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    db_ok = check_db_connection()
    
    embedding_service = get_embedding_service()
    faiss_ok = embedding_service._initialized
    
    return {
        "status": "healthy" if db_ok else "degraded",
        "database": db_ok,
        "faiss_index_loaded": faiss_ok,
        "faiss_index_size": embedding_service.index_size if faiss_ok else 0
    }


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "WhatsAMyth API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


# ===== Exception handlers =====

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# ===== Run with Uvicorn =====

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=True,
        log_level="info"
    )
