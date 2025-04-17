import polars as pl
from llama_index.core import Document, StorageContext, VectorStoreIndex
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, Filter, FieldCondition, MatchValue
from pathlib import Path
from tqdm import tqdm
import pickle
from rag.tools.config import (
    EMBEDDING_MODEL, QDRANT_HOST, QDRANT_PORT, COLLECTION_NAME, 
    CONSOLIDATED_PARQUET, STORAGE_DIR
)
from rag.tools.logger import setup_logger


class BDNBIndexer:
    """
    Module pour indexer les données BDNB dans Qdrant avec LlamaIndex.
    """
    def __init__(self, data_path: str = CONSOLIDATED_PARQUET):
        """
        Initialise l'indexeur.

        Args:
            data_path (str): Chemin vers le fichier Parquet consolidé.
        """
        self.data_path = data_path
        self.logger = setup_logger("indexer", log_file=str(Path(data_path).parent / "indexer.log"))
        self.logger.info("Initialized BDNBIndexer")

    def extract_data(self) -> pl.DataFrame:
        """
        Charge les données consolidées depuis le fichier Parquet.

        Returns:
            pl.DataFrame: Données chargées.
        """
        try:
            df = pl.read_parquet(self.data_path)
            self.logger.info(f"Extracted {len(df)} rows from {self.data_path}")
            return df
        except FileNotFoundError:
            self.logger.error(f"File not found: {self.data_path}")
            return pl.DataFrame()
        except Exception as e:
            self.logger.error(f"Error loading {self.data_path}: {e}")
            return pl.DataFrame()

    def build_documents(self, df: pl.DataFrame) -> list[Document]:
        """
        Construit des documents LlamaIndex à partir des données BDNB.

        Args:
            df (pl.DataFrame): Données consolidées.

        Returns:
            list[Document]: Liste des documents prêts à être indexés.
        """
        documents = []
        for row in df.iter_rows(named=True):
            # Texte descriptif pour l'embedding
            text = (
                f"Bâtiment ID : {row['batiment_groupe_id']}\n"
                f"Localisation : {row['libelle_commune_insee'] or 'Inconnue'} "
                f"(Département {row['code_departement_insee'] or 'N/A'}, "
                f"Commune {row['code_commune_insee'] or 'N/A'})\n"
                f"Type : {row['usage_principal'] or 'Inconnu'}\n"
                f"Surface estimée : {row['s_totale_bat'] or 'Inconnue'} m² "
                f"({row['surface_category'] or 'Inconnue'})\n"
                f"Année de construction : {row['annee_construction'] or 'Inconnue'}\n"
                f"Nombre d'étages : {row['nb_niveau'] or 'Inconnu'}\n"
                f"Classe DPE : {row['classe_bilan_dpe'] or 'Non disponible'}\n"
                f"Passoire thermique : {'Oui' if row['is_passoire_thermique'] == 1 else 'Non'}\n"
                f"Quartier prioritaire : {'Oui' if row['qpv_indicateur'] == 1 else 'Non'}\n"
                f"Arrondissement : {row['arrondissement'] or 'Non applicable'}"
            )

            # Métadonnées pour filtres et recherches
            metadata = {
                "batiment_groupe_id": str(row["batiment_groupe_id"]),
                "code_departement_insee": str(row["code_departement_insee"] or "N/A"),
                "code_commune_insee": str(row["code_commune_insee"] or "N/A"),
                "libelle_commune_insee": row["libelle_commune_insee"] or "",
                "code_iris": str(row["code_iris"] or ""),
                "usage_principal": row["usage_principal"] or "Inconnu",
                "is_residentiel": int(row["is_residentiel"] or 0),
                "is_tertiaire": int(row["is_tertiaire"] or 0),
                "s_totale_bat": float(row["s_totale_bat"]) if row["s_totale_bat"] is not None else None,
                "surface_category": str(row["surface_category"] or "Inconnue"),
                "annee_construction": float(row["annee_construction"]) if row["annee_construction"] is not None else None,
                "avant_1948": int(row["avant_1948"] or 0),
                "avant_1975": int(row["avant_1975"] or 0),
                "nb_niveau": float(row["nb_niveau"]) if row["nb_niveau"] is not None else None,
                "plus_de_5_etages": int(row["plus_de_5_etages"] or 0),
                "classe_bilan_dpe": row["classe_bilan_dpe"] or "Non disponible",
                "is_passoire_thermique": int(row["is_passoire_thermique"] or 0),
                "qpv_indicateur": int(row["qpv_indicateur"] or 0),
                "arrondissement": row["arrondissement"] or "Non applicable"
            }

            documents.append(Document(text=text, metadata=metadata))

        self.logger.info(f"Built {len(documents)} documents")
        return documents

    def create_qdrant_filter(self, query: str) -> Filter:
        """
        Crée un filtre Qdrant basé sur la requête.

        Args:
            query (str): Requête en langage naturel.

        Returns:
            Filter: Filtre Qdrant pour restreindre la recherche.
        """
        conditions = []
        query = query.lower()

        if "département" in query:
            dept_match = pl.Series([query]).str.extract(r"département (\d+)", 1)[0]
            if dept_match:
                conditions.append(
                    FieldCondition(
                        key="metadata.code_departement_insee",
                        match=MatchValue(value=dept_match)
                    )
                )
        if "résidentiels" in query:
            conditions.append(
                FieldCondition(
                    key="metadata.is_residentiel",
                    match=MatchValue(value=1)
                )
            )
        if "tertiaires" in query:
            conditions.append(
                FieldCondition(
                    key="metadata.is_tertiaire",
                    match=MatchValue(value=1)
                )
            )
        if "passoires thermiques" in query or "f ou g" in query:
            conditions.append(
                FieldCondition(
                    key="metadata.is_passoire_thermique",
                    match=MatchValue(value=1)
                )
            )
        if "plus de 5 étages" in query:
            conditions.append(
                FieldCondition(
                    key="metadata.plus_de_5_etages",
                    match=MatchValue(value=1)
                )
            )

        filter_obj = Filter(must=conditions) if conditions else None
        self.logger.info(f"Created Qdrant filter for query: {query[:50]}... (Conditions: {len(conditions)})")
        return filter_obj

    def index_documents(self):
        """
        Indexe les données BDNB dans Qdrant avec LlamaIndex.
        """
        # Charger les données
        df = self.extract_data()
        if df.is_empty():
            self.logger.error("No data to index")
            return

        # Initialiser le modèle d'embedding
        try:
            embed_model = HuggingFaceEmbedding(model_name=EMBEDDING_MODEL)
            self.logger.info(f"Loaded embedding model: {EMBEDDING_MODEL}")
        except Exception as e:
            self.logger.error(f"Error loading embedding model: {e}")
            return

        # Création du client Qdrant
        try:
            qdrant_client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
            vector_size = len(embed_model.get_text_embedding("test"))
            vector_params = VectorParams(size=vector_size, distance=Distance.COSINE)
            self.logger.info(f"Initialized Qdrant client at {QDRANT_HOST}:{QDRANT_PORT}")
        except Exception as e:
            self.logger.error(f"Error configuring Qdrant: {e}")
            return

        # Indexation par département (sharding)
        for dept in tqdm(df["code_departement_insee"].unique(), desc="Indexing departments"):
            collection_name = f"{COLLECTION_NAME}_{dept}"
            dept_df = df.filter(pl.col("code_departement_insee") == dept)
            documents = self.build_documents(dept_df)

            if not documents:
                self.logger.warning(f"No documents for department {dept}, skipping")
                continue

            # Créer ou recréer la collection
            try:
                if qdrant_client.collection_exists(collection_name):
                    qdrant_client.delete_collection(collection_name)
                    self.logger.info(f"Deleted existing collection: {collection_name}")
                qdrant_client.create_collection(collection_name=collection_name, vectors_config=vector_params)
                self.logger.info(f"Created collection: {collection_name}")
            except Exception as e:
                self.logger.error(f"Error creating collection {collection_name}: {e}")
                continue

            # Indexation par lots
            try:
                vector_store = QdrantVectorStore(client=qdrant_client, collection_name=collection_name)
                storage_context = StorageContext.from_defaults(vector_store=vector_store)

                index = VectorStoreIndex.from_documents(
                    documents,
                    storage_context=storage_context,
                    embed_model=embed_model
                )
                
                # Persister l'index
                index.storage_context.persist(persist_dir=f"{STORAGE_DIR}/{dept}")
                self.logger.info(f"Persisted index for department {dept} to {STORAGE_DIR}/{dept}")
            except Exception as e:
                self.logger.error(f"Error indexing department {dept}: {e}")
                continue

        # Sauvegarder la fonction de filtre
        try:
            with open(f"{STORAGE_DIR}/qdrant_filter.pkl", "wb") as f:
                pickle.dump(self.create_qdrant_filter, f)
            self.logger.info("Saved Qdrant filter function")
        except Exception as e:
            self.logger.error(f"Error saving Qdrant filter: {e}")

if __name__ == "__main__":
    indexer = BDNBIndexer()
    indexer.index_documents()