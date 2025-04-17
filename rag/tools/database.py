import sqlite3
import polars as pl
from pathlib import Path
from rag.tools.config import SQLITE_DB_PATH, CONSOLIDATED_PARQUET
from rag.tools.logger import setup_logger

class BDNBDatabase:
    """
    Gestion de la base de données SQLite pour les données BDNB.
    """
    def __init__(self, db_path: str = SQLITE_DB_PATH):
        """
        Initialise la connexion à la base de données SQLite.

        Args:
            db_path (str): Chemin vers le fichier SQLite.
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.logger = setup_logger("database", log_file=str(Path(db_path).parent / "database.log"))
        self.logger.info(f"Initialized SQLite database at {db_path}")

    def load_data(self, parquet_path: str = CONSOLIDATED_PARQUET):
        """
        Charge les données consolidées depuis un fichier Parquet dans SQLite.

        Args:
            parquet_path (str): Chemin vers le fichier Parquet consolidé.
        """
        try:
            df = pl.read_parquet(parquet_path)
            df.write_sql(self.conn, "buildings", if_exists="replace", index=False)
            self.logger.info(f"Loaded {len(df)} rows into SQLite table 'buildings'")
        except FileNotFoundError:
            self.logger.error(f"Parquet file not found: {parquet_path}")
            raise
        except Exception as e:
            self.logger.error(f"Error loading data into SQLite: {e}")
            raise

    def query(self, sql: str) -> pl.DataFrame:
        """
        Exécute une requête SQL et retourne les résultats sous forme de DataFrame Polars.

        Args:
            sql (str): Requête SQL à exécuter.

        Returns:
            pl.DataFrame: Résultats de la requête.
        """
        try:
            df = pl.read_database(query=sql, connection=self.conn)
            self.logger.info(f"Executed SQL query: {sql[:100]}... ({len(df)} rows returned)")
            return df
        except Exception as e:
            self.logger.error(f"Error executing SQL query: {sql[:100]}... ({e})")
            raise

    def close(self):
        """
        Ferme la connexion à la base de données.
        """
        try:
            self.conn.close()
            self.logger.info("Closed SQLite database connection")
        except Exception as e:
            self.logger.error(f"Error closing database connection: {e}")