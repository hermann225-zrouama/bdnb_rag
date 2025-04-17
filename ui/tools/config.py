# config.py
"""
Fichier de configuration centralisant les constantes du projet BDNB Assistant.
"""
import os

# Configuration de Qdrant (Vector Store)
API_HOST = "0.0.0.0"
API_PORT = 8000
API_HOST = os.getenv("API_HOST", API_HOST)
API_PORT = int(os.getenv("API_PORT", API_PORT))