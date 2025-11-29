"""
Stats Router
Endpoints for dashboard statistics and analytics.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import StatsOverviewResponse, ClustersByStatus, TopCluster, ClaimStatusEnum
from app.crud import get_stats_overview, list_top_clusters
from app.models import Message, ClaimCluster, ClaimSeen, ClaimStatus
from app.services.memory_graph import get_memory_graph_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/overview", response_model=StatsOverviewResponse)
def get_overview(db: Session = Depends(get_db)) -> StatsOverviewResponse:
    """
    Get overall statistics for the dashboard.
    
    Returns:
        StatsOverviewResponse with counts and top clusters
    """
    stats = get_stats_overview(db)
    
    # Build clusters by status
    status_counts = stats["clusters_by_status"]
    clusters_by_status = ClustersByStatus(
        unknown=status_counts.get("UNKNOWN", 0),
        true_=status_counts.get("TRUE", 0),
        false_=status_counts.get("FALSE", 0),
        misleading=status_counts.get("MISLEADING", 0),
        unverifiable=status_counts.get("UNVERIFIABLE", 0),
        partially_true=status_counts.get("PARTIALLY_TRUE", 0)
    )
    
    # Build top clusters
    top_clusters = [
        TopCluster(
            cluster_id=c["cluster_id"],
            canonical_text=c["canonical_text"],
            message_count=c["message_count"],
            status=ClaimStatusEnum(c["status"])
        )
        for c in stats["top_clusters"]
    ]
    
    return StatsOverviewResponse(
        total_messages=stats["total_messages"],
        total_claims=stats["total_claims"],
        total_clusters=stats["total_clusters"],
        clusters_by_status=clusters_by_status,
        top_clusters=top_clusters,
        messages_today=stats.get("messages_today", 0),
        claims_today=stats.get("claims_today", 0)
    )


@router.get("/trends")
def get_trends(
    db: Session = Depends(get_db),
    days: int = Query(default=7, ge=1, le=90)
) -> dict:
    """
    Get trend data for the specified number of days.
    
    Returns message and claim counts per day.
    
    Args:
        db: Database session
        days: Number of days to include in trends
    
    Returns:
        Dict with daily trend data
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Get daily message counts
    daily_messages = (
        db.query(
            func.date(Message.created_at).label("date"),
            func.count(Message.id).label("count")
        )
        .filter(Message.created_at >= start_date)
        .group_by(func.date(Message.created_at))
        .order_by(func.date(Message.created_at))
        .all()
    )
    
    # Get daily claim counts
    daily_claims = (
        db.query(
            func.date(Message.created_at).label("date"),
            func.count(Message.id).label("count")
        )
        .filter(
            and_(
                Message.created_at >= start_date,
                Message.is_claim == True
            )
        )
        .group_by(func.date(Message.created_at))
        .order_by(func.date(Message.created_at))
        .all()
    )
    
    # Get daily new cluster counts
    daily_clusters = (
        db.query(
            func.date(ClaimCluster.first_seen_at).label("date"),
            func.count(ClaimCluster.id).label("count")
        )
        .filter(ClaimCluster.first_seen_at >= start_date)
        .group_by(func.date(ClaimCluster.first_seen_at))
        .order_by(func.date(ClaimCluster.first_seen_at))
        .all()
    )
    
    return {
        "period_days": days,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "daily_messages": [
            {"date": str(d.date), "count": d.count}
            for d in daily_messages
        ],
        "daily_claims": [
            {"date": str(d.date), "count": d.count}
            for d in daily_claims
        ],
        "daily_new_clusters": [
            {"date": str(d.date), "count": d.count}
            for d in daily_clusters
        ]
    }


@router.get("/sources")
def get_source_breakdown(db: Session = Depends(get_db)) -> dict:
    """
    Get breakdown of messages by source platform.
    
    Returns:
        Dict with counts per source
    """
    source_counts = (
        db.query(
            Message.source,
            func.count(Message.id).label("count")
        )
        .group_by(Message.source)
        .all()
    )
    
    return {
        "sources": [
            {"source": s.source, "count": s.count}
            for s in source_counts
        ]
    }


@router.get("/topics")
def get_topic_breakdown(db: Session = Depends(get_db)) -> dict:
    """
    Get breakdown of claims by topic.
    
    Returns:
        Dict with counts per topic
    """
    topic_counts = (
        db.query(
            ClaimCluster.topic,
            func.count(ClaimCluster.id).label("count"),
            func.sum(ClaimCluster.message_count).label("total_messages")
        )
        .group_by(ClaimCluster.topic)
        .order_by(func.sum(ClaimCluster.message_count).desc())
        .all()
    )
    
    return {
        "topics": [
            {
                "topic": t.topic or "general",
                "cluster_count": t.count,
                "message_count": t.total_messages or 0
            }
            for t in topic_counts
        ]
    }


