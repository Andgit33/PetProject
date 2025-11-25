import json
from pathlib import Path
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Optional
import torch
import gc
import time
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from src.config import (
    DESTINATIONS_DIR,
    DERIVED_DIR,
    DEFAULT_EMBEDDING_MODEL,
    INDEX_PATH,
    DESTINATIONS_PATH
)

class DestinationIndex:
    def __init__(self, model_path: str = DEFAULT_EMBEDDING_MODEL):
        self.model_path = model_path
        self.model = None
        self.activities_index = None
        self.scenery_index = None
        self.amenities_index = None
        self.location_index = None
        self.destinations = []
        
    def _initialize_model(self):
        """Initialize the embedding model."""
        try:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            self.model = SentenceTransformer(
                self.model_path,
                device='cpu',
                cache_folder='./cache',
                use_auth_token=False
            )
            
            self.model.eval()
            
            for param in self.model.parameters():
                param.requires_grad = False
                
            return
        except Exception as e:
            raise RuntimeError(f"Failed to initialize model: {str(e)}")
    
    def _embed_text(self, text: str) -> np.ndarray:
        """Generate embedding for a text using the model."""
        if not self.model:
            self._initialize_model()
        
        try:
            with torch.no_grad():
                embeddings = self.model.encode(
                    [text],
                    convert_to_numpy=True,
                    device='cpu',
                    show_progress_bar=False,
                    batch_size=1
                )
            
            # Normalize embeddings for cosine similarity
            embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
            
            return embeddings[0]
        except Exception as e:
            raise RuntimeError(f"Failed to generate embeddings: {str(e)}")
        finally:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            gc.collect()
    
    def _geocode_destination(self, destination: Dict) -> tuple[Optional[float], Optional[float]]:
        """Geocode a destination and return lat/lon. Returns (None, None) if geocoding fails."""
        # Skip if already has coordinates
        if 'latitude' in destination and 'longitude' in destination:
            return destination['latitude'], destination['longitude']
        
        try:
            geolocator = Nominatim(user_agent="road_trip_planner_index_build/1.0")
            
            name = destination.get('name')
            location = destination.get('location')
            state = destination.get('state')
            country = destination.get('country', '')
            
            # Build prioritized search combinations
            search_candidates = []
            candidate_parts = [
                [name, location, state, country],
                [name, state, country],
                [name, country],
                [name],
                [location, state, country],
                [location, country],
                [location],
                [state, country],
                [country]
            ]
            
            for parts in candidate_parts:
                parts = [part for part in parts if part]
                if not parts:
                    continue
                search_string = ", ".join(str(part) for part in parts)
                if search_string and search_string not in search_candidates:
                    search_candidates.append(search_string)
            
            # Try candidates with rate limiting (1 request per second for Nominatim free tier)
            for search_string in search_candidates:
                try:
                    time.sleep(1.1)  # Respect Nominatim rate limits
                    location_obj = geolocator.geocode(search_string, timeout=15)
                    if location_obj:
                        return location_obj.latitude, location_obj.longitude
                except (GeocoderTimedOut, GeocoderServiceError):
                    continue
                except Exception:
                    continue
            
            return None, None
        except Exception:
            return None, None
    
    def _embed_destination(self, destination: Dict) -> Dict[str, np.ndarray]:
        """Generate multiple embeddings for different aspects of a destination."""
        # Helper function to safely get string values (handle None from JSON null)
        def safe_str(value, default=""):
            return str(value) if value is not None else default
        
        # Helper function to safely get list values and filter None
        def safe_list(value, default=None):
            if value is None:
                return default or []
            return [str(item) for item in value if item is not None]
        
        # Activities embedding - what you can do there
        activities_list = safe_list(destination.get("activities")) + safe_list(destination.get("nearby_attractions"))
        activities_text = " ".join([safe_str(destination.get("description"))] + activities_list)
        activities_embedding = self._embed_text(activities_text)
        
        # Scenery embedding - natural features, views, landscapes
        scenery_list = safe_list(destination.get("scenery"))
        scenery_text = " ".join(scenery_list + [safe_str(destination.get("description"))])
        scenery_embedding = self._embed_text(scenery_text)
        
        # Amenities embedding - facilities, services, accommodations
        amenities_list = safe_list(destination.get("amenities"))
        amenities_text = " ".join(amenities_list + [safe_str(destination.get("description"))])
        amenities_embedding = self._embed_text(amenities_text)
        
        # Location embedding - geographic context, region, accessibility
        location_parts = [
            safe_str(destination.get("location")),
            safe_str(destination.get("state")),
            safe_str(destination.get("country")),
            *safe_list(destination.get("keywords"))
        ]
        location_text = " ".join([part for part in location_parts if part])  # Filter empty strings
        location_embedding = self._embed_text(location_text)
        
        return {
            "activities": activities_embedding,
            "scenery": scenery_embedding,
            "amenities": amenities_embedding,
            "location": location_embedding
        }
    
    def build_index(self):
        """Build the FAISS index from destination files."""
        # Load all destination files
        destination_files = list(DESTINATIONS_DIR.glob("*.json"))
        if not destination_files:
            raise ValueError(f"No destination files found in {DESTINATIONS_DIR}!")
        
        print(f"Found {len(destination_files)} destination files")
        
        # Initialize model
        self._initialize_model()
        print("Model initialized")
        
        # Process destinations and build indices
        activities_embeddings = []
        scenery_embeddings = []
        amenities_embeddings = []
        location_embeddings = []
        
        # Track which destinations need geocoding (for batch processing with rate limiting)
        destinations_to_geocode = []
        
        for dest_file in destination_files:
            try:
                # Load destination
                destination = json.loads(dest_file.read_text())
                
                # Store filename for reference
                destination["filename"] = dest_file.name
                
                # Check if geocoding is needed (we'll do it in batch after loading all)
                if 'latitude' not in destination or 'longitude' not in destination:
                    destinations_to_geocode.append((dest_file, destination))
                
                self.destinations.append(destination)
                
                # Generate embeddings
                embeddings = self._embed_destination(destination)
                
                # Add to lists
                activities_embeddings.append(embeddings["activities"])
                scenery_embeddings.append(embeddings["scenery"])
                amenities_embeddings.append(embeddings["amenities"])
                location_embeddings.append(embeddings["location"])
                
                print(f"Processed: {destination.get('name', dest_file.stem)}")
                
            except Exception as e:
                print(f"Warning: Skipping destination {dest_file.name} due to error: {str(e)}")
                continue
        
        # Geocode destinations that need coordinates (for map display)
        if destinations_to_geocode:
            print(f"\n🌍 Geocoding {len(destinations_to_geocode)} destinations for map display...")
            print("(This may take a while due to rate limiting - maps will work after this completes)")
            for dest_file, destination in destinations_to_geocode:
                lat, lon = self._geocode_destination(destination)
                if lat and lon:
                    destination['latitude'] = lat
                    destination['longitude'] = lon
                    # Save updated destination back to file
                    with open(dest_file, 'w') as f:
                        json.dump(destination, f, indent=2)
                    # Update the destination in self.destinations (find it by filename)
                    for dest in self.destinations:
                        if dest.get('filename') == dest_file.name:
                            dest['latitude'] = lat
                            dest['longitude'] = lon
                            break
                    print(f"  ✓ Geocoded: {destination.get('name', dest_file.stem)}")
                else:
                    print(f"  ✗ Could not geocode: {destination.get('name', dest_file.stem)}")
            print("Geocoding complete.\n")
        
        try:
            # Convert to numpy arrays
            activities_embeddings = np.array(activities_embeddings).astype('float32')
            scenery_embeddings = np.array(scenery_embeddings).astype('float32')
            amenities_embeddings = np.array(amenities_embeddings).astype('float32')
            location_embeddings = np.array(location_embeddings).astype('float32')
            
            # Build FAISS indices (using Inner Product for normalized vectors = cosine similarity)
            dim = activities_embeddings.shape[1]
            self.activities_index = faiss.IndexFlatIP(dim)
            self.scenery_index = faiss.IndexFlatIP(dim)
            self.amenities_index = faiss.IndexFlatIP(dim)
            self.location_index = faiss.IndexFlatIP(dim)
            
            # Add vectors to indices
            self.activities_index.add(activities_embeddings)
            self.scenery_index.add(scenery_embeddings)
            self.amenities_index.add(amenities_embeddings)
            self.location_index.add(location_embeddings)
            
            print(f"Built indices with {len(self.destinations)} destinations")
            
            # Save indices and destinations
            self.save_index()
            print("Index saved successfully")
            
        except Exception as e:
            raise RuntimeError(f"Failed to build index: {str(e)}")
    
    def save_index(self):
        """Save the index and destinations to disk."""
        # Create directory if it doesn't exist
        INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        # Save destinations
        with open(DESTINATIONS_PATH, 'w') as f:
            json.dump(self.destinations, f, indent=2)
        
        # Save indices
        faiss.write_index(self.activities_index, str(INDEX_PATH.with_suffix('.activities.idx')))
        faiss.write_index(self.scenery_index, str(INDEX_PATH.with_suffix('.scenery.idx')))
        faiss.write_index(self.amenities_index, str(INDEX_PATH.with_suffix('.amenities.idx')))
        faiss.write_index(self.location_index, str(INDEX_PATH.with_suffix('.location.idx')))
    
    def load_index(self):
        """Load the index and destinations from disk. Auto-builds if index doesn't exist."""
        if not INDEX_PATH.with_suffix('.activities.idx').exists():
            # Auto-build index if it doesn't exist (useful for Streamlit Cloud deployments)
            print("Index files not found. Building index automatically...")
            self.build_index()
            return
        
        # Load destinations
        with open(DESTINATIONS_PATH, 'r') as f:
            self.destinations = json.load(f)
        
        # Merge coordinates from original JSON files (always sync from source of truth)
        # This ensures coordinates are always up-to-date even if index was built before coordinates were added
        for dest in self.destinations:
            filename = dest.get('filename')
            if filename:
                # Try to load coordinates from original JSON file
                dest_file = DESTINATIONS_DIR / filename
                if dest_file.exists():
                    try:
                        original_data = json.loads(dest_file.read_text())
                        if 'latitude' in original_data and 'longitude' in original_data:
                            dest['latitude'] = original_data['latitude']
                            dest['longitude'] = original_data['longitude']
                    except Exception:
                        pass  # If we can't read the file, just continue
        
        # Load indices
        self.activities_index = faiss.read_index(str(INDEX_PATH.with_suffix('.activities.idx')))
        self.scenery_index = faiss.read_index(str(INDEX_PATH.with_suffix('.scenery.idx')))
        self.amenities_index = faiss.read_index(str(INDEX_PATH.with_suffix('.amenities.idx')))
        self.location_index = faiss.read_index(str(INDEX_PATH.with_suffix('.location.idx')))
        
        print(f"Loaded index with {len(self.destinations)} destinations")

