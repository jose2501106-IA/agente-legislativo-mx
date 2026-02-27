"""
Scraper expandido — descarga un rango amplio de votaciones
"""

import requests
import pandas as pd
from bs4 import BeautifulSoup
from pathlib import Path
from loguru import logger
import time

RAW_DIR = Path("agente_mx/data/raw")
RAW_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = "https://sitl.diputados.gob.mx/LXV_leg/listados_votacionesnplxv.php"

PARTIDOS = {
    1: "PRI", 2: "PAN", 3: "Morena",
    4: "PRD", 5: "PVEM", 6: "PT",
    7: "MC",
}


def scrape_votacion(partido_id: int, votacion_id: int) -> list[dict]:
    params = {"partidot": partido_id, "votaciont": votacion_id}
    try:
        response = requests.get(BASE_URL, params=params, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")
        registros = []
        tabla = soup.find("table")
        if not tabla:
            return registros
        for fila in tabla.find_all("tr"):
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
        logger.warning(f"Error partido {partido_id}, votación {votacion_id}: {e}")
        return []


def descargar_rango(inicio: int, fin: int, pausa: float = 0.3) -> pd.DataFrame:
    """
    Descarga todas las votaciones en el rango [inicio, fin].
    La pausa evita saturar el servidor oficial.
    """
    todos = []
    total = (fin - inicio + 1) * len(PARTIDOS)
    procesados = 0

    for votacion_id in range(inicio, fin + 1):
        registros_votacion = []
        for partido_id in PARTIDOS:
            registros = scrape_votacion(partido_id, votacion_id)
            registros_votacion.extend(registros)
            procesados += 1
            time.sleep(pausa)

        if registros_votacion:
            todos.extend(registros_votacion)
            logger.info(f"Votación #{votacion_id}: {len(registros_votacion)} registros | Progreso: {procesados}/{total}")
        else:
            logger.warning(f"Votación #{votacion_id}: sin datos")

    df = pd.DataFrame(todos)
    logger.success(f"Descarga completa. Total registros: {len(df)}")
    return df


if __name__ == "__main__":
    logger.info("Iniciando descarga expandida de votaciones LXV Legislatura...")

    # Descarga votaciones del 1 al 80
    # Puedes ampliar el rango después (ej. 1 a 200)
    df = descargar_rango(inicio=1, fin=80)

    if not df.empty:
        ruta = RAW_DIR / "votaciones_raw.csv"
        df.to_csv(ruta, index=False, encoding="utf-8-sig")
        logger.success(f"Guardado en {ruta}")
        print(f"\nTotal registros: {len(df)}")
        print(f"Votaciones únicas: {df['votacion_id'].nunique()}")
        print(f"Distribución de votos:\n{df['voto'].value_counts()}")
    else:
        print("No se obtuvieron datos.")
