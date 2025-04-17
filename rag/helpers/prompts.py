from llama_index.core import PromptTemplate

# Prompt personnalisé pour le LLM (pour les requêtes RAG)
custom_prompt = PromptTemplate(
    """Vous êtes un assistant intelligent pour interroger la Base de Données Nationale des Bâtiments (BDNB).
    Répondez à la question suivante en utilisant les informations des documents fournis. Soyez précis, concis, et structurez votre réponse sous forme de liste ou de texte clair selon la nature de la question.
    Si la question demande une liste, fournissez les identifiants des bâtiments pertinents (batiment_groupe_id).
    Si la question demande une description, résumez les informations clés (localisation, type, surface, DPE, etc.).
    Question : {query_str}
    Documents : {context_str}
    Réponse :"""
)

# Prompt pour analyser les questions avec le LLM
analyze_prompt = PromptTemplate(
    """Vous êtes un assistant SQL intelligent pour la Base de Données Nationale des Bâtiments (BDNB).
    Votre tâche est d'analyser la question suivante et de déterminer si elle est quantitative (nécessitant un calcul agrégé comme une moyenne, un comptage, un pourcentage, etc.) ou descriptive (nécessitant une description ou une liste de bâtiments).
    Si la question est quantitative, générez une requête SQL précise pour répondre à la question en utilisant la table `buildings` décrite ci-dessous.
    Si la question est descriptive, retournez simplement un indicateur indiquant qu'aucune requête SQL n'est nécessaire.

    **Structure de la table `buildings`** :
    - batiment_groupe_id (TEXT) : Identifiant unique du bâtiment.
    - code_departement_insee (TEXT) : Code INSEE du département (ex. '69' pour Rhône).
    - libelle_commune_insee (TEXT) : Nom de la commune (ex. 'Lyon').
    - code_commune_insee (TEXT) : Code INSEE de la commune.
    - nom_quartier (TEXT) : Nom du quartier (peut être NULL).
    - is_residentiel (INTEGER) : 1 si résidentiel, 0 sinon.
    - is_tertiaire (INTEGER) : 1 si tertiaire, 0 sinon.
    - s_totale_bat (FLOAT) : Surface totale du bâtiment en m².
    - surface_category (TEXT) : Catégorie de surface (ex. 'petite', 'moyenne', 'grande').
    - annee_construction (FLOAT) : Année de construction.
    - avant_1948 (INTEGER) : 1 si construit avant 1948, 0 sinon.
    - avant_1975 (INTEGER) : 1 si construit avant 1975, 0 sinon.
    - nb_niveau (FLOAT) : Nombre de niveaux.
    - plus_de_5_etages (INTEGER) : 1 si plus de 5 étages, 0 sinon.
    - classe_bilan_dpe (TEXT) : Classe DPE (A, B, C, D, E, F, G, ou 'Non disponible').
    - is_passoire_thermique (INTEGER) : 1 si passoire thermique (DPE F ou G), 0 sinon.
    - qpv_indicateur (INTEGER) : 1 si en quartier prioritaire, 0 sinon.
    - arrondissement (TEXT) : Arrondissement (peut être 'Non applicable').

    **Instructions** :
    - Analysez la question : `{query_str}`.
    - Retournez une réponse au format JSON :
      - Si quantitative :
        ```json
        {
          "is_quantitative": true,
          "sql_query": "SELECT ... FROM buildings WHERE ...;"
        }
        ```
      - Si descriptive :
        ```json
        {
          "is_quantitative": false,
          "sql_query": null
        }
        ```
    - Assurez-vous que la requête SQL est valide, utilise les colonnes exactes de la table, et répond précisément à la question.
    - Si la question concerne un département ou une commune spécifique, incluez le filtre approprié (par exemple, `code_departement_insee = '69'` pour Rhône).
    - Si la question est ambiguë ou ne peut pas être traduite en SQL, retournez `"is_quantitative": false`.

    **Question** : {query_str}
    **Réponse** :

    IMPORTANT : Répondez UNIQUEMENT en JSON valide, sans texte supplémentaire ni markdown ```json```
    """
)

# Prompt pour formater les résultats SQL en réponse conviviale
format_sql_prompt = PromptTemplate(
    """Vous êtes un assistant intelligent pour la Base de Données Nationale des Bâtiments (BDNB).
    Votre tâche est de transformer les résultats d'une requête SQL en une réponse textuelle claire et conviviale pour l'utilisateur.
    La question posée par l'utilisateur est : `{query_str}`.
    Les résultats de la requête SQL sont : `{sql_results}` (au format JSON).

    **Instructions** :
    - Produisez une réponse en langage naturel qui répond directement à la question.
    - Utilisez les données fournies dans `sql_results` pour donner une réponse précise.
    - Soyez concis, clair et évitez le jargon technique.
    - Si les résultats sont une liste avec plusieurs lignes, résumez ou mentionnez les informations clés.
    - Si les résultats sont vides, indiquez poliment qu'aucune donnée n'a été trouvée.
    - Ne modifiez pas les données, mais présentez-les de manière compréhensible (par exemple, arrondissez les nombres si nécessaire).
    - Retournez UNIQUEMENT le texte de la réponse, sans JSON ou balises.

    **Exemples** :
    - Question : "Quelle est la surface moyenne des bâtiments tertiaires dans le Rhône ?"
      Résultats : [{"surface_moyenne": 1234.56}]
      Réponse : La surface moyenne des bâtiments tertiaires dans le Rhône est d'environ 1 235 m².
    - Question : "Combien de bâtiments résidentiels à Lyon sont classés G ?"
      Résultats : [{"nb_class_g": 150}]
      Réponse : Il y a 150 bâtiments résidentiels à Lyon classés G pour leur diagnostic de performance énergétique.
    - Question : "Quel est le nombre de passoires thermiques à Paris ?"
      Résultats : []
      Réponse : Aucune donnée disponible sur les passoires thermiques à Paris.

    **Question** : {query_str}
    **Résultats SQL** : {sql_results}
    **Réponse** :
    """
)