from app.config import EMBED_MODEL

_model = None


def get_model():
    global _model

    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(EMBED_MODEL)

    return _model


def embed_texts(texts):
    return get_model().encode(texts).tolist()


def embed_query(text):
    return get_model().encode(text).tolist()