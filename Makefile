# Nom du projet (pour logs ou debug éventuels)
PROJECT_NAME=bdnb_rag

# Commandes de base
install:
	@echo "📦 Installation des dépendances..."
	uv pip install -r requirements.txt

# Lancer l'API FastAPI
run-api:
	@echo "🚀 Lancement de l'API FastAPI..."
	uv run python -m rag.api

# Lancer l'interface Streamlit
run-ui:
	@echo "🖥️  Lancement de l'interface Streamlit..."
	uv run streamlit run ui/ui.py

# Lancer l'indexation des données
run-indexer:
	@echo "🔧 Lancement de l'indexeur..."
	uv run python -m rag.jobs.indexer

# Lancer la récupération des données
run-retriever:
	@echo "📡 Lancement du récupérateur de données..."
	uv run python -m rag.jobs.data_retriever

run-feature-eng:
	@echo "🔍 Lancement de l'extraction de caractéristiques..."
	uv run python -m rag.jobs.feature_eng

# Nettoyage
clean:
	@echo "🧹 Nettoyage des fichiers pycache et logs..."
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -name "*.log" -type f -delete
	find . -name "*.pkl" -type f -delete
	find . -name "*.json" -type f -delete
	find . -name "*.csv" -type f -delete
	find . -name "*.parquet" -type f -delete
	find . -name "*.db" -type f -delete
	find . -name "*depts.txt" -type f -delete

# Lancement complet (API + UI) - optionnel
dev:
	@echo "🔁 Lancement de l'API et de l'UI (dev)..."
	uv run python -m rag.api &
	sleep 2
	uv run streamlit run ui/ui.py

.PHONY: install run-api run-ui run-indexer run-retriever clean dev
