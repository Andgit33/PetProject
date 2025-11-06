# Road Trip Planner 🗺️

A RAG-based road trip planning tool that helps you discover destinations based on your preferences using semantic search and cosine similarity.

## Overview

This project uses Retrieval Augmented Generation (RAG) to match your travel preferences with destination information stored in a vector database. It processes destination data, creates embeddings using sentence transformers, and matches queries using cosine similarity across multiple aspects:

- **Activities**: What you can do at the destination
- **Scenery**: Natural features, views, and landscapes
- **Amenities**: Facilities, services, and accommodations
- **Location**: Geographic context and accessibility

## Project Structure

```
road_trip_planner/
├── src/
│   ├── __init__.py
│   ├── config.py          # Configuration and paths
│   ├── build_index.py     # Build vector index from destinations
│   ├── query.py           # Query destinations
│   └── cli.py             # Command-line interface
├── data/
│   ├── destinations/       # JSON files with destination data
│   └── derived/
│       └── index/        # Generated FAISS indices
├── notebooks/            # Jupyter notebooks for exploration
├── tests/                # Unit tests
├── UI.py                 # Streamlit web interface
├── build_index.py        # Standalone build script
├── query_example.py      # Example query script
└── README.md
```

## Setup

1. **Install dependencies:**

Using conda (recommended):
```bash
conda env create -f env.yml
conda activate road-trip-planner
```

Or using pip:
```bash
pip install sentence-transformers faiss-cpu numpy torch streamlit plotly rich typer pydantic
```

2. **Add destination data:**
   - Place JSON files in `data/destinations/`
   - Each file should contain destination information (see example below)

3. **Build the index:**
```python
from src.build_index import DestinationIndex

index = DestinationIndex()
index.build_index()
```

## Usage

### Web UI (Recommended)

Launch the Streamlit interface:

```bash
streamlit run UI.py
```

The UI provides:
- Interactive search interface
- Adjustable weight sliders for different aspects
- Visual score breakdowns with charts
- Detailed destination information

### Command Line Interface

```bash
# Build index
python -m src.cli build

# Search destinations
python -m src.cli search "I want to go hiking in the mountains"

# Interactive mode
python -m src.cli interactive
```

### Python API

```python
from src.query import TripPlanner

planner = TripPlanner()
results = planner.search_destinations(
    "I want to go hiking in the mountains with scenic views",
    top_k=5
)

for result in results:
    print(f"{result['destination']} - Score: {result['score']:.3f}")
    print(result['explanation'])
    print()
```

### Example Queries

- "I'm looking for beach destinations with water sports"
- "Mountain hiking trails with camping facilities"
- "Historic towns with good restaurants"
- "National parks with wildlife viewing"

## Destination Data Format

Each destination should be a JSON file with the following structure:

```json
{
  "name": "Yosemite National Park",
  "location": "California",
  "state": "CA",
  "country": "USA",
  "description": "Iconic national park known for granite cliffs, waterfalls, and giant sequoias.",
  "activities": [
    "hiking",
    "rock climbing",
    "camping",
    "photography",
    "wildlife viewing"
  ],
  "scenery": [
    "mountains",
    "waterfalls",
    "valleys",
    "giant sequoias",
    "granite cliffs"
  ],
  "amenities": [
    "campgrounds",
    "visitor centers",
    "lodging",
    "restaurants",
    "shuttle service"
  ],
  "best_season": ["spring", "summer", "fall"],
  "travel_time": "4-5 hours from San Francisco",
  "nearby_attractions": [
    "Half Dome",
    "El Capitan",
    "Yosemite Falls"
  ],
  "keywords": [
    "national park",
    "outdoor adventure",
    "nature",
    "hiking"
  ]
}
```

## Features

- **Multi-aspect matching**: Searches across activities, scenery, amenities, and location
- **Weighted scoring**: Configurable weights for different aspects
- **Cosine similarity**: Uses normalized embeddings for semantic matching
- **FAISS indexing**: Fast similarity search using Facebook AI Similarity Search
- **Extensible**: Easy to add new destinations or modify search criteria

## Future Enhancements

- [ ] Add route planning between destinations
- [ ] Integrate weather data
- [ ] Add budget considerations
- [ ] Multi-day trip planning
- [ ] Integration with mapping services
- [ ] User preference learning
- [ ] Seasonal recommendations

## License

MIT License

