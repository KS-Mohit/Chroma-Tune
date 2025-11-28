# services.py
import os
import requests
import time
import json
import re
from dotenv import load_dotenv
import google.generativeai as genai
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

def get_spotify_token():
    try:
        response = requests.post('https://accounts.spotify.com/api/token', {
            'grant_type': 'client_credentials',
            'client_id': os.getenv("SPOTIFY_CLIENT_ID"),
            'client_secret': os.getenv("SPOTIFY_CLIENT_SECRET"),
        })
        return response.json().get('access_token')
    except Exception:
        return None

def fetch_playlist_tracks(playlist_id):
    token = get_spotify_token()
    if not token: return []
    headers = {'Authorization': f'Bearer {token}'}
    url = f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks'
    tracks = []
    
    print(f"Fetching tracks from Spotify...")
    while url:
        res = requests.get(url, headers=headers)
        data = res.json()
        tracks.extend(data.get('items', []))
        url = data.get('next')
    return tracks

def generate_batch_descriptions(songs_batch):
    """
    Sends a batch of songs to Gemini and asks for a JSON response.
    songs_batch: List of dictionaries [{'name': '...', 'artist': '...'}, ...]
    """
    model = genai.GenerativeModel("gemini-2.5-flash")
    
    # Create a clean list for the prompt
    songs_text = "\n".join([f"{i+1}. {s['name']} by {s['artist']}" for i, s in enumerate(songs_batch)])
    
    prompt = f"""
    I have a list of songs. For each song, provide a short, vivid, 1-sentence description of the vibe/setting (e.g., "upbeat city drive" or "rainy coffee shop").
    
    RETURN ONLY RAW JSON. Do not use Markdown blocks.
    The format must be a list of objects, strictly in the same order as the input:
    [
        {{"title": "Song Title", "vibe": "Description here"}},
        ...
    ]

    Songs to process:
    {songs_text}
    """
    
    try:
        response = model.generate_content(prompt)
        clean_text = re.sub(r'```json|```', '', response.text).strip()
        return json.loads(clean_text)
    except Exception as e:
        print(f"Batch Gen Error: {e}")
        return []

def build_vector_store(playlist_id):
    raw_tracks = fetch_playlist_tracks(playlist_id)
    documents = []
    
    # Filter valid tracks first
    valid_tracks = []
    for item in raw_tracks:
        if item and item.get('track'):
            t = item['track']
            valid_tracks.append({
                "name": t.get('name'),
                "artist": t['artists'][0]['name'],
                "url": t['external_urls']['spotify']
            })

    total_tracks = len(valid_tracks)
    print(f"Processing {total_tracks} songs...")

    # --- BATCH PROCESSING ---
    BATCH_SIZE = 10  # Process 10 songs per API call
    
    for i in range(0, total_tracks, BATCH_SIZE):
        batch = valid_tracks[i : i + BATCH_SIZE]
        print(f"Generating vibes for batch {i//BATCH_SIZE + 1} ({len(batch)} songs)...")
        
        # Call Gemini with the batch
        results = generate_batch_descriptions(batch)
        
        # Match results back to the original track data
        for track_data, result in zip(batch, results):
            description = result.get('vibe', f"Music by {track_data['artist']}")
            
            doc = Document(
                page_content=description,
                metadata={
                    "Song_Name": track_data['name'],
                    "Artist": track_data['artist'],
                    "Song_URL": track_data['url']
                }
            )
            documents.append(doc)
            
        time.sleep(1)

    if not documents:
        return None

    print("Building Vector Store...")
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/text-embedding-004",
        google_api_key=os.getenv("GOOGLE_API_KEY")
    )
    
    vector_store = FAISS.from_documents(documents, embeddings)
    return vector_store