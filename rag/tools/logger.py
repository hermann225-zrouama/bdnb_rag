import logging
from pathlib import Path

def setup_logger(name: str, log_file: str, level: int = logging.INFO) -> logging.Logger:
    """
    Configure un logger pour enregistrer les messages dans un fichier.

    Args:
        name (str): Nom du logger (généralement le nom du module).
        log_file (str): Chemin vers le fichier de log.
        level (int): Niveau de logging (par défaut: INFO).

    Returns:
        logging.Logger: Logger configuré.
    """
    # Créer le dossier parent si nécessaire
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)

    # Configurer le logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Supprimer les handlers existants pour éviter les doublons
    logger.handlers = []
    
    # Configurer le handler pour le fichier
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    ))
    logger.addHandler(file_handler)
    
    return logger