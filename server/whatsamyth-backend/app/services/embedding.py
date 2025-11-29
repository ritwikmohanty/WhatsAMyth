"""
Embedding Service
Handles text embeddings using sentence-transformers and FAISS index management.
"""

import os
import logging
from typing import Optional, List, Tuple
from pathlib import Path
import threading

import numpy as np

logger = logging.getLogger(__name__)

# Thread lock for FAISS operations
_faiss_lock = threading.Lock()


class EmbeddingService:
    """
    Service for generating text embeddings and managing FAISS similarity index.
    
    Uses sentence-transformers for embedding generation and FAISS for
    efficient nearest neighbor search.
    """
    
    def __init__(
        self,
        model_name: str = "sentence-transformers/paraphrase-mpnet-base-v2",
        index_path: str = "/data/faiss.index",
        embedding_dim: int = 768
    ):
        """
        Initialize the embedding service.
        
        Args:
            model_name: HuggingFace model name for sentence-transformers
            index_path: Path to persist the FAISS index
            embedding_dim: Dimension of embeddings (768 for mpnet)
        """
        self.model_name = model_name
        self.index_path = index_path
        self.embedding_dim = embedding_dim
        
        self._model = None
        self._index = None
        self._id_map: List[int] = []  # Maps FAISS internal IDs to cluster IDs
        
        self._initialized = False
    
    def initialize(self) -> bool:
        """
        Initialize the model and load/create the FAISS index.
        
        Returns:
            True if initialization successful
        """
        if self._initialized:
            return True
        
        try:
            # Load sentence transformer model
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading embedding model: {self.model_name}")
            self._model = SentenceTransformer(self.model_name)
            logger.info("Embedding model loaded successfully")
            
            # Load or create FAISS index
            self._load_or_create_index()
            
            self._initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize embedding service: {e}")
            return False
    
    def _load_or_create_index(self) -> None:
        """Load existing FAISS index or create a new one."""
        import faiss
        
        index_file = Path(self.index_path)
        id_map_file = Path(self.index_path + ".idmap.npy")
        
        if index_file.exists():
            try:
                logger.info(f"Loading existing FAISS index from {self.index_path}")
                self._index = faiss.read_index(str(index_file))
                
                if id_map_file.exists():
                    self._id_map = np.load(str(id_map_file)).tolist()
                else:
                    # Reconstruct ID map (assume sequential)
                    self._id_map = list(range(self._index.ntotal))
                
                logger.info(f"Loaded FAISS index with {self._index.ntotal} vectors")
                return
            except Exception as e:
                logger.warning(f"Failed to load existing index: {e}")
        
        # Create new index
        logger.info("Creating new FAISS index")
        # Use IndexFlatIP for inner product (cosine similarity with normalized vectors)
        self._index = faiss.IndexFlatIP(self.embedding_dim)
        self._id_map = []
        logger.info("Created new empty FAISS index")
    
    def save_index(self) -> bool:
        """
        Save the FAISS index to disk.
        
        Returns:
            True if save successful
        """
        if self._index is None:
            return False
        
        try:
            import faiss
            
            with _faiss_lock:
                # Ensure directory exists
                index_dir = Path(self.index_path).parent
                index_dir.mkdir(parents=True, exist_ok=True)
                
                # Save index
                faiss.write_index(self._index, str(self.index_path))
                
                # Save ID map
                np.save(self.index_path + ".idmap.npy", np.array(self._id_map))
            
            logger.info(f"Saved FAISS index with {self._index.ntotal} vectors")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save FAISS index: {e}")
            return False
    
    def embed_text(self, text: str) -> Optional[np.ndarray]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Input text to embed
        
        Returns:
            Numpy array of shape (embedding_dim,) or None on failure
        """
        if not self._initialized:
            if not self.initialize():
                return None
        
        if not text or not isinstance(text, str):
            return None
        
        try:
            # Truncate very long texts
            if len(text) > 5000:
                text = text[:5000]
            
            embedding = self._model.encode([text], convert_to_numpy=True, normalize_embeddings=True)[0]
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None
    
    def embed_texts(self, texts: List[str]) -> Optional[np.ndarray]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of input texts
        
        Returns:
            Numpy array of shape (n_texts, embedding_dim) or None on failure
        """
        if not self._initialized:
            if not self.initialize():
                return None
        
        if not texts:
            return None
        
        try:
            # Truncate long texts
            truncated = [t[:5000] if len(t) > 5000 else t for t in texts]
            embeddings = self._model.encode(truncated, convert_to_numpy=True, normalize_embeddings=True)
            return embeddings
            
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            return None
    
    def add_to_index(self, embedding: np.ndarray, cluster_id: int) -> bool:
        """
        Add an embedding to the FAISS index.
        
        Args:
            embedding: The embedding vector to add
            cluster_id: The cluster ID this embedding represents
        
        Returns:
            True if successfully added
        """
        if self._index is None:
            if not self.initialize():
                return False
        
        try:
            with _faiss_lock:
                # Ensure embedding is 2D
                if embedding.ndim == 1:
                    embedding = embedding.reshape(1, -1)
                
                # Add to index
                self._index.add(embedding.astype(np.float32))
                self._id_map.append(cluster_id)
            
            logger.debug(f"Added embedding for cluster {cluster_id} to index")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add embedding to index: {e}")
            return False
    
    def search_nearest(
        self,
        embedding: np.ndarray,
        k: int = 5,
        threshold: float = 0.75
    ) -> List[Tuple[int, float]]:
        """
        Search for nearest neighbors in the index.
        
        Args:
            embedding: Query embedding
            k: Number of neighbors to return
            threshold: Minimum similarity threshold
        
        Returns:
            List of (cluster_id, similarity_score) tuples
        """
        if self._index is None or self._index.ntotal == 0:
            return []
        
        try:
            with _faiss_lock:
                # Ensure embedding is 2D
                if embedding.ndim == 1:
                    embedding = embedding.reshape(1, -1)
                
                # Search
                k = min(k, self._index.ntotal)
                distances, indices = self._index.search(embedding.astype(np.float32), k)
            
            results = []
            for dist, idx in zip(distances[0], indices[0]):
                if idx < 0 or idx >= len(self._id_map):
                    continue
                
                similarity = float(dist)  # Inner product with normalized vectors = cosine similarity
                if similarity >= threshold:
                    cluster_id = self._id_map[idx]
                    results.append((cluster_id, similarity))
            
            return results
            
        except Exception as e:
            logger.error(f"FAISS search failed: {e}")
            return []
    
    def get_nearest_cluster(
        self,
        embedding: np.ndarray,
        threshold: float = 0.75
    ) -> Optional[Tuple[int, float]]:
        """
        Get the nearest cluster ID for an embedding.
        
        Args:
            embedding: Query embedding
            threshold: Minimum similarity to consider a match
        
        Returns:
            Tuple of (cluster_id, similarity) or None if no match above threshold
        """
        results = self.search_nearest(embedding, k=1, threshold=threshold)
        if results:
            return results[0]
        return None
    
    def update_cluster_embedding(
        self,
        cluster_id: int,
        new_embedding: np.ndarray
    ) -> bool:
        """
        Update the embedding for a cluster (used when cluster centroid changes).
        
        Note: FAISS doesn't support in-place updates, so we add and mark old as stale.
        For simplicity in this implementation, we just add the new embedding.
        A production system would periodically rebuild the index.
        
        Args:
            cluster_id: Cluster to update
            new_embedding: New centroid embedding
        
        Returns:
            True if successful
        """
        # For simplicity, just add the new embedding
        # A production system would track versions or rebuild periodically
        return self.add_to_index(new_embedding, cluster_id)
    
    @property
    def index_size(self) -> int:
        """Get number of vectors in the index."""
        if self._index is None:
            return 0
        return self._index.ntotal
    
    def compute_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """
        Compute cosine similarity between two embeddings.
        
        Args:
            emb1: First embedding
            emb2: Second embedding
        
        Returns:
            Cosine similarity score between -1 and 1
        """
        # Normalize
        emb1_norm = emb1 / (np.linalg.norm(emb1) + 1e-9)
        emb2_norm = emb2 / (np.linalg.norm(emb2) + 1e-9)
        
        return float(np.dot(emb1_norm, emb2_norm))


# Global singleton instance
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """Get the global embedding service instance."""
    global _embedding_service
    
    if _embedding_service is None:
        from app.config import get_settings
        settings = get_settings()
        
        _embedding_service = EmbeddingService(
            model_name=settings.embedding_model,
            index_path=settings.faiss_index_path
        )
    
    return _embedding_service


def make_or_load_faiss_index(path: str) -> EmbeddingService:
    """
    Create or load a FAISS index at the given path.
    
    Args:
        path: Path to the index file
    
    Returns:
        Initialized EmbeddingService instance
    """
    from app.config import get_settings
    settings = get_settings()
    
    service = EmbeddingService(
        model_name=settings.embedding_model,
        index_path=path
    )
    service.initialize()
    
    return service
