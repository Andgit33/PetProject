import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

# Import backend query function
from src.query import TripPlanner

# Initialize geocoder (with caching)
@st.cache_resource
def get_geocoder():
    return Nominatim(user_agent="road_trip_planner")

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

@st.cache_data(ttl=3600)  # Cache for 1 hour
def geocode_location(location, state=None, country=None):
    """Geocode a location to get coordinates (cached)."""
    try:
        geolocator = get_geocoder()
        
        # Build search string
        search_parts = []
        if location:
            search_parts.append(str(location))
        if state:
            search_parts.append(str(state))
        if country:
            search_parts.append(str(country))
        
        search_string = ", ".join(search_parts)
        
        # Try geocoding
        location_obj = geolocator.geocode(search_string, timeout=10)
        
        if location_obj:
            return location_obj.latitude, location_obj.longitude
        
        # Fallback: try with just location and country
        if country and location:
            search_string = f"{location}, {country}"
            location_obj = geolocator.geocode(search_string, timeout=10)
            if location_obj:
                return location_obj.latitude, location_obj.longitude
        
        # Fallback: try with just location name
        if location:
            location_obj = geolocator.geocode(str(location), timeout=10)
            if location_obj:
                return location_obj.latitude, location_obj.longitude
        
        return None, None
        
    except (GeocoderTimedOut, GeocoderServiceError, Exception) as e:
        # Don't show warning in cached function, just return None
        return None, None

st.set_page_config(page_title="Road Trip Planner", layout="wide")
st.title("🗺️ Road Trip Planner")

# --- Query input ---
st.header("Describe Your Ideal Destination")
query_text = st.text_area(
    "Enter your travel preferences", 
    height=150,
    placeholder="e.g., I want to go hiking in the mountains with scenic views and camping facilities..."
)

# --- Auto-balancing sliders for weights ---
st.header("Adjust Search Weights (Sum must be at most 1)")

# Initialize session state
if "activities_weight" not in st.session_state:
    st.session_state.activities_weight = 0.4
if "scenery_weight" not in st.session_state:
    st.session_state.scenery_weight = 0.3
if "amenities_weight" not in st.session_state:
    st.session_state.amenities_weight = 0.2
if "location_weight" not in st.session_state:
    st.session_state.location_weight = 0.1

# Custom slider function to enforce sum <= 1
def balanced_slider(label, key, other_keys):
    current_value = st.session_state[key]
    new_value = st.slider(label, 0.0, 1.0, current_value, step=0.01, key=key)

    # Check sum and adjust others if needed
    total = sum(st.session_state[k] for k in [key] + other_keys)

    if total > 1.0:
        excess = total - 1.0
        # Distribute excess proportionally among other sliders
        for other_key in other_keys:
            other_value = st.session_state[other_key]
            if other_value > 0:
                reduce = min(excess, other_value)
                st.session_state[other_key] -= reduce
                excess -= reduce
            if excess <= 0:
                break

# Render sliders in columns
col1, col2 = st.columns(2)
with col1:
    balanced_slider("Activities", "activities_weight", ["scenery_weight", "amenities_weight", "location_weight"])
    balanced_slider("Scenery", "scenery_weight", ["activities_weight", "amenities_weight", "location_weight"])
with col2:
    balanced_slider("Amenities", "amenities_weight", ["activities_weight", "scenery_weight", "location_weight"])
    balanced_slider("Location", "location_weight", ["activities_weight", "scenery_weight", "amenities_weight"])

total_weight = (
    st.session_state.activities_weight + 
    st.session_state.scenery_weight + 
    st.session_state.amenities_weight + 
    st.session_state.location_weight
)
st.caption(f"Total weight: {total_weight:.2f}")

# --- Filters ---
st.header("🔍 Filters")

filter_col1, filter_col2, filter_col3 = st.columns(3)

with filter_col1:
    # Country filter
    # We'll get available countries from the index if it exists
    filter_country = st.selectbox(
        "Filter by Country",
        options=["All Countries"] + ["USA", "France", "Japan", "Greece", "Peru", "Iceland", "Canada", 
                                     "Tanzania", "Indonesia", "Chile", "Argentina", "UAE", "New Zealand",
                                     "Brazil", "Ecuador", "Switzerland", "Cambodia", "Italy", "Australia",
                                     "Jordan", "Norway", "India", "Turkey", "Mauritius", "Croatia", "Vietnam",
                                     "Morocco", "Nepal", "China", "Maldives", "Seychelles"],
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
        with st.spinner("Searching destinations..."):
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
                
                # Share and Download buttons at the top of results
                if filtered_results:
                    # Generate shareable summary
                    share_text = f"🗺️ Road Trip Planner Results\n\n"
                    share_text += f"Query: {query_text}\n\n"
                    share_text += f"Top {len(filtered_results)} Destinations:\n\n"
                    
                    for i, result in enumerate(filtered_results[:5], 1):
                        share_text += f"{i}. {result['destination']} ({result['location']})\n"
                        share_text += f"   Match Score: {result['score']:.1%}\n"
                        budget = infer_budget_level(result.get('full_data', {}))
                        share_text += f"   Budget: {budget}\n\n"
                    
                    # Store in session state
                    st.session_state.share_text = share_text
                    
                    share_col1, share_col2, share_col3 = st.columns([2, 1, 1])
                    with share_col2:
                        if st.button("📤 Share Results", key="share_button"):
                            st.code(share_text, language=None)
                            st.success("📋 Copy the text above to share!")
                    
                    with share_col3:
                        # Download as text file
                        safe_filename = query_text[:20].replace(' ', '_').replace('/', '_').replace('\\', '_')
                        st.download_button(
                            label="💾 Download Results",
                            data=share_text,
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
                        location_name = dest_data.get('location', '')
                        state = dest_data.get('state')
                        country = dest_data.get('country', '')
                        
                        # Geocode location
                        with st.spinner("Loading map..."):
                            lat, lon = geocode_location(location_name, state, country)
                            
                            if lat and lon:
                                # Create map data
                                map_data = pd.DataFrame({
                                    'lat': [lat],
                                    'lon': [lon]
                                })
                                
                                # Display map
                                st.map(map_data, zoom=8)
                                st.caption(f"📍 {result['destination']} - {location_name}, {country}")
                            else:
                                st.info(f"📍 {location_name}, {country} (Map unavailable)")
                        
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
                
            except FileNotFoundError:
                st.error("Index not found! Please build the index first by running: `python -m src.cli build`")
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
                st.exception(e)

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

