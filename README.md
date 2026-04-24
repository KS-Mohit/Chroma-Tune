# ChromaTune: AI-Powered Music Discovery

Struggling to find the perfect soundtrack for the moment? ChromaTune is a modern, full-stack AI application that curates song recommendations based on your exact "vibe."

Upload an image or describe a scene, and our multi-modal AI searches a community-curated playlist to find the perfect music match.

---

## Overview

This application uses a multi-modal AI approach to understand the "vibe" of an image or text description and then searches through a collaborative Spotify playlist to find songs with a similar mood. It's a powerful demonstration of Retrieval-Augmented Generation (RAG) with a beautiful landing page and seamless user experience.

### Core Technologies
- **Frontend:** Next.js 14 (React), Tailwind CSS, Shadcn UI, Framer Motion
- **Backend:** FastAPI (Python)
- **AI Models:** Google Gemini 2.5 Flash, OpenAI GPT-4o, Anthropic Claude (multi-provider support)
- **Embeddings:** Google Gemini Embedding (3072 dimensions)
- **Vector Database:** Pinecone (Serverless)
- **Music Data:** Spotify Web API
- **Infrastructure:** Docker & Docker Compose

---

## Features

- **Landing Page:** Beautiful hero section with feature highlights and smooth navigation
- **Image-to-Music:** Upload or drag-drop an image - AI analyzes the scene's mood to recommend songs
- **Text-to-Music:** Describe a setting (e.g., "rainy day in a coffee shop") to get matching music
- **Collaborative Playlist:** One shared community playlist - anyone can add songs via Spotify
- **Multi-Provider Support:** Use Google AI, OpenAI, or Anthropic API keys for image analysis
- **Rate Limiting:** Built-in protection (10 requests/minute per IP)
- **API Key Fallback:** When server quota is exceeded, users can provide their own keys

---

## How It Works

### For Users
1. Visit the landing page and click "Try It Now"
2. Type a vibe description or upload an image
3. Get AI-matched song recommendations instantly
4. Click any song to open it in Spotify

### Adding Songs to the Playlist
1. Click "Add Songs" to open the collaborative Spotify playlist
2. Add songs directly in Spotify
3. Click the sync button to index new songs with AI

---

## How to Run Locally

### Prerequisites

1. **Docker Desktop** installed and running
2. API Keys for:
   - **Google AI Studio** - [Get Key](https://aistudio.google.com/apikey)
   - **Spotify Developer** - [Dashboard](https://developer.spotify.com/dashboard)
   - **Pinecone** - [Console](https://console.pinecone.io)

### Setup Instructions

1. **Clone the repository:**
    ```bash
    git clone https://github.com/KS-Mohit/ChromaTune.git
    cd ChromaTune
    ```

2. **Create your environment variables:**
    ```bash
    # .env
    GOOGLE_API_KEY="your_google_key"
    SPOTIFY_CLIENT_ID="your_spotify_client_id"
    SPOTIFY_CLIENT_SECRET="your_spotify_client_secret"
    PINECONE_API_KEY="your_pinecone_key"
    ```

3. **Run with Docker Compose:**
    ```bash
    docker-compose up --build
    ```

4. **Access the App:**
    ```
    http://localhost:3000
    ```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/stats` | GET | Get indexed song count |
| `/sync` | POST | Sync playlist - index new songs |
| `/search` | POST | Search by text/image |
| `/inspect` | GET | View Pinecone contents |
| `/clear` | POST | Clear all vectors |
| `/recreate-index` | POST | Recreate Pinecone index |
| `/api-status` | GET | Check API availability |
| `/test-embedding` | GET | Test embedding models |

---

## Architecture Flow

### 1. Syncing (Indexing Songs)
- Collaborative Spotify playlist is fetched via Spotify API
- Google Gemini generates vibe descriptions for each song
- Descriptions are embedded using `gemini-embedding-001` (3072 dimensions)
- Vectors are upserted into Pinecone with Spotify track IDs (no duplicates)
- Local tracking file prevents re-processing existing songs

### 2. Searching (The Vibe Check)
- User uploads an image and/or types a description
- For images: Gemini/GPT-4o/Claude analyzes the scene
- Combined query is embedded into a vector
- Pinecone performs cosine similarity search
- Top 5 matching songs returned with similarity scores

---

## Multi-Provider Support

Users can bring their own API keys for image analysis:

| Provider | Model | Use Case |
|----------|-------|----------|
| Google AI | Gemini 2.5 Flash | Text search + Image analysis |
| OpenAI | GPT-4o | Image analysis |
| Anthropic | Claude Sonnet | Image analysis |

Keys are stored locally in the browser (never sent to server for storage).

---

## Free Tier Limits

- **Songs:** Max 500 indexed (Pinecone free tier)
- **Rate Limit:** 10 requests/minute per IP
- **Providers:** Users can add their own API keys when server quota is exceeded

---

## Project Structure

```
ChromaTune/
├── frontend/                # Next.js frontend
│   └── src/app/
│       ├── page.tsx        # Landing page
│       └── app/page.tsx    # Main app
├── api.py                  # FastAPI backend
├── services.py             # Spotify, Gemini, Pinecone logic
├── docker-compose.yml      # Container orchestration
├── requirements.txt        # Python dependencies
└── .env                    # Environment variables
```

---

## Contributing

1. Fork the repository
2. Add songs to the collaborative playlist
3. Submit issues or pull requests

---

## License

MIT License - Feel free to use and modify!
