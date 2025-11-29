"""
Pydantic schemas for API request/response validation.
Matches the API contract specification exactly.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


# Enums matching the API contract
class ClaimStatusEnum(str, Enum):
    """Verification status options."""
    UNKNOWN = "UNKNOWN"
    TRUE = "TRUE"
    FALSE = "FALSE"
    MISLEADING = "MISLEADING"
    UNVERIFIABLE = "UNVERIFIABLE"
    PARTIALLY_TRUE = "PARTIALLY_TRUE"


class MessageSourceEnum(str, Enum):
    """Valid message sources."""
    WEB_FORM = "web_form"
    TELEGRAM = "telegram"
    DISCORD = "discord"
    WHATSAPP_MOCK = "whatsapp_mock"
    API = "api"


# ============ Message Schemas ============

class MessageMetadata(BaseModel):
    """Optional metadata for incoming messages."""
    chat_id: Optional[str] = None
    user_id: Optional[str] = None
    reply_to_message_id: Optional[str] = None
    platform_specific: Optional[Dict[str, Any]] = None


class MessageCreate(BaseModel):
    """
    Request schema for POST /api/messages
    """
    text: str = Field(..., min_length=1, max_length=10000, description="Message text to analyze")
    source: MessageSourceEnum = Field(default=MessageSourceEnum.WEB_FORM, description="Source platform")
    metadata: Optional[MessageMetadata] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "text": "COVID-19 vaccine contains microchips for tracking",
                "source": "telegram",
                "metadata": {"chat_id": "123456", "user_id": "789"}
            }
        }
    )


class MessageIngestResponse(BaseModel):
    """
    Response schema for POST /api/messages
    """
    message_id: int = Field(..., description="Unique ID of the stored message")
    is_claim: bool = Field(..., description="Whether the message contains a verifiable claim")
    cluster_id: Optional[int] = Field(None, description="ID of the claim cluster if is_claim=true")
    cluster_status: Optional[ClaimStatusEnum] = Field(None, description="Current verification status")
    short_reply: Optional[str] = Field(None, description="WhatsApp-ready short response")
    audio_url: Optional[str] = Field(None, description="URL to audio file of the reply")
    needs_verification: bool = Field(False, description="Whether this claim needs verification")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message_id": 123,
                "is_claim": True,
                "cluster_id": 7,
                "cluster_status": "FALSE",
                "short_reply": "This claim is FALSE. COVID-19 vaccines do not contain microchips.",
                "audio_url": "/media/replies/123.mp3",
                "needs_verification": False
            }
        }
    )


# ============ Claim/Cluster Schemas ============

class ClusterSummary(BaseModel):
    """Summary view of a claim cluster for list endpoints."""
    cluster_id: int
    canonical_text: str
    topic: Optional[str] = None
    status: ClaimStatusEnum
    message_count: int
    first_seen_at: datetime
    last_seen_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class EvidenceItem(BaseModel):
    """A single piece of evidence for a verdict."""
    source_url: str
    source_name: Optional[str] = None
    snippet: str
    relevance_score: Optional[float] = None
    retrieved_at: Optional[datetime] = None


class VerdictDetail(BaseModel):
    """Detailed verdict information."""
    status: ClaimStatusEnum
    confidence_score: Optional[float] = None
    short_reply: Optional[str] = None
    long_reply: Optional[str] = None
    sources: Optional[List[EvidenceItem]] = None
    verified_at: Optional[datetime] = None
    audio_url: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class ClusterDetail(BaseModel):
    """
    Response schema for GET /api/claims/{cluster_id}
    Full details of a claim cluster including verdict.
    """
    cluster_id: int
    canonical_text: str
    topic: Optional[str] = None
    status: ClaimStatusEnum
    message_count: int
    first_seen_at: datetime
    last_seen_at: datetime
    verdict: Optional[VerdictDetail] = None
    related_clusters: Optional[List[int]] = None
    
    model_config = ConfigDict(from_attributes=True)


class ClaimsListResponse(BaseModel):
    """Response schema for GET /api/claims"""
    claims: List[ClusterSummary]
    total_count: int
    limit: int
    offset: int


# ============ Stats Schemas ============

class ClustersByStatus(BaseModel):
    """Breakdown of clusters by verification status."""
    unknown: int = 0
    true_: int = Field(0, alias="true")
    false_: int = Field(0, alias="false")
    misleading: int = 0
    unverifiable: int = 0
    partially_true: int = 0
    
    model_config = ConfigDict(populate_by_name=True)


class TopCluster(BaseModel):
    """A top trending cluster."""
    cluster_id: int
    canonical_text: str
    message_count: int
    status: ClaimStatusEnum


class StatsOverviewResponse(BaseModel):
    """
    Response schema for GET /api/stats/overview
    """
    total_messages: int
    total_claims: int
    total_clusters: int
    clusters_by_status: ClustersByStatus
    top_clusters: List[TopCluster]
    messages_today: int = 0
    claims_today: int = 0
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_messages": 1500,
                "total_claims": 800,
                "total_clusters": 150,
                "clusters_by_status": {
                    "unknown": 30,
                    "true": 40,
                    "false": 50,
                    "misleading": 20,
                    "unverifiable": 10
                },
                "top_clusters": [
                    {
                        "cluster_id": 7,
                        "canonical_text": "COVID vaccine contains microchips",
                        "message_count": 45,
                        "status": "FALSE"
                    }
                ]
            }
        }
    )


# ============ Bot Internal Schemas ============

class BotMessagePayload(BaseModel):
    """Internal payload from bots to the API."""
    text: str
    source: MessageSourceEnum
    metadata: Optional[MessageMetadata] = None
    internal_token: str = Field(..., description="Secret token for bot authentication")


# ============ Health Check ============

class HealthCheck(BaseModel):
    """Health check response."""
    status: str = "healthy"
    database: bool = True
    faiss_index_loaded: bool = True
    timestamp: datetime = Field(default_factory=datetime.utcnow)
