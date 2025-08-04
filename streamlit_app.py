import streamlit as st


ingest_page = st.Page("./pages/ingest.py", title="Connect to Your Playlist", icon=":material/add_circle:")
query_page = st.Page("./pages/query.py", title="Find Songs", icon=":material/delete:")

pg = st.navigation([ingest_page, query_page])
st.set_page_config(page_title="Vibe Check", page_icon=":musical_note:", layout="wide")
pg.run()
