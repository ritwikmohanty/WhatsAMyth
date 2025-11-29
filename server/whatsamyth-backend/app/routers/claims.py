"""
Claims Router
Endpoints for viewing and managing claim clusters.
"""

import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import (
    ClusterSummary, ClusterDetail, ClaimsListResponse,
    VerdictDetail, EvidenceItem, ClaimStatusEnum
)
from app.crud import (
    get_cluster_by_id, list_clusters, count_clusters,
    get_verdict_by_cluster, get_related_clusters as db_get_related_clusters
)
from app.models import ClaimStatus
from app.services.clustering import get_clustering_service
from app.services.memory_graph import get_memory_graph_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/claims", tags=["claims"])


@router.get("/", response_model=ClaimsListResponse)
def get_claims(
    db: Session = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status: Optional[str] = Query(default=None, description="Filter by status")
) -> ClaimsListResponse:
    """
    Get a paginated list of claim clusters.
    
    Args:
        db: Database session
        limit: Maximum number of results (1-100)
        offset: Number of results to skip
        status: Optional filter by verification status
    
    Returns:
        ClaimsListResponse with list of clusters and pagination info
    """
    # Parse status filter
    status_filter = None
    if status:
        try:
            status_filter = ClaimStatus(status.upper())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Must be one of: {[s.value for s in ClaimStatus]}"
            )
    
    # Get clusters
    clusters = list_clusters(db, limit=limit, offset=offset, status=status_filter)
    total = count_clusters(db)
    
    # Convert to response format
    claims = [
        ClusterSummary(
            cluster_id=c.id,
            canonical_text=c.canonical_text,
            topic=c.topic,
            status=ClaimStatusEnum(c.status.value),
            message_count=c.message_count,
            first_seen_at=c.first_seen_at,
            last_seen_at=c.last_seen_at
        )
        for c in clusters
    ]
    
    return ClaimsListResponse(
        claims=claims,
        total_count=total,
        limit=limit,
        offset=offset
    )


@router.get("/{cluster_id}", response_model=ClusterDetail)
def get_claim_detail(
    cluster_id: int,
    db: Session = Depends(get_db)
) -> ClusterDetail:
    """
    Get detailed information about a specific claim cluster.
    
    Includes:
    - Cluster metadata (canonical text, topic, status)
    - Full verdict with explanation and sources
    - Related clusters
    
    Args:
        cluster_id: ID of the cluster to retrieve
        db: Database session
    
    Returns:
        ClusterDetail with full cluster information
    """
    # Get cluster
    cluster = get_cluster_by_id(db, cluster_id)
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    
    # Get verdict
    verdict = get_verdict_by_cluster(db, cluster_id)
    verdict_detail = None
    
    if verdict:
        # Parse sources
        sources = None
        if verdict.sources:
            sources = [
                EvidenceItem(
                    source_url=s.get("source_url", ""),
                    source_name=s.get("source_name"),
                    snippet=s.get("snippet", ""),
                    relevance_score=s.get("relevance_score"),
                    retrieved_at=s.get("retrieved_at")
                )
                for s in verdict.sources
            ]
        
        verdict_detail = VerdictDetail(
            status=ClaimStatusEnum(verdict.status.value),
            confidence_score=verdict.confidence_score,
            short_reply=verdict.short_reply,
            long_reply=verdict.long_reply,
            sources=sources,
            verified_at=verdict.verified_at,
            audio_url=f"/media/replies/{cluster_id}.mp3" if verdict.audio_path else None
        )
    
    # Get related clusters
    related_ids = db_get_related_clusters(db, cluster_id)
    
    # Also check memory graph for relationships
    try:
        memory_graph = get_memory_graph_service()
        if memory_graph._initialized:
            graph_related = memory_graph.get_related_clusters(cluster_id, max_depth=2)
            for rid, score in graph_related:
                if rid not in related_ids:
                    related_ids.append(rid)
    except Exception:
        pass
    
    return ClusterDetail(
        cluster_id=cluster.id,
        canonical_text=cluster.canonical_text,
        topic=cluster.topic,
        status=ClaimStatusEnum(cluster.status.value),
        message_count=cluster.message_count,
        first_seen_at=cluster.first_seen_at,
        last_seen_at=cluster.last_seen_at,
        verdict=verdict_detail,
        related_clusters=related_ids[:10] if related_ids else None
    )


