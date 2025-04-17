import re
import json


def get_collection_name(message: str, collection_name, logger) -> str | None:
    dept_match = re.search(r"département (\d+)", message.lower())
    if dept_match:
        dept = dept_match.group(1)
        logger.info(f"Detected department {dept} in query")
        return f"{collection_name}_{dept}"
    logger.info("No department detected, will use all available collections")
    return None


def analyze_question_with_llm(message: str, llm, analyze_prompt, logger) -> dict:
    """
    Utilise le LLM pour déterminer si la question est quantitative et générer une requête SQL.

    Args:
        message (str): Requête en langage naturel.
        llm: Instance du modèle LLM (Ollama).

    Returns:
        dict: Résultat avec 'is_quantitative' (bool) et 'sql_query' (str ou None).
    """
    try:
        # Générer la réponse du LLM avec le prompt d'analyse
        response = llm.complete(analyze_prompt.format(query_str=message))
        # Loguer la réponse brute
        logger.info(f"LLM response: {repr(str(response))}")
        raw_response = str(response).strip()

        # Supprimer les balises Markdown si présentes
        if raw_response.startswith("```json"):
            raw_response = raw_response[len("```json"):].strip()
        if raw_response.endswith("```"):
            raw_response = raw_response[:-3].strip()

        # Loguer la réponse nettoyée pour débogage
        logger.info(f"Cleaned LLM response: {repr(raw_response)}")
        
        # Vérifier si la réponse est un JSON valide
        try:
            result = json.loads(raw_response)
            logger.info(f"LLM analysis result: {result}")
            return result
        except json.JSONDecodeError:
            # Tenter une extraction regex pour récupérer un bloc JSON
            json_match = re.search(r'\{.*?\}', raw_response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(0))
                logger.info(f"Extracted JSON from response: {result}")
                return result
            else:
                raise json.JSONDecodeError("No valid JSON found", raw_response, 0)

    except json.JSONDecodeError as e:
        logger.error(f"Error parsing LLM response as JSON: {e}")
        return {"is_quantitative": False, "sql_query": None}
    except Exception as e:
        logger.error(f"Error analyzing question with LLM: {e}")
        return {"is_quantitative": False, "sql_query": None}


def format_sql_results_with_llm(message: str, sql_results: list, llm, format_sql_prompt, logger) -> str:
    """
    Formate les résultats SQL en une réponse textuelle conviviale en utilisant le LLM.

    Args:
        message (str): Question de l'utilisateur.
        sql_results (list): Résultats SQL sous forme de liste de dictionnaires.
        llm: Instance du modèle LLM (Ollama).

    Returns:
        str: Réponse textuelle conviviale, ou message par défaut en cas d'erreur.
    """
    try:
        # Vérifier que sql_results est une liste de dictionnaires
        if not isinstance(sql_results, list):
            logger.error(f"sql_results is not a list: {type(sql_results)}")
            return "Erreur : les données SQL ne sont pas dans le format attendu."
        
        # Convertir les résultats SQL en JSON pour le prompt
        sql_results_json = json.dumps(sql_results, ensure_ascii=False)
        # Générer la réponse avec le LLM
        response = llm.complete(
            format_sql_prompt.format(query_str=message, sql_results=sql_results_json)
        )
        friendly_response = str(response).strip()
        logger.info(f"Friendly response generated: {friendly_response}")
        return friendly_response
    except Exception as e:
        logger.error(f"Error formatting SQL results with LLM: {e}")
        return "Voici les données brutes, je n'ai pas pu les formater en texte clair."
