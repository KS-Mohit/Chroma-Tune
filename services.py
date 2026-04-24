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
        client_id = os.getenv("SPOTIFY_CLIENT_ID")
        client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        print(f"[Spotify Auth] Client ID: {client_id[:8]}... Secret: {'***' if client_secret else 'MISSING'}")

        response = requests.post('https://accounts.spotify.com/api/token', {
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': client_secret,
        })
        data = response.json()

        if 'access_token' in data:
            print(f"[Spotify Auth] Token obtained successfully")
            return data['access_token']
        else:
            print(f"[Spotify Auth] Failed: {data}")
            return None
    except Exception as e:
        print(f"[Spotify Auth] Error: {e}")
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

    print(f"[Spotify] Fetching playlist {playlist_id}...")
    while url:
        res = requests.get(url, headers=headers)
        print(f"[Spotify] Response: {res.status_code}")
        if res.status_code != 200:
            try:
                error_data = res.json()
                error_msg = error_data.get('error', {}).get('message', res.text[:200])
                error_reason = error_data.get('error', {}).get('reason', 'unknown')
                print(f"[Spotify] Error: {error_msg}")
                print(f"[Spotify] Reason: {error_reason}")
                if res.status_code == 403:
                    print(f"[Spotify] 403 = Premium required OR playlist is private/restricted")
                elif res.status_code == 401:
                    print(f"[Spotify] 401 = Bad credentials")
                elif res.status_code == 404:
                    print(f"[Spotify] 404 = Playlist not found")
            except:
                print(f"[Spotify] Raw error: {res.text[:300]}")
            return None
        data = res.json()
        tracks.extend(data.get('items', []))
        url = data.get('next')

    print(f"Fetched {len(tracks)} tracks from Spotify")
    return tracks


def fetch_audio_features(track_ids):
    """Fetches audio features for multiple tracks (max 100 per request)."""
    token = get_spotify_token()
    if not token:
        return {}

    headers = {'Authorization': f'Bearer {token}'}
    features = {}

    # Spotify allows max 100 IDs per request
    for i in range(0, len(track_ids), 100):
        batch_ids = track_ids[i:i + 100]
        url = f'https://api.spotify.com/v1/audio-features?ids={",".join(batch_ids)}'

        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            data = res.json()
            for feature in data.get('audio_features', []):
                if feature:
                    features[feature['id']] = {
                        'energy': feature.get('energy', 0),
                        'tempo': feature.get('tempo', 0),
                        'danceability': feature.get('danceability', 0),
                        'valence': feature.get('valence', 0),  # happiness
                        'acousticness': feature.get('acousticness', 0),
                        'instrumentalness': feature.get('instrumentalness', 0)
                    }
        else:
            print(f"Audio features error: {res.status_code}")

    return features


def describe_audio_features(features):
    """Convert audio features to human-readable description."""
    if not features:
        return ""

    parts = []

    # Energy
    energy = features.get('energy', 0)
    if energy > 0.8:
        parts.append("high-energy")
    elif energy > 0.5:
        parts.append("moderate energy")
    else:
        parts.append("calm and relaxed")

    # Tempo
    tempo = features.get('tempo', 0)
    if tempo > 140:
        parts.append("fast-paced")
    elif tempo > 100:
        parts.append("upbeat tempo")
    else:
        parts.append("slow tempo")

    # Valence (happiness)
    valence = features.get('valence', 0)
    if valence > 0.7:
        parts.append("happy and positive")
    elif valence > 0.4:
        parts.append("neutral mood")
    else:
        parts.append("melancholic or dark")

    # Danceability
    dance = features.get('danceability', 0)
    if dance > 0.7:
        parts.append("very danceable")
    elif dance > 0.5:
        parts.append("groovy")

    # Acousticness
    acoustic = features.get('acousticness', 0)
    if acoustic > 0.7:
        parts.append("acoustic")

    # Instrumentalness
    instrumental = features.get('instrumentalness', 0)
    if instrumental > 0.5:
        parts.append("instrumental")

    return ", ".join(parts)


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


def generate_batch_descriptions(songs_batch, audio_features_map):
    """Uses Gemini to generate vibe descriptions for songs, enhanced with audio features."""
    model = genai.GenerativeModel("gemini-2.5-flash")

    # Build song text with audio features
    songs_lines = []
    for i, s in enumerate(songs_batch):
        features = audio_features_map.get(s['id'], {})
        feature_desc = describe_audio_features(features)
        if feature_desc:
            songs_lines.append(f"{i+1}. {s['name']} by {s['artist']} ({feature_desc})")
        else:
            songs_lines.append(f"{i+1}. {s['name']} by {s['artist']}")

    songs_text = "\n".join(songs_lines)

    prompt = f"""
    I have a list of songs with their audio characteristics. For each song, provide a short, vivid, 1-sentence description of the vibe/setting that matches both the song and its audio profile.
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

    # 5. Fetch audio features for all new tracks
    print("Fetching audio features from Spotify...")
    new_track_ids = [t['id'] for t in new_tracks]
    audio_features_map = fetch_audio_features(new_track_ids)
    print(f"Got audio features for {len(audio_features_map)} tracks")

    # 6. Process new songs in batches
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

            results = generate_batch_descriptions(batch, audio_features_map)

            batch_docs = []
            batch_ids = []

            for track_data, result in zip(batch, results):
                description = result.get('vibe', f"Music by {track_data['artist']}")
                features = audio_features_map.get(track_data['id'], {})

                doc = Document(
                    page_content=description,
                    metadata={
                        "Song_Name": track_data['name'],
                        "Artist": track_data['artist'],
                        "Song_URL": track_data['url'],
                        "energy": features.get('energy', 0),
                        "tempo": features.get('tempo', 0),
                        "danceability": features.get('danceability', 0),
                        "valence": features.get('valence', 0),
                        "acousticness": features.get('acousticness', 0)
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

    # 7. Update indexed songs list
    indexed_ids.update(newly_indexed)
    save_indexed_song_ids(indexed_ids)

    return {
        "success": True,
        "song_count": len(indexed_ids),
        "new_songs": len(newly_indexed),
        "error": None
    }
