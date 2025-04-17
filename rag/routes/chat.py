from fastapi import HTTPException, APIRouter
from pydantic import BaseModel
from llama_index.core import StorageContext, load_index_from_storage
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.llms.ollama import Ollama
from llama_index.llms.huggingface import HuggingFaceLLM
from qdrant_client import QdrantClient
from rag.tools.database import BDNBDatabase
from rag.jobs.indexer import BDNBIndexer
from rag.tools.cache import ResponseCache
from rag.tools.config import (
    EMBEDDING_MODEL, QDRANT_HOST, QDRANT_PORT, COLLECTION_NAME, 
    LLM_MODEL, STORAGE_DIR, SIMILARITY_TOP_K, DATA_DIR, OLLAMA_BASE_URL, REDIS_HOST,REDIS_PORT
)
from rag.helpers.prompts import (
    analyze_prompt, format_sql_prompt, custom_prompt
)
from rag.helpers.lib import get_collection_name, analyze_question_with_llm, format_sql_results_with_llm
from rag.tools.logger import setup_logger
import pickle
from pathlib import Path


chat_router = APIRouter()

# Initialisation du logger
logger = setup_logger("chat", log_file=str(Path(DATA_DIR) / "chat.log"))

embed_model = HuggingFaceEmbedding(model_name=EMBEDDING_MODEL)
llm = Ollama(model=LLM_MODEL, request_timeout=3600, base_url=OLLAMA_BASE_URL)
qdrant_client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
db = BDNBDatabase()
cache = ResponseCache(host=REDIS_PORT, port=REDIS_HOST)

# Charger la fonction de filtre Qdrant
try:
    with open(f"{STORAGE_DIR}/qdrant_filter.pkl", "rb") as f:
        create_qdrant_filter = pickle.load(f)
    logger.info("Loaded Qdrant filter function")
except Exception as e:
    logger.error(f"Error loading Qdrant filter: {e}")
    def create_qdrant_filter(query: str):
        return None


# Modèle Pydantic pour les requêtes
class ChatRequest(BaseModel):
    message: str