@router.get("/{cluster_id}/similar")
def get_similar_claims(
    cluster_id: int,
    db: Session = Depends(get_db),
    limit: int = Query(default=5, ge=1, le=20)
) -> List[ClusterSummary]:
    """
    Get claims similar to the specified cluster.
    
    Uses embedding similarity to find related claims.
    
    Args:
        cluster_id: ID of the reference cluster
        db: Database session
        limit: Maximum number of similar claims to return
    
    Returns:
        List of similar ClusterSummary objects
    """
    # Get cluster
    cluster = get_cluster_by_id(db, cluster_id)
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    
    # Find similar clusters
    clustering_service = get_clustering_service()
    similar = clustering_service.get_similar_clusters(db, cluster_id, k=limit, threshold=0.5)
    
    return [
        ClusterSummary(
            cluster_id=c.id,
            canonical_text=c.canonical_text,
            topic=c.topic,
            status=ClaimStatusEnum(c.status.value),
            message_count=c.message_count,
            first_seen_at=c.first_seen_at,
            last_seen_at=c.last_seen_at
        )
        for c, score in similar
    ]


@router.get("/{cluster_id}/messages")
def get_cluster_messages(
    cluster_id: int,
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200)
) -> dict:
    """
    Get messages belonging to a specific cluster.
    
    Args:
        cluster_id: ID of the cluster
        db: Database session
        limit: Maximum number of messages to return
    
    Returns:
        Dict with cluster info and list of messages
    """
    # Get cluster
    cluster = get_cluster_by_id(db, cluster_id)
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    
    # Get messages
    messages = cluster.messages[:limit]
    
    return {
        "cluster_id": cluster.id,
        "message_count": cluster.message_count,
        "messages": [
            {
                "id": m.id,
                "text": m.text,
                "source": m.source,
                "language": m.language,
                "created_at": m.created_at.isoformat()
            }
            for m in messages
        ]
    }


@router.post("/{cluster_id}/reverify")
def reverify_claim(
    cluster_id: int,
    db: Session = Depends(get_db)
) -> ClusterDetail:
    """
    Re-run verification for a claim cluster.
    
    Useful when new evidence might be available.
    
    Args:
        cluster_id: ID of the cluster to reverify
        db: Database session
    
    Returns:
        Updated ClusterDetail
    """
    from app.services.verification import get_verification_service
    from app.crud import update_verdict
    from app.services.tts import get_tts_service
    
    # Get cluster
    cluster = get_cluster_by_id(db, cluster_id)
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    
    logger.info(f"Re-verifying cluster {cluster_id}")
    
    # Run verification
    verification_service = get_verification_service()
    result = verification_service.verify_claim(cluster.canonical_text)
    
    # Update verdict
    verdict = update_verdict(
        db=db,
        cluster_id=cluster_id,
        status=result.status,
        short_reply=result.short_reply,
        long_reply=result.long_reply,
        sources=result.sources,
        evidence_snippets=result.evidence_snippets,
        confidence_score=result.confidence_score
    )
    
    # Generate new TTS
    if result.short_reply:
        try:
            tts_service = get_tts_service()
            audio_path = tts_service.generate(
                text=result.short_reply,
                message_id=cluster_id
            )
            if audio_path:
                verdict.audio_path = audio_path
                db.commit()
        except Exception as e:
            logger.error(f"TTS generation failed: {e}")
    
    # Return updated detail
    return get_claim_detail(cluster_id, db)


@router.get("/predictions/reemergence")
def get_reemergence_predictions(
    db: Session = Depends(get_db),
    limit: int = Query(default=5, ge=1, le=20)
) -> List[dict]:
    """
    Get predictions for claims likely to re-emerge.
    
    Uses historical patterns and current context to predict.
    
    Args:
        db: Database session
        limit: Number of predictions to return
    
    Returns:
        List of predictions with cluster info and probability
    """
    memory_graph = get_memory_graph_service()
    if not memory_graph._initialized:
        memory_graph.initialize()
    
    predictions = memory_graph.predict_reemergence(top_k=limit)
    
    results = []
    for cluster_id, probability, reason in predictions:
        cluster = get_cluster_by_id(db, cluster_id)
        if cluster:
            results.append({
                "cluster_id": cluster_id,
                "canonical_text": cluster.canonical_text[:200],
                "probability": round(probability, 3),
                "reason": reason,
                "current_status": cluster.status.value,
                "message_count": cluster.message_count
            })
    
    return results
