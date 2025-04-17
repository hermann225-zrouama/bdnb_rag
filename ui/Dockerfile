# Utiliser une image Python légère avec uv préinstallé
FROM ghcr.io/astral-sh/uv:python3.12-alpine

WORKDIR /app
COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

CMD ["uv", "run", "streamlit", "run", "ui_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
