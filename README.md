# Chroma-Tune: AI-Powered Music Discovery

Struggling to find the perfect soundtrack for every moment? Chroma-Tune is a smart music discovery app that curates song recommendations based on your vibe. Simply upload an image or describe a scene, and let our AI find the perfect music to match.

<!-- ![App Preview](https://i.imgur.com/Lz0aJ1g.png) -->

---

## Overview

This application uses a multi-modal AI approach to understand the "vibe" of an image or text description and then searches through a Spotify playlist to find songs with a similar mood. It's a powerful demonstration of Retrieval-Augmented Generation (RAG) that you can run entirely on your own machine.

### Core Technologies
- **Frontend:** [Streamlit](https://streamlit.io/)
- **Orchestration Framework:** [LangChain](https://www.langchain.com/)
- **AI & Language Models:** [Google Gemini API](https://ai.google.dev/) (Free Tier)
- **Vector Search & Storage:** [Facebook AI Similarity Search (FAISS)](https://faiss.ai/) (In-Memory)
- **Music Data:** [Spotify Web API](https://developer.spotify.com/documentation/web-api)

---

## Features

- ** Image-to-Music:** Upload a photo or use your camera, and the AI will analyze the scene's mood, color, and ambiance to recommend songs.
- ** Text-to-Music:** Provide a text description of a setting (e.g., "a rainy day, perfect for studying") to get matching music.
- ** Dynamic Playlist Analysis:** Connect any Spotify playlist. The app fetches the songs, uses an LLM to generate a rich "vibe" description for each track, and builds a searchable in-memory vector database.
- ** Runs Locally:** No complex cloud database setup required. The entire vector store is built and held in memory while the app is running.

---

## How to Run Locally

### Prerequisites

Before you begin, make sure you have the following:
1.  **Python 3.9+** installed on your machine.
2.  A **Google API Key** from the [Google AI Studio](https://aistudio.google.com/app).
3.  A **Spotify Account** and a **Spotify App** created in the [Developer Dashboard](https://developer.spotify.com/dashboard) to get your Client ID and Secret.

### Setup Instructions

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/KS-Mohit/Chroma-Tune.git](https://github.com/KS-Mohit/Chroma-Tune.git)
    cd Chroma-Tune
    ```

2.  **Create a virtual environment:**
    ```bash
    python -m venv .venv
    .\.venv\Scripts\activate
    ```

3.  **Install the required packages:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Create your secrets file:**
    - Make a copy of `example.secrets.toml` and rename it to `secrets.toml`.
    - Open `secrets.toml` and add your actual API keys:
      ```toml
      # secrets.toml

      # Google AI API Key
      GOOGLE_API_KEY = "your_google_api_key_here"

      # Spotify API Credentials
      SPOTIFY_CLIENT_ID = "your_spotify_client_id"
      SPOTIFY_CLIENT_SECRET = "your_spotify_client_secret"
      ```

### Run the Application

Once setup is complete, run the following command in your terminal:
```bash
streamlit run streamlit_app.py
```
Your browser will automatically open with the Chroma-Tune application running.

---

## Architecture Flow

### 1. Ingestion (Connecting a Playlist)
- The user provides a Spotify Playlist ID.
- The app fetches all tracks from the playlist using the Spotify API.
- For each song, the **Google Gemini** model generates a rich text description of its "vibe" and appropriate settings.
- These descriptions are converted into vector embeddings and loaded into an in-memory **FAISS** vector store, ready for searching.

### 2. Querying (Finding Songs)
- The user uploads an image or writes a text description of their current vibe.
- The **Google Gemini Vision** model analyzes the input and generates a detailed text description of the scene.
- This description is used to perform a vector similarity search against the FAISS store.
- The top 5 songs with the most similar "vibe" descriptions are returned and displayed to the user with links to Spotify.
