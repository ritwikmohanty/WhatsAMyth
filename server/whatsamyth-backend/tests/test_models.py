"""
Tests for database models and CRUD operations.
"""

import pytest
from datetime import datetime

from app.models import (
    Message, ClaimCluster, Verdict, ClaimSeen,
    ClaimStatus, MessageSource
)
from app.crud import (
    create_message, create_cluster, get_cluster_by_id,
    create_verdict, get_verdict_by_cluster, update_verdict,
    create_or_update_cluster, get_stats_overview,
    record_claim_seen, list_clusters, count_clusters
)


class TestModels:
    """Test database model creation and relationships."""
    
    def test_create_message(self, db):
        """Test creating a simple message."""
        message = create_message(
            db=db,
            text="Test message text",
            source="web_form",
            language="en",
            is_claim=False
        )
        
        assert message.id is not None
        assert message.text == "Test message text"
        assert message.source == "web_form"
        assert message.language == "en"
        assert message.is_claim is False
        assert message.created_at is not None
    
    def test_create_message_with_metadata(self, db):
        """Test creating a message with metadata."""
        metadata = {"chat_id": "123", "user_id": "456"}
        
        message = create_message(
            db=db,
            text="Test with metadata",
            source="telegram",
            metadata=metadata
        )
        
        assert message.metadata_ == metadata
    
    def test_create_claim_message(self, db):
        """Test creating a claim message with embedding."""
        embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
        
        message = create_message(
            db=db,
            text="Vaccines cause autism",
            source="discord",
            is_claim=True,
            canonical_text="Vaccines cause autism",
            embedding_vector=embedding
        )
        
        assert message.is_claim is True
        assert message.canonical_text == "Vaccines cause autism"
        assert message.embedding_vector == embedding
    
    def test_create_cluster(self, db):
        """Test creating a claim cluster."""
        cluster = create_cluster(
            db=db,
            canonical_text="Test claim for cluster",
            topic="health",
            status=ClaimStatus.UNKNOWN
        )
        
        assert cluster.id is not None
        assert cluster.canonical_text == "Test claim for cluster"
        assert cluster.topic == "health"
        assert cluster.status == ClaimStatus.UNKNOWN
        assert cluster.message_count == 1
        assert cluster.first_seen_at is not None
    
    def test_cluster_message_relationship(self, db):
        """Test relationship between cluster and messages."""
        # Create cluster
        cluster = create_cluster(
            db=db,
            canonical_text="Test cluster",
            topic="general"
        )
        
        # Create messages linked to cluster
        msg1 = create_message(
            db=db,
            text="First message",
            source="web_form",
            is_claim=True,
            cluster_id=cluster.id
        )
        
        msg2 = create_message(
            db=db,
            text="Second message",
            source="telegram",
            is_claim=True,
            cluster_id=cluster.id
        )
        
        # Refresh cluster to get relationships
        db.refresh(cluster)
        
        assert len(cluster.messages) == 2
        assert msg1 in cluster.messages
        assert msg2 in cluster.messages
    
    def test_create_verdict(self, db):
        """Test creating a verdict for a cluster."""
        cluster = create_cluster(
            db=db,
            canonical_text="Claim for verdict",
            topic="health"
        )
        
        verdict = create_verdict(
            db=db,
            cluster_id=cluster.id,
            status=ClaimStatus.FALSE,
            short_reply="This claim is false.",
            long_reply="Detailed explanation of why this is false.",
            confidence_score=0.85
        )
        
        assert verdict.id is not None
        assert verdict.cluster_id == cluster.id
        assert verdict.status == ClaimStatus.FALSE
        assert verdict.short_reply == "This claim is false."
        assert verdict.confidence_score == 0.85
    
    def test_get_verdict_by_cluster(self, db):
        """Test retrieving verdict by cluster ID."""
        cluster = create_cluster(db=db, canonical_text="Test")
        
        # No verdict yet
        verdict = get_verdict_by_cluster(db, cluster.id)
        assert verdict is None
        
        # Create verdict
        create_verdict(
            db=db,
            cluster_id=cluster.id,
            status=ClaimStatus.TRUE,
            short_reply="True claim"
        )
        
        # Now should find it
        verdict = get_verdict_by_cluster(db, cluster.id)
        assert verdict is not None
        assert verdict.status == ClaimStatus.TRUE
    
    def test_update_verdict(self, db):
        """Test updating a verdict."""
        cluster = create_cluster(db=db, canonical_text="Test")
        
        # Create initial verdict
        create_verdict(
            db=db,
            cluster_id=cluster.id,
            status=ClaimStatus.UNKNOWN
        )
        
        # Update verdict
        updated = update_verdict(
            db=db,
            cluster_id=cluster.id,
            status=ClaimStatus.FALSE,
            short_reply="Now confirmed false",
            confidence_score=0.9
        )
        
        assert updated.status == ClaimStatus.FALSE
        assert updated.short_reply == "Now confirmed false"
        assert updated.confidence_score == 0.9
        assert updated.verified_at is not None
    
    def test_record_claim_seen(self, db):
        """Test recording claim sightings."""
        cluster = create_cluster(db=db, canonical_text="Test claim")
        
        seen1 = record_claim_seen(
            db=db,
            cluster_id=cluster.id,
            source="telegram",
            platform_chat_id="chat123"
        )
        
        seen2 = record_claim_seen(
            db=db,
            cluster_id=cluster.id,
            source="discord",
            platform_chat_id="channel456"
        )
        
        # Refresh and check
        db.refresh(cluster)
        assert len(cluster.seen_records) == 2
    
    def test_list_clusters(self, db):
        """Test listing clusters with pagination."""
        # Create multiple clusters
        for i in range(5):
            create_cluster(
                db=db,
                canonical_text=f"Cluster {i}",
                topic="test"
            )
        
        # List with limit
        clusters = list_clusters(db, limit=3)
        assert len(clusters) == 3
        
        # Count total
        total = count_clusters(db)
        assert total == 5
    
    def test_get_stats_overview(self, db):
        """Test getting stats overview."""
        # Create some test data
        cluster1 = create_cluster(db=db, canonical_text="Claim 1")
        cluster2 = create_cluster(db=db, canonical_text="Claim 2", status=ClaimStatus.FALSE)
        
        create_message(db=db, text="Msg 1", source="web_form", is_claim=True, cluster_id=cluster1.id)
        create_message(db=db, text="Msg 2", source="telegram", is_claim=True, cluster_id=cluster2.id)
        create_message(db=db, text="Msg 3", source="discord", is_claim=False)
        
        stats = get_stats_overview(db)
        
        assert stats["total_messages"] == 3
        assert stats["total_claims"] == 2
        assert stats["total_clusters"] == 2
        assert "UNKNOWN" in stats["clusters_by_status"]
        assert "FALSE" in stats["clusters_by_status"]


class TestCRUDOperations:
    """Test CRUD helper functions."""
    
    def test_create_or_update_cluster_new(self, db):
        """Test creating new cluster via create_or_update."""
        embedding = [0.1] * 768
        
        cluster, is_new = create_or_update_cluster(
            db=db,
            canonical_text="New claim",
            embedding=embedding,
            topic="test"
        )
        
        assert is_new is True
        assert cluster.message_count == 1
    
    def test_create_or_update_cluster_existing(self, db):
        """Test merging into existing cluster."""
        embedding1 = [0.1] * 768
        embedding2 = [0.2] * 768
        
        # Create first cluster
        cluster1, _ = create_or_update_cluster(
            db=db,
            canonical_text="First claim",
            embedding=embedding1
        )
        
        # Merge into existing
        cluster2, is_new = create_or_update_cluster(
            db=db,
            canonical_text="Similar claim",
            embedding=embedding2,
            existing_cluster_id=cluster1.id
        )
        
        assert is_new is False
        assert cluster2.id == cluster1.id
        assert cluster2.message_count == 2
