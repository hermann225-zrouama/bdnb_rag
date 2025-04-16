# Utiliser une image Python légère avec uv préinstallé
FROM ghcr.io/astral-sh/uv:python3.12-alpine

# Définir le répertoire de travail
WORKDIR /app

# Copier les fichiers nécessaires
COPY . /app

# Installer les dépendances avec uv
RUN uv sync

# Exposer le port de Streamlit
EXPOSE 8501
EXPOSE 8000

# Commande pour lancer Streamlit
CMD ["uv", "run", "streamlit", "run", "ui.py", "--server.port", "8501", "--server.address", "0.0.0.0"]