# api.py
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from services import build_vector_store
import google.generativeai as genai
import os
from PIL import Image
import io
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global State to hold the playlist in memory
APP_STATE = {"vector_store": None}

class PlaylistRequest(BaseModel):
    playlist_id: str

@app.get("/")
def read_root():
    return {"status": "Chroma-Tune Backend Running"}

@app.post("/ingest")
def ingest_playlist(request: PlaylistRequest):
    print(f"--- Starting Ingest for {request.playlist_id} ---")
    try:
        store = build_vector_store(request.playlist_id)
        if not store:
            raise HTTPException(status_code=400, detail="Could not build vector store. Check logs.")
            
        APP_STATE["vector_store"] = store
        print("--- Ingest Complete ---")
        return {"status": "success", "message": "Playlist processed successfully"}
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search")
async def search_vibe(
    text: str = Form(None),
    file: UploadFile = File(None)
):
    store = APP_STATE["vector_store"]
    if not store:
        raise HTTPException(status_code=400, detail="No playlist loaded. Please sync a playlist first.")

    # 1. Handle Vision (if image uploaded)
    image_description = ""
    if file:
        try:
            content = await file.read()
            image = Image.open(io.BytesIO(content))
            model = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content(["Describe the vibe and atmosphere of this image in detail.", image])
            image_description = response.text
        except Exception as e:
            print(f"Vision Error: {e}")

    # 2. Combine inputs
    full_query = f"{image_description} {text if text else ''}".strip()
    if not full_query:
         raise HTTPException(status_code=400, detail="Please provide text or an image.")

    print(f"Searching for vibe: {full_query}")

    results = store.similarity_search_with_score(full_query, k=5)
    
    songs = []
    for doc, score in results:
        songs.append({
            "name": doc.metadata["Song_Name"],
            "artist": doc.metadata["Artist"],
            "url": doc.metadata["Song_URL"],
            # FAISS returns L2 distance (lower is better). 
            # We send it as is; frontend will calculate percentage.
            "score": float(score) 
        })
        
    return {"vibe_analysis": full_query, "songs": songs}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)