@chat_router.post("/chat", summary="Interroger les données BDNB")
async def chat(request: ChatRequest):
    """
    Endpoint pour interroger les données BDNB en langage naturel.

    Args:
        request (ChatRequest): Requête contenant le message.

    Returns:
        dict: Réponse textuelle et nœuds récupérés.
    """
    message = request.message
    if not message:
        logger.error("Empty message received")
        raise HTTPException(status_code=400, detail="Message is required")

    # Vérifier le cache
    try:
        cached_response = cache.get(message)
        if cached_response:
            logger.info(f"Cache hit for query: {message[:50]}...")
            return cached_response
    except Exception as e:
        logger.error(f"Cache error: {e}")

    try:
        # Analyser la question avec le LLM
        analysis = analyze_question_with_llm(message, llm, analyze_prompt, logger)
        is_quantitative = analysis.get("is_quantitative", False)
        sql_query = analysis.get("sql_query", None)

        if is_quantitative and sql_query:
            try:
                result = db.query(sql_query)
                # Convertir les résultats en liste de dictionnaires
                raw_data = result.to_dicts()
                # Formater les résultats avec le LLM
                friendly_response = format_sql_results_with_llm(message, raw_data, llm, format_sql_prompt, logger)
                response_dict = {
                    "response": friendly_response,
                    "raw_data": raw_data,
                    "retrieved_nodes": []
                }
                try:
                    cache.set(message, response_dict)
                except Exception as e:
                    logger.error(f"Error setting cache: {e}")
                logger.info(f"SQL query executed, returning {len(result)} rows")
                return response_dict
            except Exception as e:
                logger.error(f"SQL query failed: {e}")
                # Passer à RAG si la requête SQL échoue

        # Configurer l'index pour la recherche RAG
        collection_name = get_collection_name(message,COLLECTION_NAME,logger)

        if collection_name and collection_name != COLLECTION_NAME:
            # Cas 1 : une collection spécifique
            try:
                vector_store = QdrantVectorStore(client=qdrant_client, collection_name=collection_name)
                persist_dir = f"{STORAGE_DIR}/{collection_name.split('_')[-1]}"
                if not Path(persist_dir).exists() or not Path(f"{persist_dir}/docstore.json").exists():
                    logger.error(f"Index directory {persist_dir} or docstore.json missing")
                    raise HTTPException(status_code=500, detail=f"No index found for {collection_name}")
                storage_context = StorageContext.from_defaults(
                    persist_dir=persist_dir,
                    vector_store=vector_store
                )
                index = load_index_from_storage(storage_context=storage_context, embed_model=embed_model)
                logger.info(f"Loaded index for collection: {collection_name}")
            except Exception as e:
                logger.error(f"Error loading index for {collection_name}: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to load index for {collection_name}")
        else:
            # Cas 2 : aucune collection spécifique → charger toutes les collections disponibles
            try:
                collections = qdrant_client.get_collections().collections
                indexes = []

                for coll in collections:
                    if coll.name.startswith(COLLECTION_NAME):
                        logger.info(f"Attempting to load collection: {coll.name}")
                        try:
                            vector_store = QdrantVectorStore(client=qdrant_client, collection_name=coll.name)
                            persist_dir = f"{STORAGE_DIR}/{coll.name.split('_')[-1]}"
                            if not Path(persist_dir).exists() or not Path(f"{persist_dir}/docstore.json").exists():
                                logger.warning(f"Index directory {persist_dir} or docstore.json missing, skipping {coll.name}")
                                continue
                            storage_context = StorageContext.from_defaults(
                                persist_dir=persist_dir,
                                vector_store=vector_store
                            )
                            index = load_index_from_storage(storage_context=storage_context, embed_model=embed_model)
                            indexes.append(index)
                            logger.info(f"Loaded index for collection: {coll.name}")
                        except Exception as e:
                            logger.warning(f"Skipping collection {coll.name} due to error: {e}")
                            continue
                
                if not indexes:
                    logger.error("No valid indexes found for any collection")
                    raise HTTPException(status_code=500, detail="No valid indexes found for any collection")

                # Simplifier : utiliser le premier index valide comme fallback
                index = indexes[0]
                logger.info("Using first valid index as fallback for general query")

            except Exception as e:
                logger.error(f"Error loading multiple indexes: {e}")
                raise HTTPException(status_code=500, detail="Failed to load indexes for all collections")

        # Configurer le retriever avec filtres
        qdrant_filter = create_qdrant_filter(message)
        retriever = VectorIndexRetriever(
            index=index,
            similarity_top_k=SIMILARITY_TOP_K,
            filters=qdrant_filter
        )
        
        # Configurer le query engine
        query_engine = RetrieverQueryEngine.from_args(
            retriever=retriever,
            llm=llm,
            text_qa_template=custom_prompt
        )

        # Exécuter la requête RAG
        nodes = retriever.retrieve(message)
        response = query_engine.query(message)

        # Formater les nœuds récupérés
        retrieved_nodes = [
            {
                "batiment_groupe_id": node.metadata.get("batiment_groupe_id", "N/A"),
                "text": node.text,
                "score": float(node.score) if node.score is not None else 0.0,
                "metadata": {
                    "code_departement_insee": node.metadata.get("code_departement_insee", "N/A"),
                    "libelle_commune_insee": node.metadata.get("libelle_commune_insee", "N/A"),
                    "usage_principal": node.metadata.get("usage_principal", "N/A"),
                    "classe_bilan_dpe": node.metadata.get("classe_bilan_dpe", "N/A"),
                    "is_passoire_thermique": int(node.metadata.get("is_passoire_thermique", 0)),
                    "s_totale_bat": float(node.metadata.get("s_totale_bat", None)) 
                                   if node.metadata.get("s_totale_bat") is not None else None
                }
            }
            for node in nodes
        ]

        # Créer la réponse pour RAG
        response_dict = {
            "response": str(response),
            "raw_data": None,
            "retrieved_nodes": retrieved_nodes
        }

        # Stocker dans le cache
        try:
            cache.set(message, response_dict)
            logger.info(f"Cache set for query: {message[:50]}...")
        except Exception as e:
            logger.error(f"Error setting cache: {e}")

        logger.info(f"Processed RAG query, returning {len(retrieved_nodes)} nodes")
        return response_dict

    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

