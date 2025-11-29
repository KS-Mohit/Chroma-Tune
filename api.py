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
from langchain_pinecone import PineconeVectorStore
from langchain_google_genai import GoogleGenerativeAIEmbeddings

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

class PlaylistRequest(BaseModel):
    playlist_id: str

@app.get("/")
def read_root():
    return {"status": "Chroma-Tune API (Pinecone Edition)"}

@app.post("/ingest")
def ingest_playlist(request: PlaylistRequest):
    print(f"--- Starting Cloud Ingest for {request.playlist_id} ---")
    try:
        success = build_vector_store(request.playlist_id)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to process playlist")
            
        return {"status": "success", "message": "Playlist synced to Cloud Vector Store"}
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search")
async def search_vibe(
    text: str = Form(None),
    file: UploadFile = File(None)
):
    # 1. Handle Vision
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

    full_query = f"{image_description} {text if text else ''}".strip()
    if not full_query:
         raise HTTPException(status_code=400, detail="Please provide text or an image.")

    print(f"Searching Pinecone for: {full_query}")

    # 2. Connect to Pinecone Index 
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/text-embedding-004", 
        google_api_key=os.getenv("GOOGLE_API_KEY")
    )
    
    vector_store = PineconeVectorStore.from_existing_index(
        index_name="chroma-tune",
        embedding=embeddings
    )

    # 3. Perform Search
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