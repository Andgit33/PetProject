from pathlib import Path
from typing import Optional, Dict, List
from pydantic import BaseModel, Field
import os

# Base directories
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DERIVED_DIR = DATA_DIR / "derived"
MODELS_DIR = BASE_DIR / "models"

# Input directories
DESTINATIONS_DIR = DATA_DIR / "destinations"

# Output directories
INDEX_PATH = DERIVED_DIR / "index" / "index"
DESTINATIONS_PATH = DERIVED_DIR / "index" / "destinations.json"

# Model paths
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/paraphrase-MiniLM-L3-v2"

# Environment variables to prevent threading issues
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

# Matching weights for different aspects
MATCH_WEIGHTS = {
    "activities": 0.4,
    "scenery": 0.3,
    "amenities": 0.2,
    "location": 0.1
}

# Create necessary directories
for dir_path in [DERIVED_DIR, INDEX_PATH.parent, MODELS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# Pydantic models for type safety
class Destination(BaseModel):
    name: str
    location: str
    state: Optional[str] = None
    country: str = "USA"
    description: str
    activities: List[str]
    scenery: List[str]
    amenities: List[str]
    best_season: List[str]
    travel_time: Optional[str] = None
    nearby_attractions: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)

class MatchResult(BaseModel):
    destination: str
    score: float
    explanation: str
    matching_aspects: List[str]