@router.get("/verification-rate")
def get_verification_rate(db: Session = Depends(get_db)) -> dict:
    """
    Get verification rate statistics.
    
    Returns:
        Dict with verification status breakdown
    """
    total_clusters = db.query(func.count(ClaimCluster.id)).scalar() or 0
    
    if total_clusters == 0:
        return {
            "total_clusters": 0,
            "verified": 0,
            "unverified": 0,
            "verification_rate": 0.0,
            "status_breakdown": {}
        }
    
    status_counts = (
        db.query(
            ClaimCluster.status,
            func.count(ClaimCluster.id).label("count")
        )
        .group_by(ClaimCluster.status)
        .all()
    )
    
    status_breakdown = {s.status.value: s.count for s in status_counts}
    
    unverified = status_breakdown.get("UNKNOWN", 0)
    verified = total_clusters - unverified
    
    return {
        "total_clusters": total_clusters,
        "verified": verified,
        "unverified": unverified,
        "verification_rate": round(verified / total_clusters, 3) if total_clusters > 0 else 0.0,
        "status_breakdown": status_breakdown
    }


@router.get("/activity-heatmap")
def get_activity_heatmap(
    db: Session = Depends(get_db),
    days: int = Query(default=7, ge=1, le=30)
) -> dict:
    """
    Get hourly activity heatmap data.
    
    Returns message counts per hour per day of week.
    
    Args:
        db: Database session
        days: Number of days to analyze
    
    Returns:
        Dict with heatmap data
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Get hourly counts
    # Note: This is database-specific; this example works with PostgreSQL
    try:
        hourly_data = (
            db.query(
                func.extract('dow', Message.created_at).label('day_of_week'),
                func.extract('hour', Message.created_at).label('hour'),
                func.count(Message.id).label('count')
            )
            .filter(Message.created_at >= start_date)
            .group_by('day_of_week', 'hour')
            .all()
        )
        
        # Build heatmap matrix (7 days x 24 hours)
        heatmap = [[0 for _ in range(24)] for _ in range(7)]
        for row in hourly_data:
            day = int(row.day_of_week)
            hour = int(row.hour)
            heatmap[day][hour] = row.count
        
        return {
            "period_days": days,
            "heatmap": heatmap,
            "day_labels": ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
            "hour_labels": [f"{h:02d}:00" for h in range(24)]
        }
        
    except Exception as e:
        logger.error(f"Heatmap query failed: {e}")
        return {
            "period_days": days,
            "heatmap": [],
            "error": "Database does not support this query"
        }


@router.get("/graph-stats")
def get_graph_stats(db: Session = Depends(get_db)) -> dict:
    """
    Get memory graph statistics.
    
    Returns:
        Dict with graph metrics
    """
    memory_graph = get_memory_graph_service()
    if not memory_graph._initialized:
        memory_graph.initialize()
    
    return memory_graph.get_graph_stats()


@router.get("/recent-activity")
def get_recent_activity(
    db: Session = Depends(get_db),
    limit: int = Query(default=10, ge=1, le=50)
) -> dict:
    """
    Get recent activity feed.
    
    Shows recent messages and cluster updates.
    
    Args:
        db: Database session
        limit: Number of items to return
    
    Returns:
        Dict with recent activity items
    """
    # Recent messages
    recent_messages = (
        db.query(Message)
        .order_by(Message.created_at.desc())
        .limit(limit)
        .all()
    )
    
    # Recent cluster updates
    recent_clusters = (
        db.query(ClaimCluster)
        .order_by(ClaimCluster.last_seen_at.desc())
        .limit(limit)
        .all()
    )
    
    activity = []
    
    for m in recent_messages:
        activity.append({
            "type": "message",
            "timestamp": m.created_at.isoformat(),
            "id": m.id,
            "text": m.text[:100] + "..." if len(m.text) > 100 else m.text,
            "source": m.source,
            "is_claim": m.is_claim,
            "cluster_id": m.cluster_id
        })
    
    for c in recent_clusters:
        activity.append({
            "type": "cluster_update",
            "timestamp": c.last_seen_at.isoformat(),
            "id": c.id,
            "text": c.canonical_text[:100] + "..." if len(c.canonical_text) > 100 else c.canonical_text,
            "status": c.status.value,
            "message_count": c.message_count
        })
    
    # Sort by timestamp
    activity.sort(key=lambda x: x["timestamp"], reverse=True)
    
    return {
        "activity": activity[:limit]
    }
