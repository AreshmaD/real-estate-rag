import requests
import streamlit as st

API_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="Real Estate RAG Assistant",
    layout="wide",
)

st.title("Real Estate RAG Assistant")
st.write("Choose a property and ask questions about its documents.")

with st.sidebar:
    st.header("Controls")

    if st.button("Ingest Documents"):
        try:
            with st.spinner("Processing documents..."):
                response = requests.post(
                    f"{API_URL}/ingest",
                    timeout=120,
                )
                response.raise_for_status()
                data = response.json()

            st.success(f"Ingestion complete: {data}")

        except requests.RequestException as error:
            st.error(f"Ingestion failed: {error}")

property_choice = st.selectbox(
    "Choose a property:",
    ["All documents", "SYN-001", "SYN-002", "SYN-003"],
)

property_id = (
    None if property_choice == "All documents" else property_choice
)

question = st.text_input(
    "Enter your question:",
    "Was the basement water issue at SYN-001 permanently fixed?",
)

if st.button("Ask"):
    if not question.strip():
        st.warning("Please enter a question.")
    else:
        try:
            with st.spinner("Searching documents and preparing an answer..."):
                response = requests.post(
                    f"{API_URL}/ask",
                    json={
                        "question": question.strip(),
                        "property_id": property_id,
                    },
                    timeout=180,
                )
                response.raise_for_status()
                data = response.json()

            st.subheader("Answer")
            st.write(data["answer"])

            st.subheader("Sources")

            if not data["sources"]:
                st.info("No supporting sources were returned.")

            for source in data["sources"]:
                page = source.get("page_number")
                page_label = page if page is not None else "N/A"

                label = (
                    f"{source['document_name']} | "
                    f"page {page_label} | "
                    f"chunk {source['chunk_id']}"
                )

                with st.expander(label, expanded=True):
                    st.write(source["preview"])

                    st.caption(
                        f"Hybrid score: {source['hybrid_score']} · "
                        f"Vector distance: {source['vector_distance']} · "
                        f"Keyword score: {source['keyword_score']}"
                    )

        except requests.RequestException as error:
            st.error(f"Request failed: {error}")