"""
Clustering Service
Manages claim cluster assignment and merging using embeddings and FAISS.
"""

import logging
from typing import Optional, Tuple, List

import numpy as np
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import ClaimCluster, ClaimStatus
from app.crud import (
    create_cluster, get_cluster_by_id, update_cluster,
    create_or_update_cluster, record_claim_seen
)
from app.services.embedding import get_embedding_service
from app.services.detection import get_claim_topics

logger = logging.getLogger(__name__)

settings = get_settings()


class ClusteringService:
    """
    Service for managing claim clusters.
    
    Handles:
    - Assigning messages to existing clusters based on semantic similarity
    - Creating new clusters when no match is found
    - Tracking cluster statistics and sightings
    """
    
    def __init__(self, similarity_threshold: float = 0.75):
        """
        Initialize the clustering service.
        
        Args:
            similarity_threshold: Minimum similarity to merge into existing cluster
        """
        self.similarity_threshold = similarity_threshold
        self._embedding_service = None
    
    @property
    def embedding_service(self):
        """Lazy load embedding service."""
        if self._embedding_service is None:
            self._embedding_service = get_embedding_service()
        return self._embedding_service
    
    def assign_cluster(
        self,
        db: Session,
        canonical_text: str,
        embedding: np.ndarray,
        topic: Optional[str] = None,
        source: str = "web_form",
        platform_chat_id: Optional[str] = None,
        platform_user_id: Optional[str] = None
    ) -> Tuple[ClaimCluster, bool]:
        """
        Assign a claim to an existing cluster or create a new one.
        
        Algorithm:
        1. Search FAISS index for nearest cluster
        2. If similarity > threshold, merge into existing cluster
        3. Otherwise, create new cluster
        
        Args:
            db: Database session
            canonical_text: Normalized claim text
            embedding: Vector embedding of the claim
            topic: Optional topic category
            source: Source platform
            platform_chat_id: Chat ID for tracking
            platform_user_id: User ID for tracking (should be hashed)
        
        Returns:
            Tuple of (ClaimCluster, is_new_cluster)
        """
        # Initialize embedding service if needed
        if not self.embedding_service._initialized:
            self.embedding_service.initialize()
        
        # Search for existing cluster
        match = self.embedding_service.get_nearest_cluster(
            embedding, 
            threshold=self.similarity_threshold
        )
        
        if match:
            cluster_id, similarity = match
            logger.info(f"Found matching cluster {cluster_id} with similarity {similarity:.3f}")
            
            # Get existing cluster
            cluster = get_cluster_by_id(db, cluster_id)
            if cluster:
                # Update cluster with new message
                cluster = self._merge_into_cluster(db, cluster, embedding)
                
                # Record sighting
                record_claim_seen(
                    db, cluster_id, source, platform_chat_id, platform_user_id
                )
                
                return cluster, False
        
        # No match found - create new cluster
        logger.info("No matching cluster found, creating new cluster")
        
        # Determine topic if not provided
        if not topic:
            topics = get_claim_topics(canonical_text)
            topic = topics[0] if topics else "general"
        
        # Create cluster
        cluster = create_cluster(
            db=db,
            canonical_text=canonical_text,
            topic=topic,
            centroid_embedding=embedding.tolist(),
            status=ClaimStatus.UNKNOWN
        )
        
        # Add to FAISS index
        self.embedding_service.add_to_index(embedding, cluster.id)
        
        # Record initial sighting
        record_claim_seen(
            db, cluster.id, source, platform_chat_id, platform_user_id
        )
        
        return cluster, True
    
    def _merge_into_cluster(
        self,
        db: Session,
        cluster: ClaimCluster,
        new_embedding: np.ndarray
    ) -> ClaimCluster:
        """
        Merge a new message into an existing cluster.
        
        Updates:
        - Message count
        - Centroid embedding (running average)
        - Last seen timestamp
        
        Args:
            db: Database session
            cluster: Existing cluster to merge into
            new_embedding: Embedding of new message
        
        Returns:
            Updated cluster
        """
        # Calculate new centroid as weighted average
        old_count = cluster.message_count
        new_count = old_count + 1
        
        if cluster.centroid_embedding:
            old_centroid = np.array(cluster.centroid_embedding)
            new_centroid = (old_centroid * old_count + new_embedding) / new_count
        else:
            new_centroid = new_embedding
        
        # Update cluster
        cluster = update_cluster(
            db=db,
            cluster_id=cluster.id,
            increment_count=True,
            new_centroid=new_centroid.tolist()
        )
        
        return cluster
    
    def get_similar_clusters(
        self,
        db: Session,
        cluster_id: int,
        k: int = 5,
        threshold: float = 0.5
    ) -> List[Tuple[ClaimCluster, float]]:
        """
        Find clusters similar to a given cluster.
        
        Args:
            db: Database session
            cluster_id: ID of cluster to find similar to
            k: Number of similar clusters to return
            threshold: Minimum similarity
        
        Returns:
            List of (cluster, similarity) tuples
        """
        cluster = get_cluster_by_id(db, cluster_id)
        if not cluster or not cluster.centroid_embedding:
            return []
        
        embedding = np.array(cluster.centroid_embedding)
        
        # Search for neighbors (k+1 to exclude self)
        matches = self.embedding_service.search_nearest(
            embedding, k=k+1, threshold=threshold
        )
        
        results = []
        for matched_id, similarity in matches:
            if matched_id == cluster_id:
                continue  # Skip self
            
            matched_cluster = get_cluster_by_id(db, matched_id)
            if matched_cluster:
                results.append((matched_cluster, similarity))
        
        return results[:k]
    
    def merge_clusters(
        self,
        db: Session,
        primary_cluster_id: int,
        secondary_cluster_id: int
    ) -> Optional[ClaimCluster]:
        """
        Merge two clusters into one.
        
        The secondary cluster is merged into the primary cluster.
        Messages from secondary are reassigned to primary.
        
        Args:
            db: Database session
            primary_cluster_id: Cluster to keep
            secondary_cluster_id: Cluster to merge and delete
        
        Returns:
            Updated primary cluster or None if failed
        """
        primary = get_cluster_by_id(db, primary_cluster_id)
        secondary = get_cluster_by_id(db, secondary_cluster_id)
        
        if not primary or not secondary:
            logger.error("Cannot merge: cluster not found")
            return None
        
        # Update message count
        total_count = primary.message_count + secondary.message_count
        
        # Calculate combined centroid
        if primary.centroid_embedding and secondary.centroid_embedding:
            p_emb = np.array(primary.centroid_embedding)
            s_emb = np.array(secondary.centroid_embedding)
            new_centroid = (
                p_emb * primary.message_count + s_emb * secondary.message_count
            ) / total_count
        else:
            new_centroid = primary.centroid_embedding or secondary.centroid_embedding
        
        # Reassign messages from secondary to primary
        for message in secondary.messages:
            message.cluster_id = primary_cluster_id
        
        # Update primary cluster
        primary.message_count = total_count
        primary.centroid_embedding = new_centroid.tolist() if isinstance(new_centroid, np.ndarray) else new_centroid
        if secondary.last_seen_at > primary.last_seen_at:
            primary.last_seen_at = secondary.last_seen_at
        if secondary.first_seen_at < primary.first_seen_at:
            primary.first_seen_at = secondary.first_seen_at
        
        # Delete secondary cluster
        db.delete(secondary)
        db.commit()
        db.refresh(primary)
        
        logger.info(f"Merged cluster {secondary_cluster_id} into {primary_cluster_id}")
        
        return primary
    
    def recalculate_centroid(
        self,
        db: Session,
        cluster_id: int
    ) -> Optional[ClaimCluster]:
        """
        Recalculate a cluster's centroid from all its messages.
        
        Useful after manual edits or corrections.
        
        Args:
            db: Database session
            cluster_id: Cluster to recalculate
        
        Returns:
            Updated cluster or None if failed
        """
        cluster = get_cluster_by_id(db, cluster_id)
        if not cluster or not cluster.messages:
            return cluster
        
        # Collect all message embeddings
        embeddings = []
        for message in cluster.messages:
            if message.embedding_vector:
                embeddings.append(np.array(message.embedding_vector))
        
        if not embeddings:
            return cluster
        
        # Calculate mean centroid
        new_centroid = np.mean(embeddings, axis=0)
        
        cluster = update_cluster(
            db=db,
            cluster_id=cluster_id,
            new_centroid=new_centroid.tolist()
        )
        
        logger.info(f"Recalculated centroid for cluster {cluster_id}")
        
        return cluster


# Global singleton
_clustering_service: Optional[ClusteringService] = None


def get_clustering_service() -> ClusteringService:
    """Get the global clustering service instance."""
    global _clustering_service
    
    if _clustering_service is None:
        _clustering_service = ClusteringService(
            similarity_threshold=settings.similarity_threshold
        )
    
    return _clustering_service
