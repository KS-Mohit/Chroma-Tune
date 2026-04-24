# api.py
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import google.generativeai as genai
import os
from PIL import Image
import io
from dotenv import load_dotenv
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone
from collections import defaultdict
import time
from contextlib import asynccontextmanager

from services import sync_collaborative_playlist, get_song_count, init_indexed_songs, GoogleNativeEmbeddings


load_dotenv()


def describe_image_google(image: Image.Image, api_key: str) -> str:
    """Use Google Gemini for image description."""
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")
    response = model.generate_content([
        "Describe the vibe, mood, and atmosphere of this image in detail for a music playlist.",
        image
    ])
    return response.text


# Collaborative playlist ID
PLAYLIST_ID = "5DYHhVIXo6PhfXqjIlu6rt"

# Admin secret for dangerous endpoints
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "change-this-secret")

# Rate limiting config
RATE_LIMIT_REQUESTS = 10  # requests per window
RATE_LIMIT_WINDOW = 60    # seconds
request_counts = defaultdict(list)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    print("ChromaTune API ready")
    yield
    print("ChromaTune API shutting down")


app = FastAPI(lifespan=lifespan)


def check_rate_limit(client_ip: str) -> bool:
    """Returns True if request is allowed, False if rate limited."""
    now = time.time()
    # Clean old requests outside window
    request_counts[client_ip] = [t for t in request_counts[client_ip] if now - t < RATE_LIMIT_WINDOW]

    if len(request_counts[client_ip]) >= RATE_LIMIT_REQUESTS:
        return False

    request_counts[client_ip].append(now)
    return True


def get_api_key(user_key: str = None) -> tuple[str, bool]:
    """Returns (api_key, is_user_key). Tries server key first, falls back to user key."""
    server_key = os.getenv("GOOGLE_API_KEY")

    # Try server key first
    if server_key:
        try:
            genai.configure(api_key=server_key)
            # Quick test
            model = genai.GenerativeModel("gemini-2.5-flash")
            model.generate_content("test", generation_config={"max_output_tokens": 1})
            return server_key, False
        except Exception as e:
            if "quota" in str(e).lower() or "limit" in str(e).lower() or "exhausted" in str(e).lower():
                print("Server API quota exhausted, checking user key...")
            else:
                # Other error, still try server key
                return server_key, False

    # Fall back to user key
    if user_key:
        return user_key, True

    return None, False

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "ChromaTune API", "playlist_id": PLAYLIST_ID}


@app.get("/stats")
def get_stats():
    """Returns stats about the indexed songs."""
    count = get_song_count()
    return {
        "song_count": count,
        "playlist_id": PLAYLIST_ID
    }


@app.get("/inspect")
def inspect_pinecone(limit: int = 20, secret: str = None):
    """Inspect what's stored in Pinecone (no embeddings needed)."""
    if secret != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Unauthorized")
    try:
        pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        index = pc.Index("chroma-tune")

        # Get index stats
        stats = index.describe_index_stats()

        # List vectors directly from Pinecone (no embedding needed)
        # Use list to get vector IDs, then fetch their metadata
        songs = []
        seen_names = set()
        duplicates = []

        # Fetch vectors by listing IDs
        for ids in index.list(limit=limit):
            if ids:
                fetched = index.fetch(ids=ids)
                for vid, vec in fetched.vectors.items():
                    meta = vec.metadata or {}
                    song_name = meta.get("Song_Name", "Unknown")
                    artist = meta.get("Artist", "Unknown")

                    song_info = {
                        "id": vid,
                        "name": song_name,
                        "artist": artist,
                        "url": meta.get("Song_URL", ""),
                        "vibe": meta.get("text", "")[:100] if meta.get("text") else ""
                    }
                    songs.append(song_info)

                    # Check for duplicates
                    key = f"{song_name}|{artist}"
                    if key in seen_names:
                        duplicates.append(song_info)
                    seen_names.add(key)

        return {
            "total_vectors": stats.total_vector_count,
            "index_dimension": stats.dimension,
            "songs": songs,
            "duplicates_found": len(duplicates),
            "duplicate_songs": duplicates
        }
    except Exception as e:
        import traceback
        return {"error": str(e), "trace": traceback.format_exc()}


@app.get("/api-status")
def api_status():
    """Check if server API keys are configured."""
    server_key = os.getenv("GOOGLE_API_KEY")
    # Just check if key exists - don't waste quota on test calls
    return {"status": "available" if server_key else "unavailable", "needs_user_key": not server_key}


