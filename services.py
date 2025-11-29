# services.py
import os
import requests
import time
import json
import re
from dotenv import load_dotenv
import google.generativeai as genai
from langchain_core.documents import Document
from langchain_pinecone import PineconeVectorStore
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from pinecone import Pinecone

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Initialize Pinecone
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
INDEX_NAME = "chroma-tune"

# Local "Database" file for playlists
DB_FILE = "playlists.json"

def get_spotify_token():
    try:
        response = requests.post('https://accounts.spotify.com/api/token', {
            'grant_type': 'client_credentials',
            'client_id': os.getenv("SPOTIFY_CLIENT_ID"),
            'client_secret': os.getenv("SPOTIFY_CLIENT_SECRET"),
        })
        return response.json().get('access_token')
    except Exception as e:
        print(f"Auth Error: {e}")
        return None

def get_playlist_metadata(playlist_id):
    """Fetches Name, Image, and URL for a playlist."""
    token = get_spotify_token()
    if not token: return None
    
    headers = {'Authorization': f'Bearer {token}'}
    url = f'https://api.spotify.com/v1/playlists/{playlist_id}'
    
    try:
        res = requests.get(url, headers=headers)
        if res.status_code != 200: return None
        data = res.json()
        
        return {
            "id": playlist_id,
            "name": data.get("name", "Unknown Playlist"),
            "url": data.get("external_urls", {}).get("spotify", "#"),
            "image": data.get("images", [{}])[0].get("url", "")
        }
    except Exception as e:
        print(f"Metadata Error: {e}")
        return None

def save_playlist_to_db(metadata):
    """Saves the playlist details to a local JSON file."""
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, 'w') as f: json.dump([], f)
    
    with open(DB_FILE, 'r') as f:
        playlists = json.load(f)
    
    # Check if exists, update if so
    for i, p in enumerate(playlists):
        if p['id'] == metadata['id']:
            playlists[i] = metadata
            with open(DB_FILE, 'w') as f: json.dump(playlists, f)
            return

    # Else append
    playlists.append(metadata)
    with open(DB_FILE, 'w') as f: json.dump(playlists, f)

def get_all_playlists():
    """Returns list of all ingested playlists."""
    if not os.path.exists(DB_FILE): return []
    with open(DB_FILE, 'r') as f: return json.load(f)

def fetch_playlist_tracks(playlist_id):
    token = get_spotify_token()
    if not token: return []
    headers = {'Authorization': f'Bearer {token}'}
    url = f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks'
    tracks = []
    
    print(f"Fetching tracks from Spotify...")
    while url:
        res = requests.get(url, headers=headers)
        if res.status_code != 200: break
        data = res.json()
        tracks.extend(data.get('items', []))
        url = data.get('next')
    return tracks

def generate_batch_descriptions(songs_batch):
    model = genai.GenerativeModel("gemini-2.5-flash")
    songs_text = "\n".join([f"{i+1}. {s['name']} by {s['artist']}" for i, s in enumerate(songs_batch)])
    
    prompt = f"""
    I have a list of songs. For each song, provide a short, vivid, 1-sentence description of the vibe/setting.
    RETURN ONLY RAW JSON. Format: [{{"title": "Song Title", "vibe": "Description"}}]
    Songs:
    {songs_text}
    """
    try:
        response = model.generate_content(prompt)
        clean_text = re.sub(r'```json|```', '', response.text).strip()
        return json.loads(clean_text)
    except Exception:
        return []

def build_vector_store(playlist_id):
    # 1. Fetch Metadata First
    meta = get_playlist_metadata(playlist_id)
    if not meta: return False
    
    print(f"Ingesting Playlist: {meta['name']}")

    # 2. Process Songs (Normal Flow)
    raw_tracks = fetch_playlist_tracks(playlist_id)
    valid_tracks = []
    for item in raw_tracks:
        if item and item.get('track'):
            t = item['track']
            valid_tracks.append({
                "id": t.get('id'),
                "name": t.get('name'),
                "artist": t['artists'][0]['name'],
                "url": t['external_urls']['spotify']
            })

    total_tracks = len(valid_tracks)
    BATCH_SIZE = 10 
    
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/text-embedding-004",
        google_api_key=os.getenv("GOOGLE_API_KEY")
    )
    vector_store = PineconeVectorStore(index_name=INDEX_NAME, embedding=embeddings)

    # NOTE: REMOVED delete_all=True here to allow combining!

    for i in range(0, total_tracks, BATCH_SIZE):
        batch = valid_tracks[i : i + BATCH_SIZE]
        results = generate_batch_descriptions(batch)
        
        batch_docs = []
        batch_ids = []
        
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
            batch_docs.append(doc)
            batch_ids.append(track_data['id'])
            
        if batch_docs:
            vector_store.add_documents(documents=batch_docs, ids=batch_ids)
        time.sleep(1)

    # 3. Save to Local DB only after success
    save_playlist_to_db(meta)
    return True