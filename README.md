# BDNB Assistant

**BDNB Assistant** est une application permettant d'interroger la Base de Données Nationale des Bâtiments (BDNB) en langage naturel.  
Elle combine une approche hybride de **RAG (Retrieval-Augmented Generation)** pour les questions descriptives et des **requêtes SQL** pour les analyses quantitatives.

L'application comprend :
- Une **API FastAPI** pour les requêtes programmatiques.
- Une **interface Streamlit** conviviale pour les utilisateurs non-techniques, avec filtres interactifs et visualisations.
- Une architecture entièrement **containerisée avec Docker**, utilisant :
  - **Qdrant** pour le stockage vectoriel.
  - **Redis** pour le cache.
  - **Ollama** pour le modèle de langage.
  - **SQLite** pour les données consolidées.

---

## ✨ Fonctionnalités

- **Requêtes en langage naturel**  
  Posez des questions comme :
  - "Quels sont les bâtiments résidentiels classés F ou G dans le département 93 ?"
  - "Quelle est la surface moyenne des bâtiments tertiaires avant 1975 dans le Rhône ?"

- **Approche hybride**  
  Combine RAG (via Qdrant et LlamaIndex) pour les descriptions et SQL (via SQLite) pour les calculs agrégés.

- **Cache Redis**  
  Optimise les performances en stockant les réponses fréquentes.

- **Interface Streamlit**  
  Interface web avec filtres (département, type de bâtiment, DPE, surface, étages) et visualisations (tableaux, graphiques Plotly).

- **Reproductibilité**  
  Entièrement containerisé avec Docker Compose.

- **Feature engineering**  
  Génère des caractéristiques comme surface estimée, type de bâtiment, passoires thermiques, et localisation.

---

## 🏗️ Architecture

Le projet est modulaire avec les composants suivants :

