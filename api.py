from fastapi import FastAPI
import uvicorn

from tools.config import (
    API_HOST, API_PORT
)
from tools.logger import setup_logger
from pathlib import Path
from tools.indexer import BDNBIndexer
from routes.chat import chat_router

# Initialisation du logger
logger = setup_logger("api", log_file=str(Path("data") / "api.log"))

# Initialisation de FastAPI
app = FastAPI(title="BDNB Assistant API", description="API pour interroger la BDNB en langage naturel")
app.include_router(chat_router, tags=["chat"])

if __name__ == "__main__":
    uvicorn.run(app, host=API_HOST, port=API_PORT)
    logger.info(f"API running at http://{API_HOST}:{API_PORT}")