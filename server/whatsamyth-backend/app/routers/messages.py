"""
Messages Router
Handles message ingestion, claim detection, and verification pipeline.
"""

import os
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session

from app.db import get_db
from app.config import get_settings
from app.schemas import (
    MessageCreate, MessageIngestResponse, 
    ClaimStatusEnum, MessageSourceEnum
)
from app.crud import (
    create_message, update_message_cluster,
    get_verdict_by_cluster, update_verdict,
    create_verdict_if_missing
)
from app.models import ClaimStatus
from app.services.detection import is_claim, extract_canonical_claim, detect_language, get_claim_topics
from app.services.embedding import get_embedding_service
from app.services.clustering import get_clustering_service
from app.services.verification import get_verification_service
from app.services.tts import get_tts_service
from app.services.memory_graph import get_memory_graph_service

logger = logging.getLogger(__name__)

settings = get_settings()

router = APIRouter(prefix="/api/messages", tags=["messages"])


@router.post("/", response_model=MessageIngestResponse)
def ingest_message(
    payload: MessageCreate,
    db: Session = Depends(get_db),
    x_internal_token: Optional[str] = Header(None)
) -> MessageIngestResponse:
    """
    Ingest a message and run the full claim detection and verification pipeline.
    
    Pipeline:
    1. Save raw message
    2. Detect if message contains a claim
    3. If claim: extract canonical form, generate embedding
    4. Assign to existing cluster or create new one
    5. Trigger verification if needed
    6. Generate TTS for reply
    7. Return response with verdict
    
    Args:
        payload: Message data including text, source, and optional metadata
        db: Database session
        x_internal_token: Optional internal auth token (for bot requests)
    
    Returns:
        MessageIngestResponse with claim status, verdict, and audio URL
    """
    logger.info(f"Ingesting message from {payload.source.value}: {payload.text[:100]}...")
    
    # Extract metadata
    metadata = None
    if payload.metadata:
        metadata = {
            "chat_id": payload.metadata.chat_id,
            "user_id": payload.metadata.user_id,
            "reply_to_message_id": payload.metadata.reply_to_message_id,
            "platform_specific": payload.metadata.platform_specific
        }
    
    # Detect language
    language = detect_language(payload.text)
    
    # Step 1: Check if this is a claim
    claim_detected = is_claim(payload.text)
    
    if not claim_detected:
        # Not a claim - just save and return
        message = create_message(
            db=db,
            text=payload.text,
            source=payload.source.value,
            metadata=metadata,
            language=language,
            is_claim=False
        )
        
        logger.info(f"Message {message.id} is not a claim")
        
        return MessageIngestResponse(
            message_id=message.id,
            is_claim=False,
            cluster_id=None,
            cluster_status=None,
            short_reply=None,
            audio_url=None,
            needs_verification=False
        )
    
    # Step 2: Extract canonical claim
    canonical_text = extract_canonical_claim(payload.text)
    logger.info(f"Extracted canonical claim: {canonical_text[:100]}...")
    
    # Step 3: Generate embedding
    embedding_service = get_embedding_service()
    if not embedding_service._initialized:
        embedding_service.initialize()
    
    embedding = embedding_service.embed_text(canonical_text)
    
    if embedding is None:
        logger.error("Failed to generate embedding")
        raise HTTPException(status_code=500, detail="Embedding generation failed")
    
    # Step 4: Get topic
    topics = get_claim_topics(canonical_text)
    topic = topics[0] if topics else "general"
    
    # Step 5: Assign to cluster
    clustering_service = get_clustering_service()
    cluster, is_new = clustering_service.assign_cluster(
        db=db,
        canonical_text=canonical_text,
        embedding=embedding,
        topic=topic,
        source=payload.source.value,
        platform_chat_id=metadata.get("chat_id") if metadata else None,
        platform_user_id=metadata.get("user_id") if metadata else None
    )
    
    logger.info(f"Assigned to cluster {cluster.id} (new: {is_new})")
    
    # Step 6: Save message with cluster assignment
    message = create_message(
        db=db,
        text=payload.text,
        source=payload.source.value,
        metadata=metadata,
        language=language,
        is_claim=True,
        canonical_text=canonical_text,
        embedding_vector=embedding.tolist(),
        cluster_id=cluster.id
    )
    
    # Step 7: Get or create verdict
    verdict = create_verdict_if_missing(db, cluster.id)
    
    # Step 8: Run verification if needed (for new clusters or unknown status)
    needs_verification = cluster.status == ClaimStatus.UNKNOWN
    
    if needs_verification and is_new:
        # Run verification synchronously for new clusters
        try:
            verification_service = get_verification_service()
            result = verification_service.verify_claim(canonical_text)
            
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
            
            # Update cluster status
            cluster.status = result.status
            db.commit()
            
            needs_verification = False
            logger.info(f"Verification complete: {result.status.value}")
            
        except Exception as e:
            logger.error(f"Verification failed: {e}")
            # Continue with UNKNOWN status
    
    # Step 9: Generate TTS if we have a reply
    audio_url = None
    # DISABLED: TTS causes hanging issues on Windows with pyttsx3
    # if verdict and verdict.short_reply:
    #     try:
    #         tts_service = get_tts_service()
    #         audio_path = tts_service.generate(
    #             text=verdict.short_reply,
    #             message_id=message.id
    #         )
    #
    #         if audio_path:
    #             audio_url = tts_service.get_audio_url(audio_path)
    #
    #             # Update verdict with audio path
    #             verdict.audio_path = audio_path
    #             db.commit()
    #
    #             logger.info(f"Generated TTS audio: {audio_url}")
    #
    #     except Exception as e:
    if False:  # Placeholder to keep the except block
        try:
            pass
        except Exception as e:
            logger.error(f"TTS generation failed: {e}")
    
    # Step 10: Update memory graph
    try:
        memory_graph = get_memory_graph_service()
        memory_graph.add_cluster_node(cluster.id, {"topic": topic})
        
        # Check for spike
        memory_graph.detect_spike(db, cluster.id)
        
    except Exception as e:
        logger.error(f"Memory graph update failed: {e}")
    
    # Build response
    return MessageIngestResponse(
        message_id=message.id,
        is_claim=True,
        cluster_id=cluster.id,
        cluster_status=ClaimStatusEnum(cluster.status.value),
        short_reply=verdict.short_reply if verdict else None,
        audio_url=audio_url,
        needs_verification=needs_verification
    )


@router.post("/batch")
def ingest_messages_batch(
    payloads: list[MessageCreate],
    db: Session = Depends(get_db)
) -> list[MessageIngestResponse]:
    """
    Ingest multiple messages in a batch.
    
    Args:
        payloads: List of message data
        db: Database session
    
    Returns:
        List of MessageIngestResponse for each message
    """
    responses = []
    
    for payload in payloads:
        try:
            response = ingest_message(payload, db)
            responses.append(response)
        except Exception as e:
            logger.error(f"Batch ingestion failed for message: {e}")
            # Create error response
            responses.append(MessageIngestResponse(
                message_id=-1,
                is_claim=False,
                cluster_id=None,
                cluster_status=None,
                short_reply=None,
                audio_url=None,
                needs_verification=False
            ))
    
    return responses
