import json
import logging

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

# Import backend query function
from src.query import TripPlanner
from src.config import DESTINATIONS_DIR

logger = logging.getLogger("road_trip_planner.ui")

def infer_budget_level(destination_data):
    """Infer budget level from amenities and description."""
    amenities = destination_data.get("amenities", [])
    description = destination_data.get("description", "").lower()
    
    # Luxury indicators
    luxury_keywords = ["luxury", "resort", "5-star", "exclusive", "premium", "overwater", "villa", "spa"]
    luxury_amenities = ["luxury hotels", "luxury resorts", "spas", "private", "concierge"]
    
    # Budget indicators
    budget_keywords = ["campground", "hostel", "budget", "affordable", "cheap"]
    budget_amenities = ["campgrounds", "hostels", "budget hotels", "camping"]
    
    # Check for luxury
    if any(kw in description for kw in luxury_keywords) or \
       any(any(kw in amenity.lower() for kw in luxury_amenities) for amenity in amenities):
        return "Luxury"
    
    # Check for budget
    if any(kw in description for kw in budget_keywords) or \
       any(any(kw in amenity.lower() for kw in budget_amenities) for amenity in amenities):
        return "Budget-Friendly"
    
    # Default to mid-range
    return "Mid-Range"

st.set_page_config(page_title="Road Trip Planner", layout="wide")
st.title("🗺️ Road Trip Planner")

# --- Query input ---
st.header("Describe Your Ideal Destination")
default_prompt = (
    "I want to drive along the coast, stopping at charming seaside towns, "
    "lighthouses, and beaches. I'd like spots where I can walk on cliffs, take photos, "
    "and enjoy fresh seafood."
)
query_text = st.text_area(
    "Enter your travel preferences", 
    height=150,
    placeholder="e.g., I want to go hiking in the mountains with scenic views and camping facilities...",
    value=default_prompt
)

# --- Auto-balancing sliders for weights ---
st.header("Adjust Search Weights")

# Initialize session state
if "activities_weight" not in st.session_state:
    st.session_state.activities_weight = 0.4
if "scenery_weight" not in st.session_state:
    st.session_state.scenery_weight = 0.3
if "amenities_weight" not in st.session_state:
    st.session_state.amenities_weight = 0.2
if "location_weight" not in st.session_state:
    st.session_state.location_weight = 0.1

all_weight_keys = ["activities_weight", "scenery_weight", "amenities_weight", "location_weight"]

# Store previous values to detect which slider changed
if "_prev_weights" not in st.session_state:
    st.session_state._prev_weights = {
        "activities_weight": st.session_state.get("activities_weight", 0.4),
        "scenery_weight": st.session_state.get("scenery_weight", 0.3),
        "amenities_weight": st.session_state.get("amenities_weight", 0.2),
        "location_weight": st.session_state.get("location_weight", 0.1)
    }

# Check for pending adjustments (from previous run) and apply them BEFORE rendering widgets
if "_pending_adjustments" in st.session_state and st.session_state._pending_adjustments:
    adjustments = st.session_state._pending_adjustments
    for key, value in adjustments.items():
        st.session_state[key] = float(value)
    del st.session_state._pending_adjustments
    # Update previous values
    for key in all_weight_keys:
        st.session_state._prev_weights[key] = float(st.session_state.get(key, 0.0))
    st.rerun()

# Custom slider function to enforce sum <= 1
def balanced_slider(label, key, other_keys):
    # Ensure all keys exist in session state with valid float values
    if key not in st.session_state:
        st.session_state[key] = 0.0
    for other_key in other_keys:
        if other_key not in st.session_state:
            st.session_state[other_key] = 0.0
    
    current_value = float(st.session_state[key])
    st.slider(label, 0.0, 1.0, current_value, step=0.01, key=key)

# Render sliders in columns
col1, col2 = st.columns(2)
with col1:
    balanced_slider("Activities", "activities_weight", ["scenery_weight", "amenities_weight", "location_weight"])
    balanced_slider("Scenery", "scenery_weight", ["activities_weight", "amenities_weight", "location_weight"])
with col2:
    balanced_slider("Amenities", "amenities_weight", ["activities_weight", "scenery_weight", "location_weight"])
    balanced_slider("Location", "location_weight", ["activities_weight", "scenery_weight", "amenities_weight"])

# After all sliders are rendered, check if adjustments are needed
changed_key = None

