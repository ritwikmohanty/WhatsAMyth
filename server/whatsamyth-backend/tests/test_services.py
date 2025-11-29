"""
Tests for service layer (detection, embedding, clustering).
"""

import pytest
import numpy as np
from unittest.mock import patch, MagicMock

from app.services.detection import (
    is_claim, extract_canonical_claim, detect_language,
    get_claim_topics, _rule_based_claim_score
)


class TestDetectionService:
    """Tests for claim detection service."""
    
    def test_is_claim_with_health_misinformation(self):
        """Test detection of health-related misinformation."""
        claims = [
            "Drinking warm water kills coronavirus instantly",
            "Vaccines cause autism in children",
            "5G towers spread COVID-19",
            "This natural cure prevents cancer 100%",
        ]
        
        for claim in claims:
            # Rule-based should catch these
            score = _rule_based_claim_score(claim)
            assert score > 0, f"Failed to detect: {claim}"
    
    def test_is_not_claim_for_questions(self):
        """Test that questions are not classified as claims."""
        questions = [
            "What is the weather like today?",
            "How do I get to the train station?",
            "Who is the president of France?",
        ]
        
        for question in questions:
            score = _rule_based_claim_score(question)
            assert score == 0, f"Incorrectly detected as claim: {question}"
    
    def test_is_not_claim_for_opinions(self):
        """Test that opinions are not classified as claims."""
        opinions = [
            "I think this movie is great",
            "In my opinion, pizza is the best food",
            "I believe we should help each other",
        ]
        
        for opinion in opinions:
            score = _rule_based_claim_score(opinion)
            assert score == 0, f"Incorrectly detected as claim: {opinion}"
    
    def test_is_not_claim_for_short_text(self):
        """Test that very short text is not classified as claim."""
        assert _rule_based_claim_score("Hi") == 0
        assert _rule_based_claim_score("Hello there") == 0
        assert _rule_based_claim_score("OK") == 0
    
    def test_extract_canonical_claim_removes_urls(self):
        """Test that URLs are removed from canonical form."""
        text = "This claim is true https://example.com/fake-news check it out"
        canonical = extract_canonical_claim(text)
        
        assert "https://" not in canonical
        assert "example.com" not in canonical
    
    def test_extract_canonical_claim_removes_forwards(self):
        """Test that forwarding prefixes are removed."""
        texts = [
            "Fwd: Important health news about vaccines",
            "FWD: Breaking news",
            "Forwarded: This is true",
            "*Forwarded Message* Doctors hate this",
        ]
        
        for text in texts:
            canonical = extract_canonical_claim(text)
            assert not canonical.lower().startswith("fwd")
            assert not canonical.lower().startswith("forward")
    
    def test_extract_canonical_claim_removes_cta(self):
        """Test that calls to action are removed."""
        text = "Vaccines cause harm! Share this with everyone you know!"
        canonical = extract_canonical_claim(text)
        
        assert "share this" not in canonical.lower()
    
    def test_detect_language_english(self):
        """Test English language detection."""
        assert detect_language("This is an English sentence") == "en"
    
    def test_detect_language_hindi(self):
        """Test Hindi language detection (Devanagari script)."""
        assert detect_language("यह हिंदी में है") == "hi"
    
    def test_detect_language_tamil(self):
        """Test Tamil language detection."""
        assert detect_language("இது தமிழில் உள்ளது") == "ta"
    
    def test_get_claim_topics_health(self):
        """Test topic extraction for health claims."""
        text = "This vaccine causes serious disease in children"
        topics = get_claim_topics(text)
        
        assert "health" in topics
    
    def test_get_claim_topics_politics(self):
        """Test topic extraction for political claims."""
        text = "The government is hiding the truth about elections"
        topics = get_claim_topics(text)
        
        assert "politics" in topics
    
    def test_get_claim_topics_multiple(self):
        """Test extraction of multiple topics."""
        text = "Government health minister announces new vaccine policy"
        topics = get_claim_topics(text)
        
        assert len(topics) >= 2


class TestEmbeddingService:
    """Tests for embedding service."""
    
    def test_embedding_service_initialization(self):
        """Test that embedding service can be initialized."""
        from app.services.embedding import EmbeddingService
        
        service = EmbeddingService(
            model_name="sentence-transformers/paraphrase-MiniLM-L6-v2",  # Smaller model for tests
            index_path="/tmp/test_faiss.index"
        )
        
        # Don't actually initialize (slow), just check creation
        assert service.model_name == "sentence-transformers/paraphrase-MiniLM-L6-v2"
        assert service._initialized is False
    
    def test_compute_similarity(self):
        """Test similarity computation."""
        from app.services.embedding import EmbeddingService
        
        service = EmbeddingService()
        
        # Create test embeddings
        emb1 = np.array([1.0, 0.0, 0.0])
        emb2 = np.array([1.0, 0.0, 0.0])
        emb3 = np.array([0.0, 1.0, 0.0])
        
        # Same vector = similarity 1.0
        sim_same = service.compute_similarity(emb1, emb2)
        assert abs(sim_same - 1.0) < 0.01
        
        # Orthogonal vectors = similarity 0.0
        sim_ortho = service.compute_similarity(emb1, emb3)
        assert abs(sim_ortho) < 0.01


