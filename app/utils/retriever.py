import os
import requests
from typing import List, Dict
from dotenv import load_dotenv
from pathlib import Path
import logging
from app.core.config import settings

# Configure logging
logger = logging.getLogger(__name__)

# Cargar el .env desde la carpeta backend
load_dotenv(str(Path(__file__).resolve().parent.parent.parent / ".env"))

if not settings.SERPER_API_KEY:
    logger.error("No se encontró SERPER_API_KEY en el entorno. Verificá tu archivo .env.")
    raise ValueError("No se encontró SERPER_API_KEY en el entorno. Verificá tu archivo .env.")

def search_web(query: str, num_results: int = 5) -> List[Dict[str, str]]:
    """
    Realiza una búsqueda web usando Serper.dev y devuelve una lista de resultados relevantes.
    
    Args:
        query (str): Consulta de búsqueda.
        num_results (int): Cantidad de resultados deseados (máx sugerido: 10).
    
    Returns:
        List[Dict[str, str]]: Lista de resultados con 'title', 'snippet' y 'url'.
    """
    headers = {
        "X-API-KEY": settings.SERPER_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "q": query,
        "num": num_results,
    }

    try:
        logger.info(f"Enviando búsqueda a Serper.dev: {query}")
        response = requests.post(settings.SERPER_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        results = data.get("organic", [])

        if not results:
            logger.warning("No se encontraron resultados en la búsqueda")
            return []

        logger.info(f"Se encontraron {len(results)} resultados")
        return [
            {
                "title": r.get("title", ""),
                "snippet": r.get("snippet", ""),
                "url": r.get("link", "")
            }
            for r in results
        ]

    except requests.RequestException as e:
        logger.error(f"Error al consultar Serper.dev: {str(e)}", exc_info=True)
        return []