- `consolidate.py` : Télécharge et échantillonne les données BDNB depuis [https://bdnb.io](https://bdnb.io)
- `feature_eng.py` : Génère des features (surface, DPE, type de bâtiment, etc.)
- `indexer.py` : Indexe les données dans Qdrant avec LlamaIndex, shardées par département.
- `database.py` : Gère la base SQLite pour les requêtes quantitatives.
- `cache.py` : Implémente un cache Redis.
- `main.py` : API FastAPI.
- `ui.py` : Interface Streamlit.
- `logger.py` : Logging structuré.
- `config.py` : Centralise les configurations.

---

## 🧰 Prérequis

- **Docker** : Docker Desktop (Windows/Mac) ou Docker Engine (Linux)
- **Docker Compose**
- **Espace disque** : Environ 5 Go
- **RAM** : Minimum 16 Go recommandé

---

## ⚙️ Installation

### 1. Cloner le dépôt

```bash
git clone https://github.com/votre-utilisateur/bdnb-assistant.git
cd bdnb-assistant
```

> Remplacez l’URL par celle de votre dépôt si nécessaire.

---

### 2. Configurer les variables d’environnement

```bash
cp .env.example .env
```

Contenu typique de `.env` :

```env
API_HOST=0.0.0.0
API_PORT=8000
QDRANT_HOST=qdrant
QDRANT_PORT=6333
REDIS_HOST=redis
REDIS_PORT=6379
LLM_MODEL=llama3
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
COLLECTION_NAME=bdnb_buildings
SQLITE_DB_PATH=/app/data/bdnb.db
CONSOLIDATED_PARQUET=/app/data/bdnb_consolidated_93.parquet
STORAGE_DIR=/app/storage
BATCH_SIZE=1000
SIMILARITY_TOP_K=5
DATA_DIR=/app/data
REDIS_TTL=3600
```

---

### 3. Initialiser les données

```bash
chmod +x init.sh
./init.sh
```

Ce script exécute :
- `consolidate.py`
- `feature_eng.py`
- `indexer.py`

> Assurez-vous que Qdrant est lancé (`docker run -d -p 6333:6333 qdrant/qdrant`) avant `indexer.py`.

---

### 4. Lancer les services

```bash
docker-compose up --build
```

Services accessibles :
- API FastAPI : [http://localhost:8000](http://localhost:8000)
- Interface Streamlit : [http://localhost:8501](http://localhost:8501)
- Qdrant : `localhost:6333`
- Redis : `localhost:6379`
- Ollama : `localhost:11434`

---

### 5. Utiliser l'application

- **Interface Streamlit** : [http://localhost:8501](http://localhost:8501)
- Posez des questions en langage naturel.
- Utilisez les filtres dans la barre latérale.

**Exemple d’appel API :**

```bash
curl -X POST "http://localhost:8000/chat" \
     -H "Content-Type: application/json" \
     -d '{"message": "Liste des bâtiments résidentiels de plus de 1000 m² dans le département 93"}'
```

---

### 6. Arrêter les services

```bash
docker-compose down
```

---

## 📁 Structure du projet

```plaintext
bdnb-assistant/
├── data/                   # Données BDNB, SQLite, et logs
├── storage/                # Index LlamaIndex
├── qdrant_data/            # Données persistantes Qdrant
├── redis_data/             # Données persistantes Redis
├── ollama_data/            # Modèles Ollama
├── cache.py
├── config.py
├── consolidate.py
├── database.py
├── feature_eng.py
├── indexer.py
├── logger.py
├── main.py
├── ui.py
├── Dockerfile.api
├── Dockerfile.ui
├── pyproject.toml
├── docker-compose.yml
├── .env
├── .dockerignore
├── init.sh
└── README.md
```

---

## 📦 Dépendances

Gérées via `uv` et définies dans `pyproject.toml`. Principaux packages :

- `polars` : Traitement de données
- `llama-index` : Indexation / RAG
- `qdrant-client` : Stockage vectoriel
- `fastapi`, `uvicorn` : API
- `streamlit`, `plotly` : Interface et visualisations
- `redis` : Cache

---

## 🔗 Services externes

- **Qdrant** : Stockage vectoriel pour les embeddings
- **Redis** : Cache pour les réponses
- **Ollama** : Modèle de langage (ex : `llama3`)
- **SQLite** : Base de données pour les analyses

---

## 🔁 Reproductibilité

- **Docker** : Containerisation complète
- **uv** : Gestion déterministe des dépendances
- **`.env`** : Configuration centralisée
- **`init.sh`** : Initialisation cohérente des données
- **Logs** : Débogage dans `data/*.log`

---

## 🧪 Exemples de requêtes

### 🔍 Descriptives (RAG)

- "Liste des bâtiments résidentiels de plus de 1000 m² dans le département 93."
- "Décris les bâtiments tertiaires classés G à Marseille."

### 📊 Quantitatives (SQL)

- "Quelle est la surface moyenne des bâtiments tertiaires avant 1975 dans le Rhône ?"
- "Quel est le pourcentage de bâtiments résidentiels avant 1948 à Lyon ?"
- "Quels sont les 10 quartiers de Marseille avec le plus de passoires thermiques ?"
- "Quelle commune du département 34 a le plus de bâtiments classés G ?"

---

## 🤝 Contribution

1. **Forkez** le dépôt
2. **Créez une branche** : `git checkout -b feature/ma-fonctionnalite`
3. **Ajoutez des tests** dans `tests/` (avec `pytest`)
4. **Soumettez une pull request**

### Suggestions d'améliorations

- Génération de requêtes SQL dynamiques via NLP
- Visualisations géographiques (ex. Folium)
- Optimisation de l’indexation avec parallélisme
- Authentification API

---

## 🐞 Problèmes connus

- **Téléchargement** : `consolidate.py` peut être lent → possibilité de pré-téléchargement
- **Mémoire** : départements volumineux = besoin de RAM élevé
- manque de pertinence dans les réponses RAG en raison de la limitation à un seul departement (le 93 par defaut)

---

## 📄 Licence

MIT License – voir le fichier `LICENSE`.

---

## 📬 Contact

Pour toute question, ouvrez une issue ou contactez :  
`[fzrouama@gmail.com](mailto:fzrouama@gmail.com)`
