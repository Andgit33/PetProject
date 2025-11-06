# Quick Start Guide

## 1. Setup Environment

```bash
# Using conda (recommended)
conda env create -f env.yml
conda activate road-trip-planner

# Or using pip
pip install sentence-transformers faiss-cpu numpy torch rich typer pydantic
```

## 2. Add Destination Data

Place JSON files in `data/destinations/`. See the example files for the format:
- `example_yosemite.json`
- `example_grand_canyon.json`
- `example_santa_monica.json`

You can add your own destination files following the same structure.

## 3. Build the Index

```bash
# Using the CLI
python -m src.cli build

# Or using the script
python build_index.py
```

This will:
- Load all JSON files from `data/destinations/`
- Generate embeddings for each destination
- Create FAISS indices for fast similarity search
- Save everything to `data/derived/index/`

## 4. Query Destinations

### Using the Web UI (Recommended)

```bash
streamlit run UI.py
```

This will open a browser window with an interactive interface where you can:
- Enter your travel preferences
- Adjust weights for different aspects (activities, scenery, amenities, location)
- View results with visual score breakdowns
- See detailed destination information

### Using the CLI

```bash
# Single search
python -m src.cli search "I want to go hiking in the mountains"

# Interactive mode
python -m src.cli interactive

# With custom top-k
python -m src.cli search "beach destination" --top 10
```

### Using Python

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
```

### Using the Example Script

```bash
python query_example.py
```

## Example Queries

- "I'm looking for beach destinations with water sports"
- "Mountain hiking trails with camping facilities"
- "National parks with wildlife viewing"
- "Historic towns with good restaurants"
- "Desert landscapes for photography"
- "Family-friendly destinations with activities for kids"

## Project Structure

```
road_trip_planner/
├── src/
│   ├── config.py          # Configuration
│   ├── build_index.py     # Index building
│   ├── query.py           # Query interface
│   └── cli.py             # Command-line interface
├── data/
│   ├── destinations/       # Your JSON destination files
│   └── derived/index/     # Generated indices (auto-created)
├── build_index.py         # Standalone build script
├── query_example.py       # Example query script
└── README.md
```

## Next Steps

1. **Add more destinations**: Create more JSON files in `data/destinations/`
2. **Customize weights**: Edit `MATCH_WEIGHTS` in `src/config.py`
3. **Experiment with queries**: Try different search terms
4. **Extend functionality**: Add route planning, weather data, etc.

Happy road tripping! 🗺️

