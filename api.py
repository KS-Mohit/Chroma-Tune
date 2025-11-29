# api.py
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import google.generativeai as genai
import os
from PIL import Image
import io
from dotenv import load_dotenv
from langchain_pinecone import PineconeVectorStore
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# Import functions from our updated services.py
from services import build_vector_store, get_all_playlists

# Load env vars
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

app = FastAPI()

# Allow frontend connection
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, replace * with your Vercel URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PlaylistRequest(BaseModel):
    playlist_id: str

@app.get("/")
def read_root():
    return {"status": "Chroma-Tune API (Pinecone Edition)"}

@app.get("/playlists")
def get_playlists():
    """Returns the list of currently active playlists."""
    return get_all_playlists()

@app.post("/ingest")
def ingest_playlist(request: PlaylistRequest):
    print(f"--- Starting Ingest for {request.playlist_id} ---")
    try:
        # 1. Process the playlist (Fetch -> Describe -> Pinecone)
        success = build_vector_store(request.playlist_id)
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to process playlist. Check ID or Privacy settings.")
        
        # 2. Get the updated list of playlists to send back to UI
        updated_list = get_all_playlists()
        
        return {"status": "success", "playlists": updated_list}
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search")
async def search_vibe(
    text: str = Form(None),
    file: UploadFile = File(None)
):
    # 1. Handle Vision (if image uploaded)
    image_description = ""
    if file:
        try:
            content = await file.read()
            image = Image.open(io.BytesIO(content))
            # Use Vision model to get a vibe description
            model = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content(["Describe the vibe, mood, and atmosphere of this image in detail for a music playlist.", image])
            image_description = response.text
        except Exception as e:
            print(f"Vision Error: {e}")

    # 2. Combine inputs (Text + Image)
    full_query = f"{image_description} {text if text else ''}".strip()
    
    if not full_query:
         raise HTTPException(status_code=400, detail="Please provide text or an image.")

    print(f"Searching Pinecone for: {full_query}")

    # 3. Connect to Pinecone Index 
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/text-embedding-004", 
        google_api_key=os.getenv("GOOGLE_API_KEY")
    )
    
    # We use 'from_existing_index' because we just want to read, not write
    vector_store = PineconeVectorStore.from_existing_index(
        index_name="chroma-tune",
        embedding=embeddings
    )

    # 4. Perform Search
    results = vector_store.similarity_search_with_score(full_query, k=5)
    
    songs = []
    for doc, score in results:
        songs.append({
            "name": doc.metadata.get("Song_Name"),
            "artist": doc.metadata.get("Artist"),
            "url": doc.metadata.get("Song_URL"),
            "score": float(score) 
        })
        
    return {"vibe_analysis": full_query, "songs": songs}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)