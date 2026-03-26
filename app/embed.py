from sentence_transformers import SentenceTransformer
from app.config import EMBED_MODEL

_model = None


def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBED_MODEL)
    return _model


def embed_texts(texts):
    model = get_model()
    return model.encode(texts).tolist()


def embed_query(text):
    model = get_model()
    return model.encode(text).tolist()