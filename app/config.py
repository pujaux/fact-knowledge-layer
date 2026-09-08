import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "facts.db")
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads")

# Chunking / cost controls
CHUNK_CHAR_SIZE = 3000          # ~ a page or two of text per Groq call
MAX_FACTS_TOKENS = 2500          # cap output tokens for extraction calls
MAX_RELATION_TOKENS = 250       # cap output tokens for relationship calls
SIMILARITY_THRESHOLD =0.35    # cosine similarity floor to even consider a pair
TOP_K_CANDIDATES_PER_FACT = 5   # only compare each fact to its 5 nearest neighbors

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)