@app.get("/test-embedding")
def test_embedding():
    """Test which embedding model works."""
    server_key = os.getenv("GOOGLE_API_KEY")
    genai.configure(api_key=server_key)
    results = {}

    # Test the available embedding models
    models_to_test = [
        "models/gemini-embedding-001",
        "models/gemini-embedding-2",
    ]

    for model_name in models_to_test:
        try:
            response = genai.embed_content(
                model=model_name,
                content="test"
            )
            results[model_name] = f"OK - {len(response['embedding'])} dimensions"
        except Exception as e:
            results[model_name] = f"FAILED: {str(e)[:80]}"

    return results

@app.post("/clear")
def clear_pinecone(secret: str = None):
    """Clear all vectors from Pinecone and reset local tracking."""
    if secret != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Unauthorized")
    try:
        pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        index = pc.Index("chroma-tune")

        # Delete all vectors
        index.delete(delete_all=True)

        # Clear local tracking file
        import json
        with open("indexed_songs.json", "w") as f:
            json.dump([], f)

        return {"status": "cleared", "message": "All vectors deleted. Run /sync to re-index."}
    except Exception as e:
        return {"error": str(e)}


@app.post("/recreate-index")
def recreate_index(secret: str = None):
    """Delete and recreate Pinecone index with correct dimensions (3072 for gemini-embedding-001)."""
    if secret != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Unauthorized")
    try:
        pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

        # Delete existing index
        try:
            pc.delete_index("chroma-tune")
            import time
            time.sleep(5)  # Wait for deletion
        except Exception as e:
            print(f"Delete index error (may not exist): {e}")

        # Create new index with 3072 dimensions
        pc.create_index(
            name="chroma-tune",
            dimension=3072,
            metric="cosine",
            spec={"serverless": {"cloud": "aws", "region": "us-east-1"}}
        )

        # Clear local tracking
        import json
        with open("indexed_songs.json", "w") as f:
            json.dump([], f)

        return {"status": "success", "message": "Index recreated with 3072 dimensions. Run /sync to index songs."}
    except Exception as e:
        import traceback
        return {"error": str(e), "trace": traceback.format_exc()}


@app.post("/sync")
def sync_playlist():
    """Syncs the collaborative playlist - generates embeddings for any new songs."""
    try:
        result = sync_collaborative_playlist(PLAYLIST_ID)

        if result.get("error"):
            return {
                "status": "error",
                "song_count": result.get("song_count", 0),
                "new_songs": result.get("new_songs", 0),
                "error": result["error"]
            }

        if not result["success"]:
            return {
                "status": "error",
                "song_count": result.get("song_count", 0),
                "new_songs": 0,
                "error": "Failed to sync playlist - check server logs"
            }

        return {
            "status": "success",
            "song_count": result["song_count"],
            "new_songs": result["new_songs"]
        }
    except Exception as e:
        print(f"Sync Error: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "error": str(e)}

@app.post("/search")
async def search_vibe(
    request: Request,
    text: str = Form(None),
    file: UploadFile = File(None),
    user_api_key: str = Form(None),
    provider: str = Form("google")  # kept for compatibility
):
    # Rate limiting
    client_ip = request.client.host
    if not check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please wait a minute.")

    # Get Google API key (server or user-provided)
    api_key, using_user_key = get_api_key(user_api_key)

    if not api_key:
        raise HTTPException(status_code=503, detail="Google API key required. Please provide your API key.")

    # 1. Handle image (if uploaded)
    image_description = ""
    if file:
        try:
            content = await file.read()
            image = Image.open(io.BytesIO(content))
            image_description = describe_image_google(image, api_key)
        except Exception as e:
            print(f"Vision Error: {e}")
            raise HTTPException(status_code=400, detail=f"Image processing failed: {str(e)}")

    # 2. Combine inputs
    full_query = f"{image_description} {text if text else ''}".strip()

    if not full_query:
        raise HTTPException(status_code=400, detail="Please provide text or an image.")

    print(f"Searching for: {full_query}")

    # 3. Search Pinecone
    genai.configure(api_key=api_key)
    embeddings = GoogleNativeEmbeddings(model="models/gemini-embedding-001")

    vector_store = PineconeVectorStore.from_existing_index(
        index_name="chroma-tune",
        embedding=embeddings
    )

    results = vector_store.similarity_search_with_score(full_query, k=5)

    songs = []
    for doc, score in results:
        songs.append({
            "name": doc.metadata.get("Song_Name"),
            "artist": doc.metadata.get("Artist"),
            "url": doc.metadata.get("Song_URL"),
            "score": float(score)
        })

    return {"vibe_analysis": full_query, "songs": songs, "used_user_key": using_user_key}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
