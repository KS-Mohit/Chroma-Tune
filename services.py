# services.py
import os
import requests
import time
import json
import re
from typing import List
from dotenv import load_dotenv
import google.generativeai as genai
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))


class GoogleNativeEmbeddings(Embeddings):
    """Custom embeddings using Google's native SDK."""

    def __init__(self, model: str = "models/text-embedding-004"):
        self.model = model

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents."""
        embeddings = []
        for text in texts:
            response = genai.embed_content(model=self.model, content=text)
            embeddings.append(response['embedding'])
        return embeddings

    def embed_query(self, text: str) -> List[float]:
        """Embed a single query."""
        response = genai.embed_content(model=self.model, content=text)
        return response['embedding']

# Initialize Pinecone
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
INDEX_NAME = "chroma-tune"

# Track indexed songs locally
INDEXED_SONGS_FILE = "indexed_songs.json"

# Free tier limits
MAX_SONGS = 500  # Stay well under free tier limits


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


def fetch_playlist_tracks(playlist_id):
    """Fetches all tracks from a Spotify playlist."""
    token = get_spotify_token()
    if not token:
        print("ERROR: Failed to get Spotify token")
        return None

    headers = {'Authorization': f'Bearer {token}'}
    url = f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks'
    tracks = []

    print(f"Fetching tracks from Spotify for playlist {playlist_id}...")
    while url:
        res = requests.get(url, headers=headers)
        print(f"Spotify response: {res.status_code}")
        if res.status_code != 200:
            print(f"Spotify error: {res.text[:200]}")
            return None
        data = res.json()
        tracks.extend(data.get('items', []))
        url = data.get('next')

    print(f"Fetched {len(tracks)} tracks from Spotify")
    return tracks


def get_indexed_song_ids():
    """Returns set of already indexed song IDs."""
    if not os.path.exists(INDEXED_SONGS_FILE):
        return set()
    with open(INDEXED_SONGS_FILE, 'r') as f:
        return set(json.load(f))


def save_indexed_song_ids(song_ids):
    """Saves the set of indexed song IDs."""
    with open(INDEXED_SONGS_FILE, 'w') as f:
        json.dump(list(song_ids), f)


def get_song_count():
    """Returns the number of indexed songs from Pinecone."""
    try:
        # Get actual count from Pinecone
        index = pc.Index(INDEX_NAME)
        stats = index.describe_index_stats()
        return stats.total_vector_count
    except Exception as e:
        print(f"Pinecone stats error: {e}")
        # Fallback to local file
        return len(get_indexed_song_ids())


def init_indexed_songs(playlist_id):
    """
    Initializes indexed_songs.json from existing playlist.
    Call this once if embeddings already exist in Pinecone.
    """
    if os.path.exists(INDEXED_SONGS_FILE):
        return get_song_count()

    raw_tracks = fetch_playlist_tracks(playlist_id)
    if not raw_tracks:
        print("Warning: Could not fetch playlist during init. Skipping.")
        return 0

    song_ids = []
    for item in raw_tracks:
        if item and item.get('track') and item['track'].get('id'):
            song_ids.append(item['track']['id'])

    save_indexed_song_ids(set(song_ids))
    print(f"Initialized {len(song_ids)} songs as already indexed")
    return len(song_ids)


def generate_batch_descriptions(songs_batch):
    """Uses Gemini to generate vibe descriptions for songs."""
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
    except Exception as e:
        print(f"Gemini Error: {e}")
        return []


def sync_collaborative_playlist(playlist_id):
    """
    Syncs the collaborative playlist.
    Only processes NEW songs that haven't been indexed yet.
    """
    # 1. Fetch all tracks from Spotify
    raw_tracks = fetch_playlist_tracks(playlist_id)
    if raw_tracks is None:
        return {"success": False, "song_count": 0, "new_songs": 0, "error": "Failed to fetch from Spotify. Check credentials."}
    if len(raw_tracks) == 0:
        return {"success": False, "song_count": 0, "new_songs": 0, "error": "Playlist is empty or not accessible."}

    # 2. Parse valid tracks
    all_tracks = []
    for item in raw_tracks:
        if item and item.get('track') and item['track'].get('id'):
            t = item['track']
            all_tracks.append({
                "id": t.get('id'),
                "name": t.get('name'),
                "artist": t['artists'][0]['name'] if t.get('artists') else "Unknown",
                "url": t.get('external_urls', {}).get('spotify', '#')
            })

    # 3. Find new songs (not yet indexed)
    indexed_ids = get_indexed_song_ids()
    new_tracks = [t for t in all_tracks if t['id'] not in indexed_ids]

    print(f"Total songs: {len(all_tracks)}, Already indexed: {len(indexed_ids)}, New: {len(new_tracks)}")

    if not new_tracks:
        return {"success": True, "song_count": len(indexed_ids), "new_songs": 0, "error": None}

    # 4. Check free tier limit
    if len(indexed_ids) >= MAX_SONGS:
        return {
            "success": False,
            "song_count": len(indexed_ids),
            "new_songs": 0,
            "error": f"Limit reached ({MAX_SONGS} songs). Free tier limit."
        }

    # Limit new songs to stay under cap
    space_left = MAX_SONGS - len(indexed_ids)
    if len(new_tracks) > space_left:
        print(f"Limiting to {space_left} new songs (free tier)")
        new_tracks = new_tracks[:space_left]

    # 5. Process new songs in batches
    BATCH_SIZE = 10

    try:
        embeddings = GoogleNativeEmbeddings(model="models/gemini-embedding-001")
        vector_store = PineconeVectorStore(index_name=INDEX_NAME, embedding=embeddings)
    except Exception as e:
        print(f"Embedding init error: {e}")
        return {"success": False, "song_count": 0, "new_songs": 0, "error": f"Embedding error: {str(e)}"}

    newly_indexed = []

    try:
        for i in range(0, len(new_tracks), BATCH_SIZE):
            batch = new_tracks[i:i + BATCH_SIZE]
            print(f"Processing batch {i // BATCH_SIZE + 1}: {len(batch)} songs")

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
                newly_indexed.append(track_data['id'])

            if batch_docs:
                vector_store.add_documents(documents=batch_docs, ids=batch_ids)

            time.sleep(1)  # Rate limiting
    except Exception as e:
        print(f"Indexing error: {e}")
        return {"success": False, "song_count": len(indexed_ids), "new_songs": len(newly_indexed), "error": f"Indexing failed: {str(e)}"}

    # 6. Update indexed songs list
    indexed_ids.update(newly_indexed)
    save_indexed_song_ids(indexed_ids)

    return {
        "success": True,
        "song_count": len(indexed_ids),
        "new_songs": len(newly_indexed),
        "error": None
    }
