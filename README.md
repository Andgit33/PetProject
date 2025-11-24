# Road Trip Planner 🗺️

A RAG-based road trip planning tool that helps you discover destinations based on your preferences using semantic search and cosine similarity. The Streamlit UI includes improved geocoding + captions for maps, granular filters, and visual score breakdowns so you can explore each recommendation at a glance.

## Overview

This project uses Retrieval Augmented Generation (RAG) to match your travel preferences with destination information stored in a vector database. It processes destination data, creates embeddings using sentence transformers, and matches queries using cosine similarity across multiple aspects:

- **Activities**: What you can do at the destination
- **Scenery**: Natural features, views, and landscapes
- **Amenities**: Facilities, services, and accommodations
- **Location**: Geographic context and accessibility

**Includes 50 diverse destinations** from around the world, covering all continents and various travel types (cities, beaches, mountains, cultural sites, adventure destinations, and more).

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
pip install -r requirements.txt
```

2. **Build the index:**
   
   The project comes with 50 pre-loaded destinations. Build the index to create searchable vectors:
   
```bash
python -m src.cli build
```

   Or using Python:
```python
from src.build_index import DestinationIndex

index = DestinationIndex()
index.build_index()
```

   **Note:** The index only needs to be built once (or when you add/modify destinations).

## Usage

### Web UI (Recommended)

Launch the Streamlit interface:

```bash
streamlit run UI.py
```

The UI provides:
- **Interactive search interface** with natural language queries
- **Adjustable weight sliders** for different aspects (activities, scenery, amenities, location)
- **Visual score breakdowns** with interactive charts and gauges
- **Interactive maps** showing each destination's location
- **Filters** for country, budget level, and best season
- **Budget indicators** automatically inferred from amenities
- **Share & Download** functionality for results
- **Detailed destination information** with full metadata

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
- **Weighted scoring**: Configurable weights that actually impact results (searches all destinations, not just top-k)
- **Cosine similarity**: Uses normalized embeddings for semantic matching
- **FAISS indexing**: Fast similarity search using Facebook AI Similarity Search
- **Interactive maps**: Geocoded location maps for each destination
- **Smart filtering**: Filter by country, budget level, and best season
- **Budget inference**: Automatically determines budget level from amenities
- **Visual analytics**: Charts, gauges, and progress bars for score visualization
- **Share & export**: Share results or download as text file
- **50 diverse destinations**: Pre-loaded with destinations from around the world
- **Extensible**: Easy to add new destinations or modify search criteria

## Key Features Explained

### Weighted Search
The search system considers **all destinations** when applying weights, not just the top results. This means:
- High Activities weight → Destinations strong in activities rise to the top
- High Scenery weight → Scenic destinations get prioritized
- Weights have real impact on which destinations appear in results

### Budget Indicators
Automatically infers budget level from:
- **Luxury**: Luxury hotels, resorts, spas, overwater villas
- **Budget-Friendly**: Campgrounds, hostels, budget accommodations
- **Mid-Range**: Everything else

### Maps
Each destination includes an interactive map showing its location, geocoded from the location/state/country information.

### Filters
- **Country**: Filter by specific countries
- **Budget**: Filter by budget level (Budget-Friendly, Mid-Range, Luxury)
- **Season**: Filter by best season to visit

## Future Enhancements

- [x] Add budget considerations
- [x] Integration with mapping services
- [x] Seasonal recommendations (via filters)
- [ ] Add route planning between destinations
- [ ] Integrate weather data
- [ ] Multi-day trip planning
- [ ] User preference learning
- [ ] Photo galleries for destinations
- [ ] Travel time/distance calculator between destinations

## Deployment

- **Local Streamlit:** `streamlit run UI.py`
- **Streamlit Community Cloud:** point the app to `UI.py`, and let it install from `requirements.txt`. The file mirrors `env.yml`, keeping conda and pip installs in sync.
- **Custom hosting (Docker, Render, etc.):** install via `conda env create -f env.yml` or `pip install -r requirements.txt`, run `python -m src.cli build`, then launch the Streamlit UI or CLI.

## Requirements

- Python 3.10+
- Dependency lists live in `env.yml` (conda) and `requirements.txt` (pip/Streamlit)
- Internet connection for geocoding (maps feature)

## Troubleshooting

**Index not found error:**
```bash
python -m src.cli build
```

**Geocoding fails:**
- Maps require internet connection
- Some locations may not geocode correctly
- The app will continue without maps if geocoding fails

**Weights not working:**
- Make sure you've rebuilt the index after any code changes
- Weights now search all destinations, so they should have visible impact

## Contributing

Feel free to add more destinations by creating JSON files in `data/destinations/` following the format shown in the examples.

## License

MIT License

