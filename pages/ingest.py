# pages/ingest.py

import streamlit as st
import requests
import time
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from utils.connect import initialize_connections

# Initialize connections from our updated connect.py
initialize_connections()

@st.cache_data
def get_spotify_auth_token():
    """Gets an auth token from the Spotify API."""
    auth_url = 'https://accounts.spotify.com/api/token'
    try:
        auth_response = requests.post(auth_url, {
            'grant_type': 'client_credentials',
            'client_id': st.secrets["SPOTIFY_CLIENT_ID"],
            'client_secret': st.secrets["SPOTIFY_CLIENT_SECRET"],
        })
        auth_response.raise_for_status()
        auth_response_data = auth_response.json()
        return auth_response_data['access_token']
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to get Spotify token: {e}")
        return None

@st.cache_data
def get_tracks_from_spotify(playlist_id):
    """Gets a list of tracks from a specific Spotify playlist."""
    access_token = get_spotify_auth_token()
    if not access_token:
        return None
    headers = {'Authorization': f'Bearer {access_token}'}
    playlist_url = f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks'
    try:
        response = requests.get(playlist_url, headers=headers)
        response.raise_for_status()
        playlist_tracks = response.json().get('items', [])
        return playlist_tracks
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to get tracks from Spotify. Is the Playlist ID correct? Error: {e}")
        return None

@st.cache_data
def get_song_description(song_name, artist_name):
    """Generates a setting/vibe description for a song using Google Gemini."""
    prompt = f"""
        You are an AI agent that helps users determine what songs to play to match
        their setting. Based on the included song name and artist, '{song_name}' by '{artist_name}', write up a
        description of what kind of setting would be appropriate to listen to. Do not make assumptions based purely
        on the song name, you should try to use real information about the song to come up with your setting description.
    """
    # Use the Gemini text model from the session state
    gemini_text_model = st.session_state.gemini_text_model
    response = gemini_text_model.generate_content(prompt)
    
    # Add a small delay to avoid hitting the free tier rate limit (e.g., 60 queries per minute)
    time.sleep(1)
    
    return response.text.strip()

def load_tracks_to_faiss(new_playlist_id):
    """
    Main function to fetch songs, generate descriptions, and build an
    in-memory FAISS vector store.
    """
    playlist_tracks = get_tracks_from_spotify(new_playlist_id)
    if not playlist_tracks:
        st.warning("Could not retrieve tracks. Please check the Playlist ID and your Spotify credentials.")
        return

    st.toast("New playlist detected. Building a new in-memory vector store.")
    
    progress_bar = st.progress(0, "Starting song processing...")
    num_tracks = len(playlist_tracks)
    langchain_documents = []

    for i, item in enumerate(playlist_tracks):
        percentage_complete = (i + 1) / num_tracks
        if not item or 'track' not in item or not item['track']:
            progress_bar.progress(percentage_complete, text=f"Skipping invalid item {i+1}/{num_tracks}.")
            continue
        
        track = item['track']
        song_name = track.get("name", "Unknown Song")
        artist_name = track.get('artists', [{}])[0].get('name', 'Unknown Artist')
        song_url = track.get('external_urls', {}).get('spotify')

        if not song_url:
            progress_bar.progress(percentage_complete, text=f"Skipping {song_name} (no URL).")
            continue
            
        progress_text = f"({i+1}/{num_tracks}) Generating description for: {song_name}"
        progress_bar.progress(percentage_complete, text=progress_text)
        
        description = get_song_description(song_name, artist_name)
        
        # Create a LangChain Document for each song
        metadata = {
            "Song_Name": song_name,
            "Artist": artist_name,
            "Song_URL": song_url
        }
        doc = Document(page_content=description, metadata=metadata)
        langchain_documents.append(doc)

    if not langchain_documents:
        st.error("No valid songs could be processed from this playlist.")
        progress_bar.empty()
        return

    progress_bar.progress(1.0, "Building FAISS vector store from all song descriptions...")
    embedding_model = st.session_state.embedding_model
    vector_store = FAISS.from_documents(langchain_documents, embedding_model)
    
    st.session_state.vector_store = vector_store
    st.session_state.current_pid = new_playlist_id

    progress_bar.empty()
    st.success(f"Successfully loaded {len(langchain_documents)} songs into the in-memory FAISS store!")
    time.sleep(2)
    st.rerun()

def clear_playlist():
    """Clears the in-memory vector store and playlist ID."""
    st.session_state.vector_store = None
    st.session_state.current_pid = None
    st.toast("Cleared the in-memory vector store.")
    st.rerun()

def load_playlist():
    """Wrapper function called by the UI button."""
    new_playlist_id = st.session_state.get("pid_input", "").strip()
    if new_playlist_id:
        load_tracks_to_faiss(new_playlist_id)
    else:
        st.warning("Please enter a Spotify Playlist ID.")

### --- UI SECTION --- ###
st.title("Vibe Check 🎶")
st.markdown("### Connect to Your Playlist")

with st.container(border=True):
    st.write("**Current Playlist ID:**", st.session_state.get("current_pid", "None"))
    disable_buttons = not st.session_state.get("current_pid")
    st.link_button(
        "Open playlist in Spotify",
        f"https://open.spotify.com/playlist/{st.session_state.get('current_pid')}" if not disable_buttons else "#",
        disabled=disable_buttons
    )
    st.button("Clear Playlist from Memory", on_click=clear_playlist, disabled=disable_buttons)

with st.form(key="new_playlist_form"):
    st.markdown(
        """
        Copy/paste a Spotify playlist ID below. This app will:
        1. Retrieve songs from the playlist using the Spotify API.
        2. Generate descriptions for each song using **Google's Gemini model**.
        3. Load the song data into an **in-memory FAISS vector store**.
        """
    )
    new_pid = st.text_input(
        "Example Playlist ID: 37i9dQZF1DXcBWIGoYBM5M",
        key="pid_input",
        placeholder="Enter Spotify Playlist ID here"
    )
    st.form_submit_button("Load Playlist", on_click=load_playlist)