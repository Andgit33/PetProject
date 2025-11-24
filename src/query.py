from pathlib import Path
from typing import List, Dict
import numpy as np
from sentence_transformers import SentenceTransformer
import torch
import gc
from src.config import (
    DEFAULT_EMBEDDING_MODEL,
    MATCH_WEIGHTS
)
from src.build_index import DestinationIndex

class TripPlanner:
    def __init__(self, model_name: str = DEFAULT_EMBEDDING_MODEL):
        # Initialize index
        self.index = DestinationIndex(model_name)
        
        # Load index (will auto-build if it doesn't exist)
        self.index.load_index()
        
        # Ensure model is initialized
        if not self.index.model:
            self.index._initialize_model()
        
        # Reuse the model from the index
        self.model = self.index.model
        
        # Use weights from config
        self.weights = MATCH_WEIGHTS
    
    def _embed_text(self, text: str) -> np.ndarray:
        """Create an embedding for text."""
        try:
            with torch.no_grad():
                embeddings = self.model.encode(
                    [text],
                    convert_to_numpy=True,
                    device='cpu',
                    show_progress_bar=False,
                    batch_size=1
                )
            
            # Normalize embeddings
            embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
            
            return embeddings[0].astype(np.float32)
        except Exception as e:
            raise RuntimeError(f"Failed to embed text: {str(e)}")
        finally:
            gc.collect()
    
    def _parse_query(self, query_text: str) -> Dict[str, str]:
        """Parse query text into different aspects."""
        # For now, use the same text for all aspects
        # Could be enhanced with NLP to extract specific aspects
        return {
            "activities": query_text,
            "scenery": query_text,
            "amenities": query_text,
            "location": query_text
        }
    
    def _generate_explanation(self, query_text: str, destination: Dict) -> tuple[str, List[str]]:
        """Generate explanation highlighting aspects relevant to the query."""
        explanation_parts = []
        matching_aspects = []
        
        query_lower = query_text.lower()
        
        # Check for activity matches
        activities = destination.get("activities", [])
        for activity in activities:
            if any(term in activity.lower() for term in query_lower.split()):
                matching_aspects.append(f"Activity: {activity}")
        
        # Check for scenery matches
        scenery = destination.get("scenery", [])
        for scene in scenery:
            if any(term in scene.lower() for term in query_lower.split()):
                matching_aspects.append(f"Scenery: {scene}")
        
        # Check for amenity matches
        amenities = destination.get("amenities", [])
        for amenity in amenities:
            if any(term in amenity.lower() for term in query_lower.split()):
                matching_aspects.append(f"Amenity: {amenity}")
        
        # Build explanation
        explanation_parts.append(f"**{destination.get('name', 'Unknown')}**")
        explanation_parts.append(f"Location: {destination.get('location', 'N/A')}")
        
        if destination.get("description"):
            explanation_parts.append(f"\n{destination.get('description')}")
        
        if activities:
            explanation_parts.append(f"\n**Activities:** {', '.join(activities[:5])}")
        
        if scenery:
            explanation_parts.append(f"**Scenery:** {', '.join(scenery[:5])}")
        
        if destination.get("best_season"):
            explanation_parts.append(f"**Best Season:** {', '.join(destination.get('best_season', []))}")
        
        explanation = "\n".join(explanation_parts)
        
        return explanation, matching_aspects
    
    def search_destinations(self, query_text: str, top_k: int = 5) -> List[Dict]:
        """
        Search for destinations matching the query.
        
        Args:
            query_text: User's query (e.g., "I want to go hiking in the mountains")
            top_k: Number of top results to return
            
        Returns:
            List of destination matches with scores
        """
        # Parse query into aspects
        query_aspects = self._parse_query(query_text)
        
        # Generate embeddings for each aspect
        query_embeddings = {
            "activities": self._embed_text(query_aspects["activities"]),
            "scenery": self._embed_text(query_aspects["scenery"]),
            "amenities": self._embed_text(query_aspects["amenities"]),
            "location": self._embed_text(query_aspects["location"])
        }
        
        # Get total number of destinations
        num_destinations = len(self.index.destinations)
        
        # Search ALL destinations from each index (not just top_k)
        # This allows weights to have real impact by considering all candidates
        # Weights will determine which destinations rise to the top based on their strengths
        search_k = num_destinations  # Search all destinations
        
        activities_scores, activities_indices = self.index.activities_index.search(
            query_embeddings["activities"].reshape(1, -1), search_k
        )
        scenery_scores, scenery_indices = self.index.scenery_index.search(
            query_embeddings["scenery"].reshape(1, -1), search_k
        )
        amenities_scores, amenities_indices = self.index.amenities_index.search(
            query_embeddings["amenities"].reshape(1, -1), search_k
        )
        location_scores, location_indices = self.index.location_index.search(
            query_embeddings["location"].reshape(1, -1), search_k
        )
        
        # Create score dictionaries for all candidates from each dimension
        # This allows us to look up scores for any destination
        activities_score_map = {int(activities_indices[0][i]): float(activities_scores[0][i]) 
                               for i in range(search_k)}
        scenery_score_map = {int(scenery_indices[0][i]): float(scenery_scores[0][i]) 
                            for i in range(search_k)}
        amenities_score_map = {int(amenities_indices[0][i]): float(amenities_scores[0][i]) 
                              for i in range(search_k)}
        location_score_map = {int(location_indices[0][i]): float(location_scores[0][i]) 
                             for i in range(search_k)}
        
        # Collect all unique destination indices from all searches
        all_dest_indices = set(activities_score_map.keys()) | set(scenery_score_map.keys()) | \
                          set(amenities_score_map.keys()) | set(location_score_map.keys())
        
        # Combine scores with weights for ALL candidates
        # This is where weights have real impact - they determine which destinations rise to top
        combined_scores = {}
        for dest_idx in all_dest_indices:
            # Get scores from each dimension (default to 0 if not in top results)
            act_score = activities_score_map.get(dest_idx, 0.0)
            scen_score = scenery_score_map.get(dest_idx, 0.0)
            amen_score = amenities_score_map.get(dest_idx, 0.0)
            loc_score = location_score_map.get(dest_idx, 0.0)
            
            # Apply weights - this is where the magic happens!
            # Higher weights mean that dimension has more influence on final ranking
            weighted_score = (
                self.weights["activities"] * act_score +
                self.weights["scenery"] * scen_score +
                self.weights["amenities"] * amen_score +
                self.weights["location"] * loc_score
            )
            
            combined_scores[dest_idx] = {
                "score": weighted_score,
                "activities_score": act_score,
                "scenery_score": scen_score,
                "amenities_score": amen_score,
                "location_score": loc_score
            }
        
        # Sort by weighted combined score
        sorted_indices = sorted(combined_scores.items(), key=lambda x: x[1]["score"], reverse=True)
        
        # Take only top_k results
        sorted_indices = sorted_indices[:top_k]
        
        # Prepare results
        results = []
        for dest_idx, scores in sorted_indices:
            destination = self.index.destinations[dest_idx]
            
            explanation, matching_aspects = self._generate_explanation(query_text, destination)
            
            results.append({
                "destination": destination.get("name", "Unknown"),
                "location": destination.get("location", "N/A"),
                "score": scores["score"],
                "activities_score": scores["activities_score"],
                "scenery_score": scores["scenery_score"],
                "amenities_score": scores["amenities_score"],
                "location_score": scores["location_score"],
                "explanation": explanation,
                "matching_aspects": matching_aspects,
                "full_data": destination
            })
        
        return results