# Find which slider changed (if any)
for key in all_weight_keys:
    current_val = float(st.session_state.get(key, 0.0))
    prev_val = float(st.session_state._prev_weights.get(key, 0.0))
    if abs(current_val - prev_val) > 0.001:
        changed_key = key
        break

# If a slider changed and total exceeds 1.0, calculate and schedule adjustments
if changed_key:
    total = sum(float(st.session_state.get(k, 0.0)) for k in all_weight_keys)
    if total > 1.0:
        excess = total - 1.0
        # Get other keys (all except the one that changed)
        other_keys = [k for k in all_weight_keys if k != changed_key]
        
        # Calculate adjustments
        adjustments = {}
        for other_key in other_keys:
            if excess <= 0.001:
                break
            other_value = float(st.session_state.get(other_key, 0.0))
            if other_value > 0:
                reduce_amount = min(excess, other_value)
                new_other_value = max(0.0, other_value - reduce_amount)
                adjustments[other_key] = float(new_other_value)
                excess -= reduce_amount
        
        # Store adjustments for next run (to be applied before widgets are rendered)
        if adjustments:
            st.session_state._pending_adjustments = adjustments
            st.rerun()

# Update previous values for next render
for key in all_weight_keys:
    st.session_state._prev_weights[key] = float(st.session_state.get(key, 0.0))

total_weight = (
    st.session_state.activities_weight + 
    st.session_state.scenery_weight + 
    st.session_state.amenities_weight + 
    st.session_state.location_weight
)
st.caption(f"Total weight: {total_weight:.2f}")

@st.cache_data(show_spinner=False)
def get_country_options():
    """Return sorted list of countries present in destination data."""
    countries = set()
    if not DESTINATIONS_DIR.exists():
        return []
    for dest_file in DESTINATIONS_DIR.glob("*.json"):
        try:
            data = json.loads(dest_file.read_text())
            country = data.get("country")
            if country:
                countries.add(country)
        except Exception:
            continue
    return sorted(countries)


# --- Filters ---
st.header("🔍 Filters")

dynamic_countries = get_country_options()
fallback_countries = [
    "USA", "France", "Japan", "Greece", "Peru", "Iceland", "Canada",
    "Tanzania", "Indonesia", "Chile", "Argentina", "UAE", "New Zealand",
    "Brazil", "Ecuador", "Switzerland", "Cambodia", "Italy", "Australia",
    "Jordan", "Norway", "India", "Turkey", "Mauritius", "Croatia", "Vietnam",
    "Morocco", "Nepal", "China", "Maldives", "Seychelles"
]
country_options = ["All Countries"] + (dynamic_countries if dynamic_countries else fallback_countries)

filter_col1, filter_col2, filter_col3 = st.columns(3)

with filter_col1:
    # Country filter
    filter_country = st.selectbox(
        "Filter by Country",
        options=country_options,
        index=0
    )

with filter_col2:
    # Budget filter
    filter_budget = st.selectbox(
        "Budget Level",
        options=["Any Budget", "Budget-Friendly", "Mid-Range", "Luxury"],
        index=0
    )

with filter_col3:
    # Season filter
    filter_season = st.selectbox(
        "Best Season",
        options=["Any Season", "Spring", "Summer", "Fall", "Winter"],
        index=0
    )

# --- Top K input ---
top_k = st.number_input("Number of top destinations to show", min_value=1, max_value=20, value=5)

# Initialize planner (with caching) - moved outside button handler
@st.cache_resource
def get_planner():
    return TripPlanner()

