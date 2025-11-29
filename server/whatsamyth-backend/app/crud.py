"""
CRUD (Create, Read, Update, Delete) operations for database models.
Provides a clean interface for database operations.
"""

import datetime
import logging
from typing import Optional, List, Dict, Any, Tuple

from sqlalchemy import func, desc, and_
from sqlalchemy.orm import Session

from app.models import (
    Message, ClaimCluster, Verdict, ClaimSeen, 
    ClaimStatus, MessageSource, MemoryGraphEdge
)
from app.schemas import MessageCreate, ClaimStatusEnum

logger = logging.getLogger(__name__)


# ============ Message Operations ============

def create_message(
    db: Session,
    text: str,
    source: str,
    metadata: Optional[Dict[str, Any]] = None,
    language: Optional[str] = "en",
    is_claim: bool = False,
    canonical_text: Optional[str] = None,
    embedding_vector: Optional[List[float]] = None,
    cluster_id: Optional[int] = None
) -> Message:
    """
    Create a new message record in the database.
    
    Args:
        db: Database session
        text: Original message text
        source: Source platform (telegram, discord, etc.)
        metadata: Optional platform-specific metadata
        language: Detected language code
        is_claim: Whether message contains a verifiable claim
        canonical_text: Normalized claim text
        embedding_vector: Vector embedding of the claim
        cluster_id: ID of assigned cluster if any
    
    Returns:
        Created Message object
    """
    message = Message(
        text=text,
        source=source,
        metadata_=metadata,
        language=language,
        is_claim=is_claim,
        canonical_text=canonical_text,
        embedding_vector=embedding_vector,
        cluster_id=cluster_id
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    logger.info(f"Created message id={message.id}, is_claim={is_claim}")
    return message


def update_message_cluster(
    db: Session,
    message_id: int,
    cluster_id: int
) -> Optional[Message]:
    """Update a message's cluster assignment."""
    message = db.query(Message).filter(Message.id == message_id).first()
    if message:
        message.cluster_id = cluster_id
        db.commit()
        db.refresh(message)
    return message


def get_message_by_id(db: Session, message_id: int) -> Optional[Message]:
    """Get a message by its ID."""
    return db.query(Message).filter(Message.id == message_id).first()


def get_recent_messages(
    db: Session,
    limit: int = 100,
    source: Optional[str] = None
) -> List[Message]:
    """Get recent messages, optionally filtered by source."""
    query = db.query(Message).order_by(desc(Message.created_at))
    if source:
        query = query.filter(Message.source == source)
    return query.limit(limit).all()


# ============ Cluster Operations ============

def create_cluster(
    db: Session,
    canonical_text: str,
    topic: Optional[str] = None,
    centroid_embedding: Optional[List[float]] = None,
    status: ClaimStatus = ClaimStatus.UNKNOWN
) -> ClaimCluster:
    """
    Create a new claim cluster.
    
    Args:
        db: Database session
        canonical_text: Representative text for the cluster
        topic: Optional topic category
        centroid_embedding: Average embedding of cluster members
        status: Initial verification status
    
    Returns:
        Created ClaimCluster object
    """
    cluster = ClaimCluster(
        canonical_text=canonical_text,
        topic=topic,
        centroid_embedding=centroid_embedding,
        status=status,
        message_count=1
    )
    db.add(cluster)
    db.commit()
    db.refresh(cluster)
    logger.info(f"Created new cluster id={cluster.id}")
    return cluster


def get_cluster_by_id(db: Session, cluster_id: int) -> Optional[ClaimCluster]:
    """Get a cluster by its ID."""
    return db.query(ClaimCluster).filter(ClaimCluster.id == cluster_id).first()


def update_cluster(
    db: Session,
    cluster_id: int,
    status: Optional[ClaimStatus] = None,
    increment_count: bool = False,
    new_centroid: Optional[List[float]] = None
) -> Optional[ClaimCluster]:
    """
    Update a cluster's properties.
    
    Args:
        db: Database session
        cluster_id: ID of cluster to update
        status: New status if updating
        increment_count: Whether to increment message count
        new_centroid: New centroid embedding if updating
    
    Returns:
        Updated ClaimCluster or None if not found
    """
    cluster = db.query(ClaimCluster).filter(ClaimCluster.id == cluster_id).first()
    if not cluster:
        return None
    
    if status is not None:
        cluster.status = status
    if increment_count:
        cluster.message_count += 1
    if new_centroid is not None:
        cluster.centroid_embedding = new_centroid
    
    cluster.last_seen_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(cluster)
    return cluster


def create_or_update_cluster(
    db: Session,
    canonical_text: str,
    embedding: List[float],
    topic: Optional[str] = None,
    existing_cluster_id: Optional[int] = None
) -> Tuple[ClaimCluster, bool]:
    """
    Create a new cluster or update existing one.
    
    Args:
        db: Database session
        canonical_text: Representative claim text
        embedding: Vector embedding
        topic: Optional topic
        existing_cluster_id: If provided, merge into this cluster
    
    Returns:
        Tuple of (cluster, is_new_cluster)
    """
    if existing_cluster_id:
        cluster = get_cluster_by_id(db, existing_cluster_id)
        if cluster:
            # Update existing cluster
            cluster.message_count += 1
            cluster.last_seen_at = datetime.datetime.utcnow()
            # Update centroid as running average
            if cluster.centroid_embedding:
                old_centroid = cluster.centroid_embedding
                n = cluster.message_count
                new_centroid = [
                    (old * (n - 1) + new) / n 
                    for old, new in zip(old_centroid, embedding)
                ]
                cluster.centroid_embedding = new_centroid
            db.commit()
            db.refresh(cluster)
            return cluster, False
    
    # Create new cluster
    cluster = create_cluster(
        db=db,
        canonical_text=canonical_text,
        topic=topic,
        centroid_embedding=embedding,
        status=ClaimStatus.UNKNOWN
    )
    return cluster, True


def list_clusters(
    db: Session,
    limit: int = 20,
    offset: int = 0,
    status: Optional[ClaimStatus] = None
) -> List[ClaimCluster]:
    """List clusters with optional filtering."""
    query = db.query(ClaimCluster).order_by(desc(ClaimCluster.last_seen_at))
    if status:
        query = query.filter(ClaimCluster.status == status)
    return query.offset(offset).limit(limit).all()


def list_top_clusters(
    db: Session,
    limit: int = 10
) -> List[ClaimCluster]:
    """Get top clusters by message count."""
    return (
        db.query(ClaimCluster)
        .order_by(desc(ClaimCluster.message_count))
        .limit(limit)
        .all()
    )


def get_unknown_clusters(
    db: Session,
    limit: int = 10
) -> List[ClaimCluster]:
    """Get clusters that need verification."""
    return (
        db.query(ClaimCluster)
        .filter(ClaimCluster.status == ClaimStatus.UNKNOWN)
        .order_by(desc(ClaimCluster.message_count))
        .limit(limit)
        .all()
    )


def count_clusters(db: Session) -> int:
    """Count total clusters."""
    return db.query(func.count(ClaimCluster.id)).scalar() or 0


def count_clusters_by_status(db: Session) -> Dict[str, int]:
    """Get count of clusters grouped by status."""
    results = (
        db.query(ClaimCluster.status, func.count(ClaimCluster.id))
        .group_by(ClaimCluster.status)
        .all()
    )
    status_counts = {status.value: 0 for status in ClaimStatus}
    for status, count in results:
        status_counts[status.value] = count
    return status_counts


# ============ Verdict Operations ============

def create_verdict(
    db: Session,
    cluster_id: int,
    status: ClaimStatus = ClaimStatus.UNKNOWN,
    short_reply: Optional[str] = None,
    long_reply: Optional[str] = None,
    sources: Optional[List[Dict[str, Any]]] = None,
    evidence_snippets: Optional[List[str]] = None,
    confidence_score: Optional[float] = None,
    audio_path: Optional[str] = None
) -> Verdict:
    """Create a new verdict for a cluster."""
    verdict = Verdict(
        cluster_id=cluster_id,
        status=status,
        short_reply=short_reply,
        long_reply=long_reply,
        sources=sources,
        evidence_snippets=evidence_snippets,
        confidence_score=confidence_score,
        audio_path=audio_path,
        verified_at=datetime.datetime.utcnow() if status != ClaimStatus.UNKNOWN else None
    )
    db.add(verdict)
    db.commit()
    db.refresh(verdict)
    return verdict


def get_verdict_by_cluster(db: Session, cluster_id: int) -> Optional[Verdict]:
    """Get the verdict for a cluster."""
    return db.query(Verdict).filter(Verdict.cluster_id == cluster_id).first()


def create_verdict_if_missing(
    db: Session,
    cluster_id: int
) -> Verdict:
    """Get existing verdict or create a new UNKNOWN one."""
    verdict = get_verdict_by_cluster(db, cluster_id)
    if verdict:
        return verdict
    return create_verdict(db, cluster_id)


def update_verdict(
    db: Session,
    cluster_id: int,
    status: ClaimStatus,
    short_reply: Optional[str] = None,
    long_reply: Optional[str] = None,
    sources: Optional[List[Dict[str, Any]]] = None,
    evidence_snippets: Optional[List[str]] = None,
    confidence_score: Optional[float] = None,
    audio_path: Optional[str] = None
) -> Optional[Verdict]:
    """Update an existing verdict."""
    verdict = get_verdict_by_cluster(db, cluster_id)
    if not verdict:
        return create_verdict(
            db, cluster_id, status, short_reply, long_reply,
            sources, evidence_snippets, confidence_score, audio_path
        )
    
    verdict.status = status
    if short_reply is not None:
        verdict.short_reply = short_reply
    if long_reply is not None:
        verdict.long_reply = long_reply
    if sources is not None:
        verdict.sources = sources
    if evidence_snippets is not None:
        verdict.evidence_snippets = evidence_snippets
    if confidence_score is not None:
        verdict.confidence_score = confidence_score
    if audio_path is not None:
        verdict.audio_path = audio_path
    
    verdict.verified_at = datetime.datetime.utcnow()
    
    # Also update cluster status
    cluster = get_cluster_by_id(db, cluster_id)
    if cluster:
        cluster.status = status
    
    db.commit()
    db.refresh(verdict)
    return verdict


# ============ ClaimSeen Operations ============

def record_claim_seen(
    db: Session,
    cluster_id: int,
    source: str,
    platform_chat_id: Optional[str] = None,
    platform_user_id: Optional[str] = None
) -> ClaimSeen:
    """Record a sighting of a claim."""
    seen = ClaimSeen(
        cluster_id=cluster_id,
        source=source,
        platform_chat_id=platform_chat_id,
        platform_user_id=platform_user_id
    )
    db.add(seen)
    db.commit()
    db.refresh(seen)
    return seen


def get_claim_seen_history(
    db: Session,
    cluster_id: int,
    limit: int = 100
) -> List[ClaimSeen]:
    """Get sighting history for a cluster."""
    return (
        db.query(ClaimSeen)
        .filter(ClaimSeen.cluster_id == cluster_id)
        .order_by(desc(ClaimSeen.seen_at))
        .limit(limit)
        .all()
    )


# ============ Stats Operations ============

def get_stats_overview(db: Session) -> Dict[str, Any]:
    """
    Get overall statistics for the dashboard.
    
    Returns:
        Dictionary with total counts and breakdowns
    """
    today = datetime.datetime.utcnow().date()
    today_start = datetime.datetime.combine(today, datetime.time.min)
    
    total_messages = db.query(func.count(Message.id)).scalar() or 0
    total_claims = db.query(func.count(Message.id)).filter(Message.is_claim == True).scalar() or 0
    total_clusters = count_clusters(db)
    
    messages_today = (
        db.query(func.count(Message.id))
        .filter(Message.created_at >= today_start)
        .scalar() or 0
    )
    claims_today = (
        db.query(func.count(Message.id))
        .filter(and_(Message.is_claim == True, Message.created_at >= today_start))
        .scalar() or 0
    )
    
    clusters_by_status = count_clusters_by_status(db)
    top_clusters = list_top_clusters(db, limit=5)
    
    return {
        "total_messages": total_messages,
        "total_claims": total_claims,
        "total_clusters": total_clusters,
        "clusters_by_status": clusters_by_status,
        "top_clusters": [
            {
                "cluster_id": c.id,
                "canonical_text": c.canonical_text[:100],
                "message_count": c.message_count,
                "status": c.status.value
            }
            for c in top_clusters
        ],
        "messages_today": messages_today,
        "claims_today": claims_today
    }


# ============ Memory Graph Operations ============

def create_graph_edge(
    db: Session,
    source_cluster_id: int,
    target_cluster_id: int,
    relationship_type: str = "related_to",
    weight: float = 1.0
) -> MemoryGraphEdge:
    """Create an edge between two clusters in the memory graph."""
    edge = MemoryGraphEdge(
        source_cluster_id=source_cluster_id,
        target_cluster_id=target_cluster_id,
        relationship_type=relationship_type,
        weight=weight
    )
    db.add(edge)
    db.commit()
    db.refresh(edge)
    return edge


def get_related_clusters(
    db: Session,
    cluster_id: int
) -> List[int]:
    """Get IDs of clusters related to the given cluster."""
    edges = (
        db.query(MemoryGraphEdge)
        .filter(
            (MemoryGraphEdge.source_cluster_id == cluster_id) |
            (MemoryGraphEdge.target_cluster_id == cluster_id)
        )
        .all()
    )
    related = set()
    for edge in edges:
        if edge.source_cluster_id != cluster_id:
            related.add(edge.source_cluster_id)
        if edge.target_cluster_id != cluster_id:
            related.add(edge.target_cluster_id)
    return list(related)
