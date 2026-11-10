import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import URL

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

DB_URL = URL.create(
    drivername="postgresql+psycopg",
    username=os.environ["POSTGRES_USER"],
    password=os.environ["POSTGRES_PASSWORD"],
    host=os.getenv("DB_HOST", "127.0.0.1"),
    port=int(os.getenv("DB_PORT", "55432")),
    database=os.environ["POSTGRES_DB"],
)

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
LLM_MODEL = "gpt-oss:20b"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100
TOP_K = 5
DATA_DIR = "data/raw"
