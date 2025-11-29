"""
Memory Graph Service
Maintains a graph of related claims and predicts claim re-emergence.
Uses NetworkX for graph operations with JSON persistence.
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from collections import defaultdict
import threading

import networkx as nx
from sqlalchemy.orm import Session

from app.config import get_settings
from app.crud import get_cluster_by_id, get_claim_seen_history, create_graph_edge
from app.models import ClaimCluster, ClaimSeen

logger = logging.getLogger(__name__)

settings = get_settings()

_graph_lock = threading.Lock()


class MemoryGraphService:
    """
    Service for managing claim relationship graph and predicting re-emergence.
    
    The graph tracks:
    - Nodes: Claim clusters
    - Edges: Relationships between clusters (co-occurrence, similarity, topic)
    
    Re-emergence prediction uses:
    - Historical spike patterns
    - Seasonal trends
    - Topic correlations
    """
    
    def __init__(self, graph_path: str = "/data/memory_graph.json"):
        """
        Initialize the memory graph service.
        
        Args:
            graph_path: Path to persist the graph as JSON
        """
        self.graph_path = graph_path
        self._graph: Optional[nx.Graph] = None
        self._spike_history: Dict[int, List[datetime]] = defaultdict(list)
        self._initialized = False
    
    def initialize(self) -> bool:
        """Initialize and load the graph."""
        if self._initialized:
            return True
        
        try:
            self._load_or_create_graph()
            self._initialized = True
            return True
        except Exception as e:
            logger.error(f"Failed to initialize memory graph: {e}")
            return False
    
    def _load_or_create_graph(self) -> None:
        """Load existing graph or create new one."""
        graph_file = Path(self.graph_path)
        
        if graph_file.exists():
            try:
                logger.info(f"Loading memory graph from {self.graph_path}")
                with open(graph_file, 'r') as f:
                    data = json.load(f)
                
                self._graph = nx.node_link_graph(data.get("graph", {"nodes": [], "links": []}))
                
                # Load spike history
                spike_data = data.get("spike_history", {})
                for cluster_id, timestamps in spike_data.items():
                    self._spike_history[int(cluster_id)] = [
                        datetime.fromisoformat(ts) for ts in timestamps
                    ]
                
                logger.info(f"Loaded graph with {self._graph.number_of_nodes()} nodes, {self._graph.number_of_edges()} edges")
                return
                
            except Exception as e:
                logger.warning(f"Failed to load existing graph: {e}")
        
        # Create new graph
        logger.info("Creating new memory graph")
        self._graph = nx.Graph()
        self._spike_history = defaultdict(list)
    
    def save(self) -> bool:
        """Save the graph to disk."""
        if self._graph is None:
            return False
        
        try:
            with _graph_lock:
                # Ensure directory exists
                graph_dir = Path(self.graph_path).parent
                graph_dir.mkdir(parents=True, exist_ok=True)
                
                # Convert graph to JSON-serializable format
                graph_data = nx.node_link_data(self._graph)
                
                # Convert spike history timestamps to ISO format
                spike_data = {}
                for cluster_id, timestamps in self._spike_history.items():
                    spike_data[str(cluster_id)] = [ts.isoformat() for ts in timestamps]
                
                data = {
                    "graph": graph_data,
                    "spike_history": spike_data,
                    "saved_at": datetime.utcnow().isoformat()
                }
                
                with open(self.graph_path, 'w') as f:
                    json.dump(data, f)
            
            logger.info(f"Saved memory graph with {self._graph.number_of_nodes()} nodes")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save memory graph: {e}")
            return False
    
    def add_cluster_node(self, cluster_id: int, attributes: Optional[Dict[str, Any]] = None) -> None:
        """Add a cluster as a node in the graph."""
        if not self._initialized:
            self.initialize()
        
        with _graph_lock:
            if cluster_id not in self._graph:
                self._graph.add_node(cluster_id, **(attributes or {}))
    
    def add_relationship(
        self,
        cluster_id_1: int,
        cluster_id_2: int,
        relationship_type: str = "related_to",
        weight: float = 1.0
    ) -> None:
        """
        Add or update a relationship between two clusters.
        
        Args:
            cluster_id_1: First cluster ID
            cluster_id_2: Second cluster ID  
            relationship_type: Type of relationship
            weight: Relationship strength
        """
        if not self._initialized:
            self.initialize()
        
        with _graph_lock:
            # Ensure both nodes exist
            if cluster_id_1 not in self._graph:
                self._graph.add_node(cluster_id_1)
            if cluster_id_2 not in self._graph:
                self._graph.add_node(cluster_id_2)
            
            # Add or update edge
            if self._graph.has_edge(cluster_id_1, cluster_id_2):
                # Increment weight
                self._graph[cluster_id_1][cluster_id_2]['weight'] += weight
            else:
                self._graph.add_edge(
                    cluster_id_1, cluster_id_2,
                    relationship_type=relationship_type,
                    weight=weight
                )
    
    def record_spike(self, cluster_id: int, timestamp: Optional[datetime] = None) -> None:
        """
        Record a spike in activity for a cluster.
        
        A spike is recorded when a cluster sees significant increase in messages.
        
        Args:
            cluster_id: Cluster that spiked
            timestamp: When the spike occurred (defaults to now)
        """
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        with _graph_lock:
            self._spike_history[cluster_id].append(timestamp)
            
            # Keep only last 100 spikes per cluster
            if len(self._spike_history[cluster_id]) > 100:
                self._spike_history[cluster_id] = self._spike_history[cluster_id][-100:]
    
    def get_related_clusters(
        self,
        cluster_id: int,
        max_depth: int = 2
    ) -> List[Tuple[int, float]]:
        """
        Get clusters related to a given cluster.
        
        Args:
            cluster_id: Source cluster
            max_depth: Maximum graph traversal depth
        
        Returns:
            List of (cluster_id, relevance_score) tuples
        """
        if not self._initialized:
            self.initialize()
        
        if cluster_id not in self._graph:
            return []
        
        related = []
        
        # Get neighbors within max_depth
        try:
            lengths = nx.single_source_shortest_path_length(
                self._graph, cluster_id, cutoff=max_depth
            )
            
            for node, distance in lengths.items():
                if node != cluster_id:
                    # Score inversely proportional to distance
                    score = 1.0 / (distance + 1)
                    related.append((node, score))
            
            # Sort by score descending
            related.sort(key=lambda x: x[1], reverse=True)
            
        except nx.NetworkXError:
            pass
        
        return related
    
    def predict_reemergence(
        self,
        current_context: Optional[List[int]] = None,
        top_k: int = 5
    ) -> List[Tuple[int, float, str]]:
        """
        Predict which clusters are likely to re-emerge.
        
        Uses:
        - Historical spike intervals
        - Current active clusters (context)
        - Graph connectivity
        
        Args:
            current_context: List of currently active cluster IDs
            top_k: Number of predictions to return
        
        Returns:
            List of (cluster_id, probability, reason) tuples
        """
        if not self._initialized:
            self.initialize()
        
        predictions = []
        now = datetime.utcnow()
        
        # Analyze each cluster's spike history
        for cluster_id, spikes in self._spike_history.items():
            if len(spikes) < 2:
                continue
            
            # Calculate average interval between spikes
            intervals = []
            for i in range(1, len(spikes)):
                interval = (spikes[i] - spikes[i-1]).total_seconds() / 86400  # days
                if interval > 0:
                    intervals.append(interval)
            
            if not intervals:
                continue
            
            avg_interval = sum(intervals) / len(intervals)
            
            # Time since last spike
            last_spike = max(spikes)
            days_since = (now - last_spike).total_seconds() / 86400
            
            # Probability increases as we approach the average interval
            if avg_interval > 0:
                cycle_position = days_since / avg_interval
                # Peak probability around 1.0 (at average interval)
                if cycle_position < 0.5:
                    prob = cycle_position * 0.5
                elif cycle_position < 1.5:
                    prob = 0.5 + (1 - abs(1 - cycle_position)) * 0.5
                else:
                    prob = max(0.2, 1.0 - (cycle_position - 1.5) * 0.2)
                
                reason = f"Historical pattern: avg {avg_interval:.0f} day cycle, {days_since:.0f} days since last"
                predictions.append((cluster_id, prob, reason))
        
        # Boost predictions for clusters related to current context
        if current_context:
            for context_cluster in current_context:
                related = self.get_related_clusters(context_cluster, max_depth=2)
                for related_id, score in related:
                    # Find and boost existing prediction
                    for i, (cid, prob, reason) in enumerate(predictions):
                        if cid == related_id:
                            boosted_prob = min(1.0, prob + score * 0.3)
                            predictions[i] = (cid, boosted_prob, reason + f" (related to active cluster {context_cluster})")
                            break
                    else:
                        # Add new prediction based on relationship
                        predictions.append((
                            related_id,
                            score * 0.4,
                            f"Related to currently active cluster {context_cluster}"
                        ))
        
        # Sort by probability and take top_k
        predictions.sort(key=lambda x: x[1], reverse=True)
        return predictions[:top_k]
    
    def detect_spike(
        self,
        db: Session,
        cluster_id: int,
        window_hours: int = 24,
        threshold_multiplier: float = 3.0
    ) -> bool:
        """
        Detect if a cluster is experiencing a spike.
        
        A spike is detected when recent activity exceeds the average
        by the threshold multiplier.
        
        Args:
            db: Database session
            cluster_id: Cluster to check
            window_hours: Hours to consider as "recent"
            threshold_multiplier: How many times above average triggers spike
        
        Returns:
            True if spike detected
        """
        # Get sighting history
        history = get_claim_seen_history(db, cluster_id, limit=500)
        
        if len(history) < 10:
            return False
        
        now = datetime.utcnow()
        window_start = now - timedelta(hours=window_hours)
        
        # Count sightings in window
        recent_count = sum(1 for h in history if h.seen_at >= window_start)
        
        # Calculate average rate (per window)
        oldest = min(h.seen_at for h in history)
        total_hours = max(1, (now - oldest).total_seconds() / 3600)
        windows = max(1, total_hours / window_hours)
        avg_per_window = len(history) / windows
        
        is_spike = recent_count > avg_per_window * threshold_multiplier
        
        if is_spike:
            self.record_spike(cluster_id, now)
        
        return is_spike
    
    def get_graph_stats(self) -> Dict[str, Any]:
        """Get statistics about the memory graph."""
        if not self._initialized:
            self.initialize()
        
        return {
            "nodes": self._graph.number_of_nodes(),
            "edges": self._graph.number_of_edges(),
            "density": nx.density(self._graph) if self._graph.number_of_nodes() > 1 else 0,
            "tracked_spikes": sum(len(spikes) for spikes in self._spike_history.values()),
            "clusters_with_spikes": len(self._spike_history)
        }


# Global singleton
_memory_graph_service: Optional[MemoryGraphService] = None


def get_memory_graph_service() -> MemoryGraphService:
    """Get the global memory graph service instance."""
    global _memory_graph_service
    
    if _memory_graph_service is None:
        _memory_graph_service = MemoryGraphService(graph_path=settings.memory_graph_path)
    
    return _memory_graph_service