class TestClusteringService:
    """Tests for clustering service."""
    
    def test_clustering_service_initialization(self):
        """Test clustering service can be initialized."""
        from app.services.clustering import ClusteringService
        
        service = ClusteringService(similarity_threshold=0.75)
        assert service.similarity_threshold == 0.75


class TestMemoryGraphService:
    """Tests for memory graph service."""
    
    def test_memory_graph_initialization(self):
        """Test memory graph can be initialized."""
        from app.services.memory_graph import MemoryGraphService
        
        service = MemoryGraphService(graph_path="/tmp/test_graph.json")
        service.initialize()
        
        assert service._initialized is True
        assert service._graph is not None
    
    def test_add_cluster_node(self):
        """Test adding nodes to graph."""
        from app.services.memory_graph import MemoryGraphService
        
        service = MemoryGraphService(graph_path="/tmp/test_graph2.json")
        service.initialize()
        
        service.add_cluster_node(1, {"topic": "health"})
        service.add_cluster_node(2, {"topic": "politics"})
        
        assert 1 in service._graph.nodes
        assert 2 in service._graph.nodes
    
    def test_add_relationship(self):
        """Test adding edges between nodes."""
        from app.services.memory_graph import MemoryGraphService
        
        service = MemoryGraphService(graph_path="/tmp/test_graph3.json")
        service.initialize()
        
        service.add_cluster_node(1)
        service.add_cluster_node(2)
        service.add_relationship(1, 2, "related_to", weight=0.8)
        
        assert service._graph.has_edge(1, 2)
    
    def test_record_spike(self):
        """Test recording activity spikes."""
        from app.services.memory_graph import MemoryGraphService
        from datetime import datetime
        
        service = MemoryGraphService(graph_path="/tmp/test_graph4.json")
        service.initialize()
        
        service.record_spike(1)
        service.record_spike(1)
        
        assert len(service._spike_history[1]) == 2
    
    def test_get_related_clusters(self):
        """Test getting related clusters."""
        from app.services.memory_graph import MemoryGraphService
        
        service = MemoryGraphService(graph_path="/tmp/test_graph5.json")
        service.initialize()
        
        # Create connected graph
        service.add_cluster_node(1)
        service.add_cluster_node(2)
        service.add_cluster_node(3)
        service.add_relationship(1, 2)
        service.add_relationship(2, 3)
        
        related = service.get_related_clusters(1, max_depth=2)
        
        # Should find both 2 and 3
        related_ids = [r[0] for r in related]
        assert 2 in related_ids
        assert 3 in related_ids


class TestVerificationService:
    """Tests for verification service."""
    
    def test_extract_domain(self):
        """Test domain extraction from URLs."""
        from app.services.verification import VerificationService
        
        service = VerificationService()
        
        assert service._extract_domain("https://www.example.com/page") == "example.com"
        assert service._extract_domain("https://who.int/news") == "who.int"
        assert service._extract_domain("http://sub.domain.org/path") == "sub.domain.org"
    
    def test_is_authoritative_domain(self):
        """Test authoritative domain checking."""
        from app.services.verification import VerificationService
        
        service = VerificationService()
        
        # Should be authoritative
        assert service._is_authoritative_domain("https://who.int/news")
        assert service._is_authoritative_domain("https://www.cdc.gov/page")
        assert service._is_authoritative_domain("https://factcheck.org/article")
        
        # Should not be authoritative
        assert not service._is_authoritative_domain("https://randomsite.com")
        assert not service._is_authoritative_domain("https://fake-news.biz")


class TestTTSService:
    """Tests for TTS service."""
    
    def test_clean_text_for_tts(self):
        """Test text cleaning for TTS."""
        from app.services.tts import TTSService
        
        service = TTSService()
        
        # Test URL removal
        text = "Check this https://example.com now"
        cleaned = service._clean_text_for_tts(text)
        assert "https://" not in cleaned
        
        # Test abbreviation expansion
        text = "e.g. this is important"
        cleaned = service._clean_text_for_tts(text)
        assert "for example" in cleaned
