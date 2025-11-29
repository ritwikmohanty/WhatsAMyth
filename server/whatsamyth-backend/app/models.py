"""
SQLAlchemy ORM models for the WhatsAMyth application.
Defines the database schema for messages, claims, clusters, and verdicts.
"""

import datetime
from enum import Enum as PyEnum
from typing import Optional, List

from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, 
    JSON, Text, Float, Boolean, Enum, Index
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class ClaimStatus(str, PyEnum):
    """Possible verification statuses for a claim cluster."""
    UNKNOWN = "UNKNOWN"
    TRUE = "TRUE"
    FALSE = "FALSE"
    MISLEADING = "MISLEADING"
    UNVERIFIABLE = "UNVERIFIABLE"
    PARTIALLY_TRUE = "PARTIALLY_TRUE"


class MessageSource(str, PyEnum):
    """Sources from which messages can originate."""
    WEB_FORM = "web_form"
    TELEGRAM = "telegram"
    DISCORD = "discord"
    WHATSAPP_MOCK = "whatsapp_mock"
    API = "api"


class Message(Base):
    """
    Represents a single incoming message that may contain a claim.
    Messages are clustered together when they express similar claims.
    """
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    text = Column(Text, nullable=False)
    source = Column(String(50), nullable=False, default=MessageSource.WEB_FORM.value)
    metadata_ = Column("metadata", JSON, nullable=True)  # Renamed to avoid conflict
    language = Column(String(10), nullable=True, default="en")
    is_claim = Column(Boolean, default=False)
    canonical_text = Column(Text, nullable=True)
    embedding_vector = Column(JSON, nullable=True)  # Store as JSON list
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Foreign key to cluster
    cluster_id = Column(Integer, ForeignKey("claim_clusters.id"), nullable=True)
    
    # Relationships
    cluster = relationship("ClaimCluster", back_populates="messages")
    
    # Indexes for common queries
    __table_args__ = (
        Index("ix_messages_source", "source"),
        Index("ix_messages_created_at", "created_at"),
        Index("ix_messages_cluster_id", "cluster_id"),
        Index("ix_messages_is_claim", "is_claim"),
    )
    
    def __repr__(self):
        return f"<Message(id={self.id}, source={self.source}, is_claim={self.is_claim})>"


class ClaimCluster(Base):
    """
    Represents a cluster of similar claims.
    Multiple messages expressing the same claim are grouped into one cluster.
    """
    __tablename__ = "claim_clusters"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    canonical_text = Column(Text, nullable=False)
    topic = Column(String(100), nullable=True)
    status = Column(
        Enum(ClaimStatus), 
        default=ClaimStatus.UNKNOWN, 
        nullable=False
    )
    message_count = Column(Integer, default=1)
    centroid_embedding = Column(JSON, nullable=True)  # Average embedding of cluster
    
    first_seen_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_seen_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationships
    messages = relationship("Message", back_populates="cluster")
    verdicts = relationship("Verdict", back_populates="cluster", cascade="all, delete-orphan")
    seen_records = relationship("ClaimSeen", back_populates="cluster", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("ix_clusters_status", "status"),
        Index("ix_clusters_topic", "topic"),
        Index("ix_clusters_message_count", "message_count"),
        Index("ix_clusters_last_seen", "last_seen_at"),
    )
    
    def __repr__(self):
        return f"<ClaimCluster(id={self.id}, status={self.status}, count={self.message_count})>"


class Verdict(Base):
    """
    Stores the verification verdict for a claim cluster.
    Includes evidence, sources, and both short and long explanations.
    """
    __tablename__ = "verdicts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    cluster_id = Column(Integer, ForeignKey("claim_clusters.id"), nullable=False, unique=True)
    
    status = Column(Enum(ClaimStatus), default=ClaimStatus.UNKNOWN, nullable=False)
    confidence_score = Column(Float, nullable=True)
    
    short_reply = Column(Text, nullable=True)  # WhatsApp-ready short response
    long_reply = Column(Text, nullable=True)   # Detailed explanation
    
    sources = Column(JSON, nullable=True)  # List of source URLs and snippets
    evidence_snippets = Column(JSON, nullable=True)  # Raw evidence collected
    
    audio_path = Column(String(255), nullable=True)  # Path to generated TTS audio
    
    verified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationships
    cluster = relationship("ClaimCluster", back_populates="verdicts")
    
    def __repr__(self):
        return f"<Verdict(id={self.id}, cluster_id={self.cluster_id}, status={self.status})>"


class ClaimSeen(Base):
    """
    Records each sighting of a claim across different platforms.
    Tracks when and where claims appear for trend analysis.
    """
    __tablename__ = "claim_seen"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    cluster_id = Column(Integer, ForeignKey("claim_clusters.id"), nullable=False)
    
    source = Column(String(50), nullable=False)
    platform_chat_id = Column(String(100), nullable=True)
    platform_user_id = Column(String(100), nullable=True)  # Hashed for privacy
    
    seen_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    cluster = relationship("ClaimCluster", back_populates="seen_records")
    
    # Indexes
    __table_args__ = (
        Index("ix_claimseen_cluster_id", "cluster_id"),
        Index("ix_claimseen_source", "source"),
        Index("ix_claimseen_seen_at", "seen_at"),
    )
    
    def __repr__(self):
        return f"<ClaimSeen(id={self.id}, cluster_id={self.cluster_id}, source={self.source})>"


class MemoryGraphEdge(Base):
    """
    Stores edges for the memory graph (cluster relationships).
    Used for predicting claim re-emergence.
    """
    __tablename__ = "memory_graph_edges"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    source_cluster_id = Column(Integer, ForeignKey("claim_clusters.id"), nullable=False)
    target_cluster_id = Column(Integer, ForeignKey("claim_clusters.id"), nullable=False)
    
    relationship_type = Column(String(50), default="related_to")
    weight = Column(Float, default=1.0)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index("ix_edges_source", "source_cluster_id"),
        Index("ix_edges_target", "target_cluster_id"),
    )
    
    def __repr__(self):
        return f"<MemoryGraphEdge(source={self.source_cluster_id}, target={self.target_cluster_id})>"
