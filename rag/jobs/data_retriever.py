import argparse
import requests
from bs4 import BeautifulSoup
import polars as pl
import zipfile
import os
import shutil
from tqdm import tqdm
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from pathlib import Path
from rag.tools.config import DATA_DIR
from rag.tools.logger import setup_logger

TEMP_DIR = os.path.join(DATA_DIR, "temp_bdnb_data")
OUTPUT_DIR = os.path.join(DATA_DIR, "files")
PROCESSED_DEPTS_FILE = os.path.join(OUTPUT_DIR, "processed_depts.txt")
URL = "https://bdnb.io/archives_data/bdnb_millesime_2024_10_a/"

# === Logger ===
# Utilisation de DATA_DIR pour stocker les logs dans le répertoire des données
logger = setup_logger("data_retriever", log_file=os.path.join(DATA_DIR, "data_retriever.log"))


# === Créer les dossiers ===
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# === Session avec retries ===
session = requests.Session()
retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
session.mount('https://', HTTPAdapter(max_retries=retries))


def download_and_extract_zip(url: str, temp_dir: str, dept_code: str) -> str:
    zip_path = os.path.join(temp_dir, f"{dept_code}.zip")
    try:
        response = session.get(url, stream=True, timeout=30)
        response.raise_for_status()
        with open(zip_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(os.path.join(temp_dir, dept_code))
        os.remove(zip_path)
        logger.info(f"Extracted zip for department {dept_code}")
        return os.path.join(temp_dir, dept_code)
    except (requests.exceptions.RequestException, zipfile.BadZipFile) as e:
        logger.error(f"Error downloading/extracting for {dept_code}: {e}")
        return None


def sample_csv_file(csv_path: str, csv_file: str, dept_code: str, sample: bool, sample_size: int) -> pl.DataFrame:
    if os.path.exists(csv_path):
        try:
            df = pl.read_csv(csv_path, infer_schema_length=1000000)
            if sample:
                if len(df) < sample_size:
                    logger.warning(f"{dept_code} - {csv_file}: only {len(df)} rows, keeping all")
                    sample_df = df
                else:
                    sample_df = df.sample(n=sample_size, seed=42)
            else:
                sample_df = df
            sample_df = sample_df.with_columns(pl.lit(dept_code).alias("departement"))
            logger.info(f"Loaded {len(sample_df)} rows for {dept_code} - {csv_file}")
            return sample_df
        except Exception as e:
            logger.error(f"Error processing {dept_code} - {csv_file}: {e}")
            return None
    logger.error(f"File not found: {csv_path}")
    return None


def append_to_combined_file(sample_df: pl.DataFrame, csv_file: str, output_dir: str):
    output_file = os.path.join(output_dir, f"bdnb_{os.path.basename(csv_file)}.parquet")
    # remove .csv from the filename
    output_file = output_file.replace(".csv", "")
    try:
        if os.path.exists(output_file):
            existing_df = pl.read_parquet(output_file)
            missing_cols = [col for col in existing_df.columns if col not in sample_df.columns]
            for col in missing_cols:
                sample_df = sample_df.with_columns(pl.lit(None).alias(col))
            sample_df = sample_df.select(existing_df.columns)
            combined_df = pl.concat([existing_df, sample_df])
            combined_df.write_parquet(output_file, compression="snappy")
        else:
            sample_df.write_parquet(output_file, compression="snappy")
        logger.info(f"Appended {len(sample_df)} rows to {output_file}")
    except Exception as e:
        logger.error(f"Error appending to {output_file}: {e}")


def main(departements, sample, sample_size):
    logger.info("Starting BDNB data consolidation")

    # Chargement des départements déjà traités
    processed_depts = set()
    if os.path.exists(PROCESSED_DEPTS_FILE):
        with open(PROCESSED_DEPTS_FILE, 'r') as f:
            processed_depts = set(f.read().splitlines())

    # Scraping de la page
    try:
        response = session.get(URL, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        table = soup.find('table', class_='table-striped')
        dept_rows = table.find('tbody').find_all('tr')
    except Exception as e:
        logger.error(f"Error scraping {URL}: {e}")
        return

    # Parsing des départements
    for row in tqdm(dept_rows, desc="Processing departments"):
        cols = row.find_all('td')
        dept_name = cols[0].text.strip()
        dept_code = dept_name.replace("Département ", "").replace(" ", "")

        if departements and dept_code not in departements:
            continue

        if dept_code in processed_depts:
            logger.info(f"Department {dept_code} already processed, skipping")
            continue

        logger.info(f"Processing department {dept_code}")
        csv_link = cols[1].find('a', href=True)['href']

        extract_dir = download_and_extract_zip(csv_link, TEMP_DIR, dept_code)
        if extract_dir:
            csv_files_found = []
            for root, _, files in os.walk(extract_dir):
                for file in files:
                    if file.endswith('.csv'):
                        csv_files_found.append(os.path.relpath(os.path.join(root, file), extract_dir))

            logger.info(f"Found {len(csv_files_found)} CSV files for {dept_code}")

            for csv_file in csv_files_found:
                csv_path = os.path.join(extract_dir, csv_file)
                sample_df = sample_csv_file(csv_path, csv_file, dept_code, sample, sample_size)
                if sample_df is not None:
                    append_to_combined_file(sample_df, csv_file, OUTPUT_DIR)

            shutil.rmtree(extract_dir)
            logger.info(f"Deleted temporary directory for {dept_code}")

            with open(PROCESSED_DEPTS_FILE, 'a') as f:
                f.write(f"{dept_code}\n")
            processed_depts.add(dept_code)

    if os.path.exists(TEMP_DIR) and not os.listdir(TEMP_DIR):
        os.rmdir(TEMP_DIR)
        logger.info("Deleted global temporary directory")

    logger.info("BDNB data consolidation completed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Consolide les données BDNB par département.")
    parser.add_argument(
        "--departements", "-d",
        nargs="+",
        default=["93"],
        help="Liste des départements à traiter (ex: 75 93 13). Si non spécifié, traite tous. valeur par defaut 93",
    )
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Activer l’échantillonnage des fichiers CSV",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=2500,
        help="Nombre de lignes à échantillonner par defaut 2500 (si --sample est activé)",
    )
    args = parser.parse_args()

    main(args.departements, args.sample, args.sample_size)
