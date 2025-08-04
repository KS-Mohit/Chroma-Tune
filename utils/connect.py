# utils/connect.py

import streamlit as st
import google.generativeai as genai
from langchain_google_genai import GoogleGenerativeAIEmbeddings

@st.cache_resource
def load_gemini_models():
    """
    Configures and initializes the Google Gemini models for text, vision,
    and embeddings using the API key from secrets.
    """
    # Configure the generative AI library with the API key
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

    # Initialize the model for text generation (describing songs)
    text_model = genai.GenerativeModel("gemini-1.5-flash")
    
    # Initialize the model for image analysis (understanding the vibe)
    vision_model = genai.GenerativeModel("gemini-1.5-flash") # This model can handle both text and images
    
    return text_model, vision_model

@st.cache_resource
def load_embedding_model():
    """
    Initializes the LangChain embedding model from Google.
    This will be used by FAISS to create vectors from text.
    """
    # The task_type is 'retrieval_document' for storing docs and 'retrieval_query' for searching
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/embedding-001", 
        google_api_key=st.secrets["GOOGLE_API_KEY"]
    )
    return embeddings

def initialize_connections():
    """
    Initializes all necessary clients and models and loads them into
    the Streamlit session state. Also prepares placeholders for our
    in-memory vector store (FAISS) and playlist tracker.
    """
    # Load the Gemini models for text and vision
    if "gemini_text_model" not in st.session_state or "gemini_vision_model" not in st.session_state:
        text_model, vision_model = load_gemini_models()
        st.session_state["gemini_text_model"] = text_model
        st.session_state["gemini_vision_model"] = vision_model

    # Load the embedding model for vectorization
    if "embedding_model" not in st.session_state:
        st.session_state["embedding_model"] = load_embedding_model()

    # This will hold our FAISS vector store in memory
    if "vector_store" not in st.session_state:
        st.session_state["vector_store"] = None

    # This will track the current playlist ID in memory
    if "current_pid" not in st.session_state:
        st.session_state["current_pid"] = None