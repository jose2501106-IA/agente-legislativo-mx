"""
Scraper de votaciones nominales de la Cámara de Diputados de México
Fuente oficial: https://sitl.diputados.gob.mx
Legislatura LXV (2021-2024)
"""

import requests
import pandas as pd
from bs4 import BeautifulSoup
from pathlib import Path
from loguru import logger

# Rutas
RAW_DIR = Path("agente_mx/data/raw")
RAW_DIR.mkdir(parents=True, exist_ok=True)

# URL base del sistema de votaciones
BASE_URL = "https://sitl.diputados.gob.mx/LXV_leg/listados_votacionesnplxv.php"

# Partidos disponibles en el sistema (id: nombre)
PARTIDOS = {
    1: "PRI",
    2: "PAN",
    3: "Morena",
    4: "PRD",
    5: "PVEM",
    6: "PT",
    7: "MC",
    8: "Nueva Alianza",
}


def scrape_votacion(partido_id: int, votacion_id: int) -> list[dict]:
    """
    Descarga el listado de votos de un partido en una votación específica.
    Retorna una lista de diccionarios con nombre del diputado y sentido del voto.
    """
    params = {"partidot": partido_id, "votaciont": votacion_id}

    try:
        response = requests.get(BASE_URL, params=params, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")

        registros = []
        tabla = soup.find("table")
        if not tabla:
            return registros

        filas = tabla.find_all("tr")
        for fila in filas:
            celdas = fila.find_all("td")
            if len(celdas) >= 3:
                nombre = celdas[1].get_text(strip=True)
                voto = celdas[2].get_text(strip=True)
                if nombre and voto:
                    registros.append({
                        "partido": PARTIDOS.get(partido_id, f"Partido_{partido_id}"),
                        "diputado": nombre,
                        "voto": voto,
                        "votacion_id": votacion_id,
                    })
        return registros

    except Exception as e:
        logger.warning(f"Error en partido {partido_id}, votación {votacion_id}: {e}")
        return []


def descargar_votaciones(votacion_ids: list[int]) -> pd.DataFrame:
    """
    Descarga todas las votaciones indicadas para todos los partidos.
    """
    todos = []

    for votacion_id in votacion_ids:
        logger.info(f"Descargando votación #{votacion_id}...")
        for partido_id in PARTIDOS:
            registros = scrape_votacion(partido_id, votacion_id)
            todos.extend(registros)

    df = pd.DataFrame(todos)
    logger.success(f"Total de registros descargados: {len(df)}")
    return df


def guardar_votaciones(df: pd.DataFrame, nombre: str = "votaciones_raw.csv"):
    """Guarda el DataFrame en la carpeta raw."""
    if df.empty:
        logger.warning("No hay datos para guardar.")
        return
    ruta = RAW_DIR / nombre
    df.to_csv(ruta, index=False, encoding="utf-8-sig")
    logger.success(f"Datos guardados en: {ruta}")


if __name__ == "__main__":
    # Descargamos las primeras 5 votaciones como prueba
    votaciones_prueba = [42, 43, 44, 45, 46]

    df = descargar_votaciones(votaciones_prueba)

    if not df.empty:
        print("\n--- Vista previa ---")
        print(df.head(10))
        print(f"\nColumnas: {list(df.columns)}")
        print(f"Total registros: {len(df)}")
        print(f"\nDistribución de votos:\n{df['voto'].value_counts()}")
        guardar_votaciones(df)
    else:
        print("No se obtuvieron datos.")
