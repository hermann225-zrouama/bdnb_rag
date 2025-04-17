# config.py
"""
Fichier de configuration centralisant les constantes du projet BDNB Assistant.
"""
import os

# Configuration de Qdrant (Vector Store)
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
COLLECTION_NAME = "bdnb_buildings"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
LLM_MODEL = "llama3.2"
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0
REDIS_TTL = 3600  # Durée de vie du cache en secondes (1 heure)
SQLITE_DB_PATH = "bdnb.db"
DATA_DIR = "data"
CONSOLIDATED_PARQUET = "bdnb_consolidated.parquet"
STORAGE_DIR = "storage"
API_HOST = "0.0.0.0"
API_PORT = 8000
BATCH_SIZE = 1000  # Taille des lots pour l'indexation
SIMILARITY_TOP_K = 5  # Nombre de documents récupérés par requête RAG

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QDRANT_HOST = os.getenv("QDRANT_HOST", QDRANT_HOST)
QDRANT_PORT = int(os.getenv("QDRANT_PORT", QDRANT_PORT))
COLLECTION_NAME = os.getenv("COLLECTION_NAME", COLLECTION_NAME)
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", EMBEDDING_MODEL)
LLM_MODEL = os.getenv("LLM_MODEL", LLM_MODEL)
REDIS_HOST = os.getenv("REDIS_HOST", REDIS_HOST)
REDIS_PORT = int(os.getenv("REDIS_PORT", REDIS_PORT))
REDIS_DB = int(os.getenv("REDIS_DB", REDIS_DB))

DATA_DIR = os.path.join(PROJECT_ROOT, os.getenv("DATA_DIR", DATA_DIR))  # Le répertoire des données
SQLITE_DB_PATH = os.path.join(DATA_DIR, os.getenv("SQLITE_DB_PATH", SQLITE_DB_PATH))
CONSOLIDATED_PARQUET = os.path.join(DATA_DIR, os.getenv("CONSOLIDATED_PARQUET", CONSOLIDATED_PARQUET))
STORAGE_DIR = os.path.join(PROJECT_ROOT, os.getenv("STORAGE_DIR", STORAGE_DIR))  # Le répertoire de stockage
API_HOST = os.getenv("API_HOST", API_HOST)
API_PORT = int(os.getenv("API_PORT", API_PORT))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", BATCH_SIZE))
SIMILARITY_TOP_K = int(os.getenv("SIMILARITY_TOP_K", SIMILARITY_TOP_K))