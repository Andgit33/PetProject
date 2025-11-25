# Road Trip Planner 🗺️

Discover destinations that actually match your travel vibe. Road Trip Planner combines a curated catalog of 50 hand-crafted locations with semantic search, weighted scoring, and an expressive Streamlit UI so you can describe your ideal getaway and get tailored suggestions instantly.

---

## Why Road Trip Planner?

- **Natural-language friendly** – write “I want volcanic landscapes with hot springs and night skies” and get relevant matches.
- **Multi-aspect ranking** – activities, scenery, amenities, and location each have their own embedding + adjustable weight so you control the blend.
- **Actionable insights** – visual score breakdowns, inferred budget level, best season, nearby attractions, and downloadable summaries.
- **Ready for deployment** – Streamlit UI builds the FAISS index automatically on first run, so it works out-of-the-box on Streamlit Community Cloud or any custom host.

---

## How It Works

1. **Destination catalog** – `data/destinations/` holds JSON profiles describing activities, scenery, amenities, and metadata for 50 destinations.
2. **Index building** – `src/build_index.py` turns each profile into four embeddings (activities, scenery, amenities, location) using `sentence-transformers/paraphrase-MiniLM-L3-v2` and stores them in FAISS indices under `data/derived/index/`.
3. **Semantic search** – `TripPlanner` (in `src/query.py`) embeds your query, performs cosine-similarity search across every destination, applies your weights, and returns ranked matches.
4. **Streamlit experience** – `UI.py` wraps the search in a friendly interface, adds filters (country, budget, season), geocodes destinations for map previews, and handles sharing/downloading the results.

---

## Repository Tour

```
road_trip_planner/
├── UI.py                  # Streamlit app
├── src/
│   ├── config.py          # Paths, defaults, Pydantic models
│   ├── build_index.py     # DestinationIndex builder
│   ├── query.py           # TripPlanner search logic
│   └── cli.py             # Typer-powered CLI
├── data/
│   ├── destinations/      # Source JSON files (tracked)
│   └── derived/index/     # Generated FAISS indices + cache (gitignored)
├── build_index.py         # Convenience script to rebuild the index
├── query_example.py       # Quick script showing API usage
├── requirements.txt       # Pip environment (Python 3.11)
└── env.yml                # Conda environment (Python 3.11)
```

---

## Getting Started

### Requirements
- Python **3.11** (matches Streamlit Cloud)
- Conda **or** virtualenv
- Internet access for the geocoding feature (Nominatim)

### Installation
```bash
# Option 1: Conda
conda env create -f env.yml
conda activate road-trip-planner

# Option 2: Pip/venv
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Build the Index (optional)
The Streamlit UI will build the FAISS indices automatically the first time you run a search. If you want to pre-build them (for faster cold starts or local CLI usage):

```bash
python -m src.cli build
# or
python build_index.py
```

---

## Using the App

### Streamlit UI (recommended)
```bash
streamlit run UI.py
```

From there you can:
1. **Describe your trip** in natural language.
2. **Adjust weights** so the ranking favors activities, scenery, amenities, or location.
3. **Apply filters** (country list is populated from the destination files, budget tier is inferred automatically, season filters exact matches).
4. **Explore results** – each destination shows a match score, charted breakdowns, inferred budget badge, key facts, map, and expandable metadata.
5. **Download** the top matches as a text summary to share with friends or keep for planning.

### CLI
```bash
python -m src.cli search "I want to go hiking in the mountains"
python -m src.cli interactive
```
The CLI uses the same TripPlanner engine and prints tables, score breakdowns, and rich-formatted explanations.

### Python API
```python
from src.query import TripPlanner

planner = TripPlanner()
results = planner.search_destinations(
    "Beach destination with water sports and good restaurants",
    top_k=5
)
for match in results:
    print(match["destination"], match["score"])
```

---

## Destination Data

Each JSON file in `data/destinations/` represents one location. Fields include:

- `name`, `location`, `state`, `country`
- `description`
- Lists for `activities`, `scenery`, `amenities`, `best_season`, `nearby_attractions`, `keywords`
- Optional `travel_time`

Add new destinations by copying an existing file, editing the values, and rerunning `python -m src.cli build` (or just restarting the Streamlit app and letting auto-build handle it).

---

## Troubleshooting

- **“Index not found”** – the auto-build will kick in as long as `data/destinations/` exists. If it doesn’t, copy the JSON files from the repo.
- **Geocoding errors** – requires internet access. The app hides the map if Nominatim fails and continues gracefully.
- **Weights feel ineffective** – make sure you let the search finish after changing sliders. The system searches *every* destination before applying weights, so they should have noticeable impact once the index is ready.
- **First run feels slow** – embedding + FAISS build can take a couple of minutes on Streamlit Cloud; subsequent searches are instant because everything is cached.

---

## Roadmap

- Route planning between suggested destinations
- Weather overlays for the chosen season
- Multi-day itinerary builder
- On-device photo previews for each destination
- Personalization loop that learns from thumbs-up/down feedback

---

## License

MIT License – see `LICENSE`.