# --- Run search ---
if st.button("🔍 Find Destinations", type="primary"):
    if not query_text.strip():
        st.warning("Please enter your travel preferences.")
    else:
        # Check if index exists to show appropriate message
        from src.config import INDEX_PATH
        index_exists = INDEX_PATH.with_suffix('.activities.idx').exists()
        
        # Build appropriate spinner message
        if not index_exists:
            spinner_message = "🔨 Building search index and geocoding destinations for maps. This may take several minutes (geocoding is rate-limited to 1 request/second)..."
        else:
            spinner_message = "Searching destinations..."
        
        with st.spinner(spinner_message):
            try:
                planner = get_planner()
                
                # Get weights from sliders
                slider_weights = {
                    "activities": st.session_state.activities_weight,
                    "scenery": st.session_state.scenery_weight,
                    "amenities": st.session_state.amenities_weight,
                    "location": st.session_state.location_weight
                }
                
                # Normalize weights if they don't sum to 1
                total = sum(slider_weights.values())
                if total > 0:
                    slider_weights = {k: v/total for k, v in slider_weights.items()}
                
                # Temporarily update planner weights with slider values
                original_weights = planner.weights.copy()
                planner.weights = slider_weights
                
                # Call backend search function (uses self.weights in the calculation)
                results = planner.search_destinations(
                    query_text=query_text,
                    top_k=int(top_k)
                )
                
                # Restore original weights
                planner.weights = original_weights
                
                # Apply filters
                filtered_results = []
                for result in results:
                    dest_data = result.get('full_data', {})
                    
                    # Country filter
                    if filter_country != "All Countries":
                        if dest_data.get('country') != filter_country:
                            continue
                    
                    # Budget filter
                    if filter_budget != "Any Budget":
                        budget_level = infer_budget_level(dest_data)
                        if budget_level != filter_budget:
                            continue
                    
                    # Season filter
                    if filter_season != "Any Season":
                        best_seasons = [s.lower() for s in dest_data.get('best_season', [])]
                        if filter_season.lower() not in best_seasons:
                            continue
                    
                    filtered_results.append(result)
                
                # Store results in session state for sharing
                st.session_state.last_results = filtered_results
                st.session_state.last_query = query_text
                
                st.success(f"Found {len(filtered_results)} matching destinations!")
                
                # Download button at the top of results
                if filtered_results:
                    # Generate downloadable summary
                    download_text = f"🗺️ Road Trip Planner Results\n\n"
                    download_text += f"Query: {query_text}\n\n"
                    download_text += f"Top {len(filtered_results)} Destinations:\n\n"
                    
                    for i, result in enumerate(filtered_results[:5], 1):
                        download_text += f"{i}. {result['destination']} ({result['location']})\n"
                        download_text += f"   Match Score: {result['score']:.1%}\n"
                        budget = infer_budget_level(result.get('full_data', {}))
                        download_text += f"   Budget: {budget}\n\n"
                    
                    # Download as text file
                    safe_filename = query_text[:20].replace(' ', '_').replace('/', '_').replace('\\', '_')
                    st.download_button(
                        label="💾 Download Results",
                        data=download_text,
                        file_name=f"road_trip_results_{safe_filename}.txt",
                        mime="text/plain",
                        key="download_file"
                    )
                
                # --- Display results ---
                for i, result in enumerate(filtered_results, 1):
                    with st.container():
                        st.markdown("---")
                        
                        # Header with prominent match score
                        col_header1, col_header2 = st.columns([3, 1])
                        
                        with col_header1:
                            st.subheader(f"📍 {i}. {result['destination']}")
                            st.caption(f"📍 {result['location']}")
                        
                        with col_header2:
                            # Color-coded match score with visual indicator
                            score = result['score']
                            if score >= 0.8:
                                score_color = "#00cc00"  # Green
                                score_label = "Excellent Match"
                            elif score >= 0.6:
                                score_color = "#66cc00"  # Light green
                                score_label = "Great Match"
                            elif score >= 0.4:
                                score_color = "#ffcc00"  # Yellow
                                score_label = "Good Match"
                            else:
                                score_color = "#ff9900"  # Orange
                                score_label = "Fair Match"
                            
                            # Large score display
                            st.markdown(
                                f"""
                                <div style="text-align: center; padding: 15px; background: linear-gradient(135deg, {score_color}22, {score_color}11); 
                                border-radius: 10px; border: 2px solid {score_color};">
                                    <h2 style="color: {score_color}; margin: 0; font-size: 2.5em;">{score:.1%}</h2>
                                    <p style="color: {score_color}; margin: 5px 0 0 0; font-weight: bold;">{score_label}</p>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )
                        
                        # Progress bar for match score
                        st.progress(score, text=f"Overall Match: {score:.1%}")
                        
                        # Score breakdown in columns with visual bars
                        st.markdown("#### 📊 Score Breakdown")
                        score_cols = st.columns(4)
                        
                        dimension_scores = [
                            ("Activities", result['activities_score'], "#1f77b4"),
                            ("Scenery", result['scenery_score'], "#ff7f0e"),
                            ("Amenities", result['amenities_score'], "#2ca02c"),
                            ("Location", result['location_score'], "#d62728")
                        ]
                        
                        for idx, (name, dim_score, color) in enumerate(dimension_scores):
                            with score_cols[idx]:
                                st.markdown(f"**{name}**")
                                st.progress(dim_score, text=f"{dim_score:.1%}")
                                st.markdown(
                                    f'<div style="text-align: center; color: {color}; font-weight: bold; font-size: 1.2em;">{dim_score:.2f}</div>',
                                    unsafe_allow_html=True
                                )
                        
                        # Enhanced visual chart for dimension scores
                        dimensions = ['Activities', 'Scenery', 'Amenities', 'Location']
                        scores = [
                            result['activities_score'],
                            result['scenery_score'],
                            result['amenities_score'],
                            result['location_score']
                        ]
                        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
                        
                        # Horizontal bar chart for better readability
                        fig = go.Figure()
                        for dim, score, color in zip(dimensions, scores, colors):
                            fig.add_trace(go.Bar(
                                name=dim,
                                x=[score],
                                y=[dim],
                                orientation='h',
                                marker=dict(
                                    color=color,
                                    line=dict(color='white', width=2)
                                ),
                                text=[f"{score:.2f}"],
                                textposition='inside',
                                textfont=dict(color='white', size=14, family='Arial Black')
                            ))
                        
                        fig.update_layout(
                            title=dict(
                                text="<b>Dimension Similarity Scores</b>",
                                font=dict(size=18, color='#333')
                            ),
                            xaxis=dict(
                                title="Similarity Score",
                                range=[0, 1],
                                tickformat='.2f'
                            ),
                            yaxis=dict(title=""),
                            height=300,
                            barmode='group',
                            showlegend=False,
                            plot_bgcolor='rgba(0,0,0,0)',
                            paper_bgcolor='rgba(0,0,0,0)',
                            margin=dict(l=20, r=20, t=50, b=20)
                        )
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Radial/Donut chart for overall score visualization
                        fig_radial = go.Figure(go.Indicator(
                            mode="gauge+number+delta",
                            value=score * 100,
                            domain={'x': [0, 1], 'y': [0, 1]},
                            title={'text': "Overall Match Score", 'font': {'size': 20}},
                            delta={'reference': 50},
                            gauge={
                                'axis': {'range': [None, 100]},
                                'bar': {'color': score_color},
                                'steps': [
                                    {'range': [0, 50], 'color': "lightgray"},
                                    {'range': [50, 80], 'color': "gray"}
                                ],
                                'threshold': {
                                    'line': {'color': "red", 'width': 4},
                                    'thickness': 0.75,
                                    'value': 90
                                }
                            }
                        ))
                        fig_radial.update_layout(height=250)
                        st.plotly_chart(fig_radial, use_container_width=True)
                        
                        # Map visualization
                        st.markdown("### 🗺️ Location")
                        dest_data = result.get('full_data', {})
                        destination_name = dest_data.get('name') or result.get('destination')
                        region = dest_data.get('location')
                        state = dest_data.get('state')
                        country = dest_data.get('country', '')
                        
                        # Get stored coordinates (geocoded automatically during index build)
                        lat = dest_data.get('latitude')
                        lon = dest_data.get('longitude')
                        
                        if lat and lon:
                            # Create map data
                            map_data = pd.DataFrame({
                                'lat': [lat],
                                'lon': [lon]
                            })
                            
                            # Display map
                            st.map(map_data, zoom=8)
                            caption_parts = [part for part in [region, state, country] if part]
                            if caption_parts:
                                st.caption(f"📍 {destination_name} — {', '.join(caption_parts)}")
                            else:
                                st.caption(f"📍 {destination_name}")
                        else:
                            # Coordinates should be present after index build, but show message if missing
                            display_parts = [part for part in [destination_name, region, country] if part]
                            st.info(f"📍 {', '.join(display_parts) or 'Unknown location'} (Map unavailable - coordinates not found. Rebuild index to geocode destinations.)")
                        
                        # Destination details in columns with visual cards
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            st.markdown("### 📝 Destination Summary")
                            # Styled text area with better visual presentation
                            st.markdown(
                                f"""
                                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 10px; 
                                border-left: 4px solid {score_color}; margin: 10px 0;">
                                    <p style="line-height: 1.6; color: #333;">{result['explanation']}</p>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )
                        
                        with col2:
                            st.markdown("### ⚡ Quick Info")
                            # dest_data already retrieved above
                            
                            # Budget indicator
                            budget_level = infer_budget_level(dest_data)
                            budget_colors = {
                                "Budget-Friendly": "#28a745",  # Green
                                "Mid-Range": "#ffc107",  # Yellow/Orange
                                "Luxury": "#dc3545"  # Red
                            }
                            budget_icons = {
                                "Budget-Friendly": "💰",
                                "Mid-Range": "💵",
                                "Luxury": "💎"
                            }
                            budget_color = budget_colors.get(budget_level, "#6c757d")
                            budget_icon = budget_icons.get(budget_level, "💰")
                            
                            st.markdown(
                                f"""
                                <div style="background-color: {budget_color}22; padding: 10px; border-radius: 8px; 
                                border-left: 4px solid {budget_color}; margin-bottom: 15px; text-align: center;">
                                    <p style="margin: 0; font-weight: bold; color: {budget_color}; font-size: 1.1em;">
                                        {budget_icon} {budget_level}
                                    </p>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )
                            
                            # Visual cards for quick info
                            info_items = []
                            
                            if dest_data.get('best_season'):
                                seasons = ', '.join(dest_data['best_season'])
                                info_items.append(f"**🌤️ Best Season:** {seasons}")
                            
                            if dest_data.get('travel_time'):
                                info_items.append(f"**✈️ Travel Time:** {dest_data['travel_time']}")
                            
                            if dest_data.get('activities'):
                                info_items.append(f"**🎯 Activities:** {len(dest_data['activities'])} options")
                            
                            if dest_data.get('nearby_attractions'):
                                info_items.append(f"**📍 Nearby:** {len(dest_data['nearby_attractions'])} attractions")
                            
                            # Display in styled container
                            if info_items:
                                st.markdown(
                                    f"""
                                    <div style="background-color: #e8f4f8; padding: 15px; border-radius: 8px;">
                                        {'<br>'.join([f'<p style="margin: 8px 0;">{item}</p>' for item in info_items])}
                                    </div>
                                    """,
                                    unsafe_allow_html=True
                                )
                        
                        # Expandable full details with visual separator
                        st.markdown("<br>", unsafe_allow_html=True)
                        with st.expander("🔍 View Full Details"):
                            # Display key highlights first
                            if dest_data.get('activities'):
                                st.markdown("**🎯 Activities:**")
                                activities_str = " • ".join(dest_data['activities'][:10])
                                st.markdown(f"*{activities_str}*")
                            
                            if dest_data.get('scenery'):
                                st.markdown("**🏔️ Scenery:**")
                                scenery_str = " • ".join(dest_data['scenery'][:10])
                                st.markdown(f"*{scenery_str}*")
                            
                            st.json(dest_data)
                
            except FileNotFoundError as e:
                st.error(f"Required files not found: {str(e)}")
                st.info("💡 The index will be built automatically on first use. If this error persists, please ensure destination files are available in the data/destinations directory.")
            except ValueError as e:
                if "No destination files found" in str(e):
                    st.error("No destination files found! Please ensure destination JSON files are in the data/destinations directory.")
                else:
                    st.error(f"Error: {str(e)}")
            except Exception as e:
                # Show user-friendly error message without exposing stack trace
                error_msg = str(e)
                # Sanitize error messages to avoid exposing sensitive paths
                if "mount" in error_msg.lower() or "path" in error_msg.lower():
                    st.error("An error occurred while processing your request. Please try again or contact support if the issue persists.")
                else:
                    st.error(f"An error occurred: {error_msg}")
                # Full error details are logged server-side (not shown to users)
                logger.exception("Streamlit search failed")

# --- Sidebar with info ---
with st.sidebar:
    st.header("ℹ️ About")
    st.markdown("""
    **Road Trip Planner** uses semantic search to find destinations 
    that match your travel preferences.
    
    **How it works:**
    1. Enter your travel preferences
    2. Adjust weights to prioritize different aspects
    3. Click "Find Destinations" to search
    
    **Tips:**
    - Be specific about activities you enjoy
    - Mention scenery preferences (mountains, beaches, etc.)
    - Include any must-have amenities
    """)
    
    st.header("📊 Current Weights")
    
    # Visual weight indicators
    weights_data = {
        "Activities": (st.session_state.activities_weight, "#1f77b4"),
        "Scenery": (st.session_state.scenery_weight, "#ff7f0e"),
        "Amenities": (st.session_state.amenities_weight, "#2ca02c"),
        "Location": (st.session_state.location_weight, "#d62728")
    }
    
    for name, (weight, color) in weights_data.items():
        st.markdown(f"**{name}**")
        st.progress(weight, text=f"{weight:.1%}")
        st.markdown(f'<div style="text-align: center; color: {color}; font-weight: bold;">{weight:.2f}</div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

