import streamlit as st
import requests

API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="Real Estate RAG Assistant", layout="wide")

st.title("Real Estate RAG Assistant")
st.write("Ask questions about uploaded real estate reports.")

with st.sidebar:
    st.header("Controls")
    if st.button("Ingest Documents"):
        try:
            response = requests.post(f"{API_URL}/ingest", timeout=120)
            response.raise_for_status()
            data = response.json()
            st.success(f"Ingestion complete: {data}")
        except Exception as e:
            st.error(f"Ingestion failed: {e}")

question = st.text_input("Enter your question:", "Which markets show strong rental demand?")

if st.button("Ask"):
    try:
        response = requests.post(
            f"{API_URL}/ask",
            json={"question": question},
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()

        st.subheader("Answer")
        st.write(data["answer"])

        st.subheader("Sources")
        for source in data["sources"]:
            with st.expander(f"{source['document_name']} | page {source['page_number']} | chunk {source['chunk_id']}"):
                st.write(f"Hybrid score: {source['hybrid_score']}")
                st.write(f"Vector distance: {source['vector_distance']}")
                st.write(f"Keyword score: {source['keyword_score']}")
                st.write(source["preview"])

    except Exception as e:
        st.error(f"Request failed: {e}")