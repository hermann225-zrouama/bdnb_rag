import polars as pl
import warnings
from typing import Dict, List, Optional, Callable
from pathlib import Path
from sklearn.linear_model import LinearRegression
from sklearn.impute import KNNImputer
import numpy as np
from tools.config import DATA_DIR, CONSOLIDATED_PARQUET, SQLITE_DB_PATH
from tools.logger import setup_logger

warnings.filterwarnings("ignore")  # Ignorer les avertissements mineurs pour lisibilité

class BDNBFeatureEngineer:
    """
    Module pour le feature engineering de la BDNB.
    """
    def __init__(self, data_dir: str = DATA_DIR):
        """
        Initialise le module avec le dossier des données.

        Args:
            data_dir (str): Chemin vers le dossier des données.
        """
        self.data_dir = Path(data_dir).joinpath("files")
        self.log_dir = Path(data_dir)
        self.logger = setup_logger("feature_eng", log_file=str(self.log_dir / "feature_eng.log"))
        self.files = {
            "batiment_groupe": self.data_dir / "bdnb_batiment_groupe.parquet",
            "dpe_representatif": self.data_dir / "bdnb_batiment_groupe_dpe_representatif_logement.parquet",
            "dpe_statistique": self.data_dir / "bdnb_batiment_groupe_dpe_statistique_logement.parquet",
            "ffo_bat": self.data_dir / "bdnb_batiment_groupe_ffo_bat.parquet",
            "adresse": self.data_dir / "bdnb_adresse.parquet",
            "rel_adresse": self.data_dir / "bdnb_rel_batiment_groupe_adresse.parquet",
            "synthese_usage": self.data_dir / "bdnb_batiment_groupe_synthese_propriete_usage.parquet",
            "qpv": self.data_dir / "bdnb_batiment_groupe_qpv.parquet"
        }
        self.dataframes: Dict[str, pl.DataFrame] = {}
        self.sqlite_db = SQLITE_DB_PATH
        self.logger.info("Initialized BDNBFeatureEngineer")

    def load_parquet_safe(self, file_path: Path, required_cols: Optional[List[str]] = None) -> Optional[pl.DataFrame]:
        """
        Charge un fichier Parquet et vérifie les colonnes requises.

        Args:
            file_path (Path): Chemin vers le fichier Parquet.
            required_cols (Optional[List[str]]): Colonnes requises.

        Returns:
            Optional[pl.DataFrame]: DataFrame chargé, ou None en cas d'erreur.
        """
        try:
            df = pl.read_parquet(file_path)
            self.logger.info(f"Loaded {file_path} with {len(df)} rows")
            if required_cols:
                missing_cols = [col for col in required_cols if col not in df.columns]
                if missing_cols:
                    self.logger.warning(f"Missing columns in {file_path}: {missing_cols}")
            return df
        except FileNotFoundError:
            self.logger.error(f"File not found: {file_path}")
            return None
        except Exception as e:
            self.logger.error(f"Error loading {file_path}: {e}")
            return None

    def load_data(self) -> bool:
        """
        Charge toutes les tables nécessaires.

        Returns:
            bool: True si toutes les tables sont chargées, False sinon.
        """
        required_cols = {
            "batiment_groupe": ["batiment_groupe_id", "code_departement_insee", "code_commune_insee", 
                                "libelle_commune_insee", "code_iris"],
            "dpe_representatif": ["batiment_groupe_id", "classe_bilan_dpe"],
            "dpe_statistique": ["batiment_groupe_id", "nb_classe_bilan_dpe_f", "nb_classe_bilan_dpe_g"],
            "ffo_bat": ["batiment_groupe_id", "annee_construction", "nb_niveau", "usage_niveau_1_txt", "nb_log"],
            "adresse": ["cle_interop_adr", "code_departement_insee", "code_commune_insee", "libelle_commune"],
            "rel_adresse": ["batiment_groupe_id", "cle_interop_adr"],
            "synthese_usage": ["batiment_groupe_id", "usage_principal_bdnb_open"],
            "qpv": ["batiment_groupe_id", "nom_quartier"]
        }

        for key, file_path in self.files.items():
            self.dataframes[key] = self.load_parquet_safe(file_path, required_cols.get(key))
            if self.dataframes[key] is None:
                self.logger.error(f"Failed to load {key}")
                return False
        self.logger.info("All tables loaded successfully")
        return True

    # Methode de feature eng
    def add_building_type(self):
        """Ajoute les features de type de bâtiment (résidentiel/tertiaire)."""
        df_usage = self.dataframes["synthese_usage"]
        self.dataframes["synthese_usage"] = df_usage.with_columns([
            pl.col("usage_principal_bdnb_open").str.contains("résidentiel", literal=True)
              .fill_null(False).cast(pl.Int32).alias("is_residentiel"),
            pl.col("usage_principal_bdnb_open").str.contains("tertiaire", literal=True)
              .fill_null(False).cast(pl.Int32).alias("is_tertiaire"),
            pl.col("usage_principal_bdnb_open").replace({
                "Résidentiel collectif": "Résidentiel",
                "Résidentiel individuel": "Résidentiel",
                "Maison": "Résidentiel",
                "Tertiaire - bureaux": "Tertiaire",
                "Tertiaire - commerce": "Tertiaire"
            }).alias("usage_principal")
        ])
        self.logger.info("Added building type features")

    def add_surface(self):
        """Ajoute les features de surface en utilisant surface_habitable ou une régression."""
        df_ffo = self.dataframes["ffo_bat"]
        
        if "surface_habitable" in df_ffo.columns:
            df_ffo = df_ffo.with_columns(pl.col("surface_habitable").fill_null(0).alias("s_totale_bat"))
            self.logger.info("Used surface_habitable for surface feature")
        else:
            # Régression linéaire pour estimer la surface
            train_data = df_ffo.filter(pl.col("nb_log").is_not_null() & pl.col("nb_niveau").is_not_null())
            if len(train_data) > 0:
                X = train_data[["nb_log", "nb_niveau"]].to_numpy()
                y = train_data["nb_log"].to_numpy() * 50  # Hypothèse initiale
                model = LinearRegression()
                model.fit(X, y)
                
                # Prédire pour toutes les lignes
                X_all = df_ffo[["nb_log", "nb_niveau"]].fill_null(0).to_numpy()
                df_ffo = df_ffo.with_columns(pl.Series(model.predict(X_all)).alias("s_totale_bat"))
                self.logger.info("Estimated surface using linear regression")
            else:
                df_ffo = df_ffo.with_columns((pl.col("nb_log").fill_null(0) * 50).alias("s_totale_bat"))
                self.logger.warning("Fallback to nb_log * 50 for surface")

        # Catégorisation
        df_ffo = df_ffo.with_columns(
            pl.col("s_totale_bat").cut(breaks=[500, 1000], labels=["<500m²", "500-1000m²", ">1000m²"])
              .alias("surface_category")
        )
        self.dataframes["ffo_bat"] = df_ffo
        self.logger.info("Added surface features")

    def add_dpe(self):
        """Ajoute les features liées au DPE."""
        df_dpe = self.dataframes["dpe_representatif"]
        self.dataframes["dpe_representatif"] = df_dpe.with_columns(
            pl.col("classe_bilan_dpe").is_in(["F", "G"]).cast(pl.Int32).alias("is_passoire_thermique")
        )
        self.logger.info("Added DPE features")

    def add_construction_year(self):
        """Ajoute les features liées à l'année de construction."""
        df_ffo = self.dataframes["ffo_bat"]
        self.dataframes["ffo_bat"] = df_ffo.with_columns([
            (pl.col("annee_construction") < 1948).cast(pl.Int32).alias("avant_1948"),
            (pl.col("annee_construction") < 1975).cast(pl.Int32).alias("avant_1975")
        ])
        self.logger.info("Added construction year features")

    def add_floors(self):
        """Ajoute les features liées au nombre d'étages."""
        df_ffo = self.dataframes["ffo_bat"]
        self.dataframes["ffo_bat"] = df_ffo.with_columns(
            (pl.col("nb_niveau") > 5).cast(pl.Int32).alias("plus_de_5_etages")
        )
        self.logger.info("Added floor features")

    def add_location(self):
        """Ajoute les features de localisation."""
        df_adr = self.dataframes["adresse"]
        df_bat = self.dataframes["batiment_groupe"]
        df_rel_adr = self.dataframes["rel_adresse"]
        df_qpv = self.dataframes["qpv"]

        # Normaliser code_departement_insee
        df_adr = df_adr.with_columns(
            pl.col("code_departement_insee").cast(pl.Utf8).str.zfill(3).alias("code_departement_insee")
        )
        df_bat = df_bat.with_columns(
            pl.col("code_departement_insee").cast(pl.Utf8).str.zfill(3).alias("code_departement_insee")
        )

        # Joindre adresses
        df_loc = df_rel_adr.join(
            df_adr.select(["cle_interop_adr", "code_departement_insee", "code_commune_insee", "libelle_commune"]),
            on="cle_interop_adr", how="left"
        )

        # Extraire arrondissement
        df_loc = df_loc.with_columns(
            pl.col("code_commune_insee").cast(pl.Utf8).str.slice(-2).cast(pl.Int32)
              .map_elements(lambda x: f"{x}e arrondissement").alias("arrondissement")
        )

        # Indicateur QPV
        df_loc = df_loc.join(
            df_qpv.select(["batiment_groupe_id", "nom_quartier"]), 
            on="batiment_groupe_id", how="left"
        ).with_columns(
            pl.col("nom_quartier").is_not_null().cast(pl.Int32).alias("qpv_indicateur")
        )

        self.dataframes["location"] = df_loc
        self.logger.info("Added location features")

    def add_passoires_by_area(self):
        """Ajoute les features de passoires thermiques par quartier."""
        df_dpe_stat = self.dataframes["dpe_statistique"]
        df_loc = self.dataframes["location"]
        
        df_dpe_stat = df_dpe_stat.with_columns(
            (pl.col("nb_classe_bilan_dpe_f").fill_null(0) + pl.col("nb_classe_bilan_dpe_g").fill_null(0))
              .alias("nb_passoires")
        )
        
        df_passoires = df_dpe_stat.join(
            df_loc.select(["batiment_groupe_id", "code_commune_insee"]),
            on="batiment_groupe_id", how="left"
        )
        
        df_passoires_by_commune = df_passoires.group_by("code_commune_insee").agg(
            nb_passoires=pl.col("nb_passoires").sum()
        )
        
        self.dataframes["passoires_by_commune"] = df_passoires_by_commune
        self.logger.info("Added passoires by area features")

    def clean_data(self):
        """Nettoie les données (valeurs manquantes, dédoublonnage)."""
        # Imputer annee_construction
        df_ffo = self.dataframes["ffo_bat"]
        median_year = df_ffo.group_by("nb_niveau").agg(
            annee_construction=pl.col("annee_construction").median()
        )
        df_ffo = df_ffo.join(median_year, on="nb_niveau", how="left").with_columns(
            pl.col("annee_construction").fill_null(pl.col("annee_construction_right"))
              .fill_null(df_ffo["annee_construction"].median()).alias("annee_construction")
        ).drop("annee_construction_right")

        # Imputer classe_bilan_dpe avec k-NN
        df_dpe = self.dataframes["dpe_representatif"]
        df_ffo_tmp = df_ffo.select(["batiment_groupe_id", "annee_construction", "nb_niveau"])
        
        df_impute = df_dpe.join(df_ffo_tmp, on="batiment_groupe_id", how="left")
        dpe_mapping = {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6, "G": 7}
        df_impute = df_impute.with_columns(
            pl.col("classe_bilan_dpe").replace(dpe_mapping).alias("classe_bilan_dpe_num")
        )
        
        imputer = KNNImputer(n_neighbors=5)
        imputed = imputer.fit_transform(
            df_impute[["classe_bilan_dpe_num", "annee_construction", "nb_niveau"]].fill_null(0).to_numpy()
        )
        
        reverse_mapping = {v: k for k, v in dpe_mapping.items()}
        mapped_values = [
            reverse_mapping.get(int(round(val)), "Non disponible") for val in imputed[:, 0]
        ]

        # Créer la colonne Polars à partir du mapping
        df_impute = df_impute.with_columns(
            pl.Series(name="classe_bilan_dpe", values=mapped_values)
        )
        
        df_dpe = df_impute.select(df_dpe.columns).with_columns(
            pl.col("classe_bilan_dpe").is_in(["F", "G"]).cast(pl.Int32).alias("is_passoire_thermique")
        )
        self.dataframes["dpe_representatif"] = df_dpe

        # Filtrer surfaces aberrantes
        df_ffo = df_ffo.filter((pl.col("s_totale_bat") > 0) & (pl.col("s_totale_bat") < 1_000_000))
        self.dataframes["ffo_bat"] = df_ffo

        # Dédoublonnage
        for key in ["batiment_groupe", "dpe_representatif", "location", "synthese_usage", "ffo_bat"]:
            if key in self.dataframes:
                self.dataframes[key] = self.dataframes[key].unique(subset=["batiment_groupe_id"])
        
        self.logger.info("Cleaned data (imputed missing values, removed duplicates)")

    def validate_data(self):
        """Valide la cohérence des données."""
        df = self.merge_data()
        errors = []

        # Vérifier la cohérence des codes géographiques
        df = df.with_columns([
            pl.col("code_departement_insee").cast(pl.Utf8).str.slice(0, 2).alias("dep_prefix"),
            pl.col("code_commune_insee").cast(pl.Utf8).str.slice(0, 2).alias("com_prefix")
        ])

        invalid_geo = df.filter(
            pl.col("dep_prefix") != pl.col("com_prefix")
        ).shape[0]
        if invalid_geo > 0:
            errors.append(f"{invalid_geo} lignes avec des codes département/commune incohérents")

        # Vérifier les classes DPE
        valid_dpe = ["A", "B", "C", "D", "E", "F", "G", "Non disponible"]
        invalid_dpe = df.filter(~pl.col("classe_bilan_dpe").is_in(valid_dpe)).shape[0]
        if invalid_dpe > 0:
            errors.append(f"{invalid_dpe} lignes avec des classes DPE invalides")

        # Vérifier les surfaces aberrantes
        invalid_surface = df.filter(
            (pl.col("s_totale_bat") < 0) | (pl.col("s_totale_bat") > 1_000_000)
        ).shape[0]
        if invalid_surface > 0:
            errors.append(f"{invalid_surface} lignes avec des surfaces aberrantes")

        if errors:
            self.logger.warning("Data validation errors:")
            for error in errors:
                self.logger.warning(f"- {error}")
        else:
            self.logger.info("Data validation: OK")

    def merge_data(self) -> pl.DataFrame:
        """
        Fusionne les tables pour créer une table consolidée.

        Returns:
            pl.DataFrame: Table consolidée.
        """
        df_consolidated = self.dataframes["batiment_groupe"].select([
            "batiment_groupe_id", "code_departement_insee", "code_commune_insee", 
            "libelle_commune_insee", "code_iris"
        ]).join(
            self.dataframes["ffo_bat"].select([
                "batiment_groupe_id", "annee_construction", "nb_niveau", 
                "s_totale_bat", "surface_category", "avant_1948", 
                "avant_1975", "plus_de_5_etages"
            ]), 
            on="batiment_groupe_id", how="left"
        ).join(
            self.dataframes["dpe_representatif"].select([
                "batiment_groupe_id", "classe_bilan_dpe", "is_passoire_thermique"
            ]), 
            on="batiment_groupe_id", how="left"
        ).join(
            self.dataframes["synthese_usage"].select([
                "batiment_groupe_id", "usage_principal", "is_residentiel", "is_tertiaire"
            ]), 
            on="batiment_groupe_id", how="left"
        ).join(
            self.dataframes["location"].select([
                "batiment_groupe_id", "libelle_commune", "arrondissement", "qpv_indicateur"
            ]), 
            on="batiment_groupe_id", how="left"
        )
        self.logger.info(f"Merged data into consolidated table with {len(df_consolidated)} rows")
        return df_consolidated
    
    def save_to_sqlite(self, df: pl.DataFrame, table_name: str = "buildings") -> None:
        """
        Sauvegarde le DataFrame consolidé dans une base de données SQLite.

        Args:
            df (pl.DataFrame): DataFrame à sauvegarder.
            table_name (str): Nom de la table dans SQLite.
        """
        try:
            # Créer la connexion SQLite
            connection_uri = f"sqlite:///{self.sqlite_db}"
            # Sauvegarder le DataFrame dans SQLite, remplacer la table si elle existe
            df.write_database(
                table_name=table_name,
                connection=connection_uri,
                if_table_exists="replace"
            )
            self.logger.info(f"Saved consolidated table to SQLite at {self.sqlite_db}, table: {table_name}")
        except Exception as e:
            self.logger.error(f"Error saving to SQLite: {e}")
            raise

    def run_pipeline(self, steps: Optional[List[Callable]] = None, output_path: Optional[str] = CONSOLIDATED_PARQUET) -> pl.DataFrame:
        """
        Exécute le pipeline de feature engineering.

        Args:
            steps (Optional[List[Callable]]): Liste des étapes à exécuter.
            output_path (Optional[str]): Chemin pour sauvegarder la table consolidée.

        Returns:
            pl.DataFrame: Table consolidée.
        """
        if not self.load_data():
            self.logger.error("Failed to load data, aborting pipeline")
            raise RuntimeError("Failed to load data")

        default_steps = [
            self.add_building_type,
            self.add_surface,
            self.add_dpe,
            self.add_construction_year,
            self.add_floors,
            self.add_location,
            self.add_passoires_by_area,
            self.clean_data,
            self.validate_data
        ]

        steps = steps if steps is not None else default_steps

        for step in steps:
            self.logger.info(f"Executing step: {step.__name__}")
            step()

        df_consolidated = self.merge_data()

        ##################### recuperer que  10000 lignes
        df_consolidated = df_consolidated.sample(10000)
        ######################################################### A SUPPRIMER

        if output_path:
            df_consolidated.write_parquet(output_path, compression="snappy")
            self.logger.info(f"Saved consolidated table to {output_path}")

        self.save_to_sqlite(df_consolidated)
        return df_consolidated

if __name__ == "__main__":
    engineer = BDNBFeatureEngineer()

    # Exemple avec toutes les étapes
    df_consolidated = engineer.run_pipeline()
    print(f"Consolidated table preview:\n{df_consolidated.head()}")
