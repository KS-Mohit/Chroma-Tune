# pages/query.py

import streamlit as st
from PIL import Image
from utils.connect import initialize_connections

# Initialize connections from our updated connect.py
initialize_connections()

# The prompt for the multimodal LLM remains the same
prompt = """
    You are an AI agent that helps users find music that matches their current setting.
    Please describe the ambiance and vibe of the included image. 
    What types of music would be fitting for this setting? 
    What kind of mood is conveyed in the image?
"""

# Initialize session state variables
if 'user_feedback' not in st.session_state:
    st.session_state.user_feedback = ''
if 'top_songs' not in st.session_state:
    st.session_state.top_songs = []

@st.cache_data
def get_setting_description_from_image(photo_input):
    """
    Sends an image to Google Gemini and gets a text description of the vibe.
    """
    if not photo_input:
        return ""
    
    # Use the Gemini vision model from the session state
    gemini_vision_model = st.session_state.gemini_vision_model
    
    # Open the image using Pillow
    image = Image.open(photo_input)
    
    # Generate content using the Gemini model with both text and image
    response = gemini_vision_model.generate_content([prompt, image])
    
    return response.text.strip()

def find_songs(setting_description):
    """
    Finds the top 5 most similar songs from the in-memory FAISS vector store.
    """
    vector_store = st.session_state.get("vector_store")
    if not vector_store:
        st.warning("Please load a playlist first on the 'Connect to Your Playlist' page.")
        return

    if not setting_description:
        st.session_state.top_songs = []
        return

    # Use the similarity_search_with_score method from FAISS
    results = vector_store.similarity_search_with_score(setting_description, k=5)

    # Process the results into the format our UI expects
    top_songs = []
    for doc, score in results:
        song_data = {
            "Song_Name": doc.metadata.get("Song_Name"),
            "Artist": doc.metadata.get("Artist"),
            "Song_URL": doc.metadata.get("Song_URL"),
            "similarity_score": score  # Lower score means more similar in FAISS
        }
        top_songs.append(song_data)
    
    st.session_state.top_songs = top_songs

def handle_submit():
    """
    Handles the form submission, gets the vibe description, and finds songs.
    """
    if st.session_state.photo_input or st.session_state.text_input:
        with st.spinner("Analyzing your vibe with Google Gemini..."):
            setting_description = get_setting_description_from_image(st.session_state.photo_input)
            full_search_query = " ".join([setting_description, st.session_state.text_input])
            st.session_state.user_feedback = full_search_query
            find_songs(full_search_query)
    else:
        st.warning("Please upload a photo or describe your setting.")
        st.session_state.user_feedback = None

### --- UI SECTION --- ###
st.title("Vibe Check 🎶")
st.markdown("### Find Songs Based on Your Vibe")

# Add a check to ensure a playlist is loaded before allowing search
if not st.session_state.get("vector_store"):
    st.info("⬅️ Please go to the 'Connect to Your Playlist' page to load some songs first.")
    st.stop()

# --- THIS IS THE ONLY LINE THAT CHANGED ---
# By putting "File Uploader" first, it becomes the default option.
photo_method = st.radio(
    "Select an image upload method:",
    ["File Uploader", "Camera"],
    horizontal=True,
)

with st.form(key="query_form"):
    if photo_method == "Camera":
        photo_input = st.camera_input(
            "Take a picture of your setting:", 
            key="photo_input"
        )
    else: # File Uploader
        photo_input = st.file_uploader(
            "Upload a photo of your setting:",
            key="photo_input",
            type=["jpg", "jpeg", "png"]
        )
    
    text_input = st.text_input(
        "Optionally, add more details about your vibe:",
        key="text_input",
        placeholder="e.g., 'upbeat and energetic for a workout'"
    )
    
    st.form_submit_button("Find My Vibe ✨", on_click=handle_submit, use_container_width=True)

# --- Display Results ---
if st.session_state.get('user_feedback'):
    with st.container(border=True):
        st.header("✨ Your Vibe Analysis (from Google Gemini)")
        st.write(st.session_state.user_feedback)

    with st.container(border=True):
        st.header("🎧 Recommended Songs")
        if st.session_state.top_songs:
            for song in st.session_state.top_songs:
                name = song.get("Song_Name", "N/A")
                artist = song.get("Artist", "N/A")
                url = song.get("Song_URL", "")
                st.markdown(f"- **[{name} - {artist}]({url})**")
            
            with st.expander("Show Raw Data from FAISS"):
                st.dataframe(
                    st.session_state.top_songs,
                    column_config={"Song_URL": st.column_config.LinkColumn()}
                )
        else:
            st.info("No matching songs found. Try a different vibe!")
elif st.session_state.get('photo_input') or st.session_state.get('text_input'):
     st.info("Click 'Find My Vibe' to get song recommendations.")
