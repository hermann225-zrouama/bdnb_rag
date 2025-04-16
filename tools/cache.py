import redis
import json

class ResponseCache:
    def __init__(self, host="localhost", port=6379, db=0):
        """
        Initialise le client Redis pour le cache.

        Args:
            host (str): Adresse de l'hôte Redis (par défaut: localhost).
            port (int): Port de Redis (par défaut: 6379).
            db (int): Base de données Redis à utiliser (par défaut: 0).
        """
        self.client = redis.Redis(host=host, port=port, db=db)
    
    def get(self, key: str):
        """
        Récupère une réponse du cache.

        Args:
            key (str): Clé de la requête (généralement la question posée).

        Returns:
            dict: Réponse mise en cache, ou None si non trouvée.
        """
        result = self.client.get(key)
        return json.loads(result) if result else None
    
    def set(self, key: str, value: dict, ttl: int = 3600):
        """
        Stocke une réponse dans le cache avec une durée de vie (TTL).

        Args:
            key (str): Clé de la requête.
            value (dict): Réponse à mettre en cache.
            ttl (int): Durée de vie en secondes (par défaut: 1 heure).
        """
        self.client.setex(key, ttl, json.dumps(value))