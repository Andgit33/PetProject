# Quick Start Guide

## 1. Setup Environment

The project targets **Python 3.11** (same version Streamlit Cloud runs). Create or upgrade your environment to that version before installing dependencies:

```bash
# Using conda (recommended)
conda env create -f env.yml
conda activate road-trip-planner

# Or using pip
pip install sentence-transformers faiss-cpu numpy torch streamlit plotly rich typer pydantic geopy pandas
```

## 2. Build the Index (Optional)

The project comes with **50 pre-loaded destinations** from around the world. **The index builds automatically on first use** when you run the Streamlit app, so you can skip this step if you're using the web UI.

However, you can also build it manually:

```bash
# Using the CLI
python -m src.cli build

# Or using the script
python build_index.py
```

This will:
- Load all 50 JSON files from `data/destinations/`
- Generate embeddings for each destination across 4 dimensions
- Create FAISS indices for fast similarity search
- Save everything to `data/derived/index/`

**Note:** The index builds automatically on first use in the Streamlit app. Manual building is only needed if you want to build it before running the app, or when you add/modify destinations.

## 3. Query Destinations

### Using the Web UI (Recommended)

```bash
streamlit run UI.py
```

This will open a browser window with an interactive interface where you can:
- Enter your travel preferences in natural language
- Adjust weights for different aspects (activities, scenery, amenities, location)
- View results with visual score breakdowns (charts, gauges, progress bars)
- See interactive maps for each destination
- Filter by country, budget level, and best season
- Download results as text file
- See detailed destination information with full metadata
- **Note:** On first run, the index will build automatically (you'll see a progress message)

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

