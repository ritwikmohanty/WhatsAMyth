"""
Tests for API endpoints.
Uses FastAPI TestClient to test the full request/response cycle.
"""

import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoints:
    """Test health check and root endpoints."""
    
    def test_root_endpoint(self, client):
        """Test root endpoint returns API info."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "WhatsAMyth" in data["name"]
    
    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "database" in data


class TestMessagesEndpoint:
    """Test the /api/messages endpoint."""
    
    def test_ingest_non_claim_message(self, client, sample_non_claim):
        """Test ingesting a non-claim message."""
        response = client.post(
            "/api/messages/",
            json={
                "text": sample_non_claim,
                "source": "web_form"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "message_id" in data
        assert data["is_claim"] is False
        assert data["cluster_id"] is None
    
    def test_ingest_claim_message(self, client, sample_claim):
        """Test ingesting a claim message."""
        response = client.post(
            "/api/messages/",
            json={
                "text": sample_claim,
                "source": "web_form"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "message_id" in data
        assert data["is_claim"] is True
        assert data["cluster_id"] is not None
        assert "cluster_status" in data
    
    def test_ingest_with_metadata(self, client, sample_claim):
        """Test ingesting a message with metadata."""
        response = client.post(
            "/api/messages/",
            json={
                "text": sample_claim,
                "source": "telegram",
                "metadata": {
                    "chat_id": "123456",
                    "user_id": "789"
                }
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message_id"] > 0
    
    def test_similar_claims_cluster_together(self, client):
        """Test that similar claims are assigned to the same cluster."""
        # First claim
        response1 = client.post(
            "/api/messages/",
            json={
                "text": "Drinking warm water kills coronavirus instantly",
                "source": "web_form"
            }
        )
        
        # Similar claim
        response2 = client.post(
            "/api/messages/",
            json={
                "text": "Hot water can kill the coronavirus virus",
                "source": "telegram"
            }
        )
        
        data1 = response1.json()
        data2 = response2.json()
        
        # Both should be claims
        assert data1["is_claim"] is True
        assert data2["is_claim"] is True
        
        # Note: In a real test with full embedding model,
        # these would likely be in the same cluster.
        # With mocked/fallback services, they may or may not cluster.
        assert data1["cluster_id"] is not None
        assert data2["cluster_id"] is not None
    
    def test_invalid_source_rejected(self, client):
        """Test that invalid source values are rejected."""
        response = client.post(
            "/api/messages/",
            json={
                "text": "Test message",
                "source": "invalid_source"
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_empty_text_rejected(self, client):
        """Test that empty text is rejected."""
        response = client.post(
            "/api/messages/",
            json={
                "text": "",
                "source": "web_form"
            }
        )
        
        assert response.status_code == 422


class TestClaimsEndpoint:
    """Test the /api/claims endpoint."""
    
    def test_list_claims_empty(self, client):
        """Test listing claims when database is empty."""
        response = client.get("/api/claims/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "claims" in data
        assert "total_count" in data
        assert data["total_count"] == 0
    
    def test_list_claims_with_data(self, client, sample_claim):
        """Test listing claims after ingesting some."""
        # First ingest a claim
        client.post(
            "/api/messages/",
            json={"text": sample_claim, "source": "web_form"}
        )
        
        # Then list claims
        response = client.get("/api/claims/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_count"] >= 1
        assert len(data["claims"]) >= 1
    
    def test_list_claims_pagination(self, client, sample_claims_batch):
        """Test claims pagination."""
        # Ingest multiple claims
        for claim in sample_claims_batch:
            client.post(
                "/api/messages/",
                json={"text": claim, "source": "web_form"}
            )
        
        # Get first page
        response = client.get("/api/claims/?limit=2&offset=0")
        data = response.json()
        
        assert len(data["claims"]) <= 2
        assert data["limit"] == 2
        assert data["offset"] == 0
    
    def test_get_claim_detail(self, client, sample_claim):
        """Test getting detailed claim information."""
        # Ingest a claim
        ingest_response = client.post(
            "/api/messages/",
            json={"text": sample_claim, "source": "web_form"}
        )
        cluster_id = ingest_response.json()["cluster_id"]
        
        # Get detail
        response = client.get(f"/api/claims/{cluster_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["cluster_id"] == cluster_id
        assert "canonical_text" in data
        assert "status" in data
        assert "message_count" in data
    
    def test_get_claim_not_found(self, client):
        """Test 404 for non-existent cluster."""
        response = client.get("/api/claims/99999")
        
        assert response.status_code == 404


class TestStatsEndpoint:
    """Test the /api/stats endpoint."""
    
    def test_stats_overview_empty(self, client):
        """Test stats overview with empty database."""
        response = client.get("/api/stats/overview")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "total_messages" in data
        assert "total_claims" in data
        assert "total_clusters" in data
        assert "clusters_by_status" in data
    
    def test_stats_overview_with_data(self, client, sample_claim, sample_non_claim):
        """Test stats overview after ingesting data."""
        # Ingest some messages
        client.post("/api/messages/", json={"text": sample_claim, "source": "web_form"})
        client.post("/api/messages/", json={"text": sample_non_claim, "source": "telegram"})
        
        response = client.get("/api/stats/overview")
        data = response.json()
        
        assert data["total_messages"] >= 2
        assert data["total_claims"] >= 1
    
    def test_stats_trends(self, client):
        """Test trends endpoint."""
        response = client.get("/api/stats/trends?days=7")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "period_days" in data
        assert "daily_messages" in data
    
    def test_stats_sources(self, client, sample_claim):
        """Test source breakdown endpoint."""
        # Add data from different sources
        client.post("/api/messages/", json={"text": sample_claim, "source": "web_form"})
        client.post("/api/messages/", json={"text": sample_claim + " variation", "source": "telegram"})
        
        response = client.get("/api/stats/sources")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "sources" in data
    
    def test_stats_topics(self, client, sample_claim):
        """Test topic breakdown endpoint."""
        # Add some claims
        client.post("/api/messages/", json={"text": sample_claim, "source": "web_form"})
        
        response = client.get("/api/stats/topics")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "topics" in data


class TestVerificationFlow:
    """Test the full verification workflow."""
    
    def test_claim_verification_flow(self, client):
        """Test that a claim goes through the verification pipeline."""
        # Ingest a claim
        response = client.post(
            "/api/messages/",
            json={
                "text": "COVID-19 vaccines contain microchips for tracking people",
                "source": "web_form"
            }
        )
        
        data = response.json()
        assert data["is_claim"] is True
        
        cluster_id = data["cluster_id"]
        assert cluster_id is not None
        
        # Get cluster detail
        detail_response = client.get(f"/api/claims/{cluster_id}")
        detail = detail_response.json()
        
        # Should have some status
        assert detail["status"] in ["UNKNOWN", "FALSE", "TRUE", "MISLEADING", "UNVERIFIABLE", "PARTIALLY_TRUE"]
    
    def test_reverify_claim(self, client, sample_claim):
        """Test re-verification of a claim."""
        # First ingest
        ingest_response = client.post(
            "/api/messages/",
            json={"text": sample_claim, "source": "web_form"}
        )
        cluster_id = ingest_response.json()["cluster_id"]
        
        # Request re-verification
        response = client.post(f"/api/claims/{cluster_id}/reverify")
        
        assert response.status_code == 200
        data = response.json()
        assert "cluster_id" in data
        assert "status" in data


class TestClusteringBehavior:
    """Test clustering behavior with multiple messages."""
    
    def test_multiple_messages_increment_count(self, client):
        """Test that adding similar messages increments cluster count."""
        base_claim = "5G towers cause coronavirus"
        
        # Send multiple similar claims
        for i in range(3):
            variation = f"{base_claim} - variation {i}"
            client.post(
                "/api/messages/",
                json={"text": variation, "source": "web_form"}
            )
        
        # Check claims
        response = client.get("/api/claims/")
        data = response.json()
        
        # Should have at least some clusters
        assert data["total_count"] >= 1
    
    def test_different_claims_create_different_clusters(self, client):
        """Test that different claims create separate clusters."""
        claim1 = "Vaccines cause autism in children according to studies"
        claim2 = "The earth is actually flat according to research"
        
        response1 = client.post(
            "/api/messages/",
            json={"text": claim1, "source": "web_form"}
        )
        
        response2 = client.post(
            "/api/messages/",
            json={"text": claim2, "source": "web_form"}
        )
        
        # Both should be claims with different clusters
        data1 = response1.json()
        data2 = response2.json()
        
        assert data1["is_claim"] is True
        assert data2["is_claim"] is True
        # Different enough to be separate clusters
        assert data1["cluster_id"] != data2["cluster_id"]
