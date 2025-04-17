# Utiliser l'image officielle uv basée sur Debian Bookworm
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Installer make, curl et autres dépendances système
RUN apt-get update && apt-get install -y --no-install-recommends \
    make \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Définir le répertoire de travail
WORKDIR /app

# Copier les fichiers de dépendances et le Makefile
COPY pyproject.toml uv.lock Makefile ./

# Synchroniser les dépendances avec uv
RUN uv sync --frozen

# Copier le répertoire rag/ contenant le code
COPY rag/ ./rag/

# Commande par défaut (sera remplacée par docker-compose)
CMD ["make", "run-api"]