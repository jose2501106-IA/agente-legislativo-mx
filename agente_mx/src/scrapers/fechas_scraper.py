"""
Scraper de fechas de votaciones
Enriquece el dataset con la fecha real de cada votación
Fuente: sitl.diputados.gob.mx
"""

import requests
import pandas as pd
from bs4 import BeautifulSoup
from pathlib import Path
from loguru import logger
import time
import re
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

RAW_DIR = Path("agente_mx/data/raw")
BASE_URL = "https://sitl.diputados.gob.mx/LXV_leg/listados_votacionesnplxv.php"

# Fechas conocidas de la LXV Legislatura por período de sesiones
# Esto nos permite asignar fechas aproximadas por rango de votacion_id
PERIODOS_SESIONES = [
    {"inicio": 1,   "fin": 15,  "fecha": "2021-10-15", "periodo": "1er Periodo Ordinario 2021", "ano_electoral": False},
    {"inicio": 16,  "fin": 30,  "fecha": "2021-11-20", "periodo": "1er Periodo Ordinario 2021", "ano_electoral": False},
    {"inicio": 31,  "fin": 45,  "fecha": "2022-02-10", "periodo": "2do Periodo Ordinario 2022", "ano_electoral": False},
    {"inicio": 46,  "fin": 60,  "fecha": "2022-04-05", "periodo": "2do Periodo Ordinario 2022", "ano_electoral": False},
    {"inicio": 61,  "fin": 80,  "fecha": "2022-10-20", "periodo": "1er Periodo Ordinario 2022", "ano_electoral": False},
]

# Elecciones relevantes en México durante la LXV Legislatura
# Elecciones intermedias: junio 2024 (renovación de Cámara de Diputados)
# Elección presidencial: junio 2024
ANOS_ELECTORALES = [2024]
MESES_CAMPANA = {2024: [3, 4, 5, 6]}  # Meses de campaña activa


def asignar_contexto_electoral(votacion_id: int) -> dict:
    """
    Asigna fecha aproximada y contexto electoral a cada votación
    basándose en el período de sesiones correspondiente.
    """
    for periodo in PERIODOS_SESIONES:
        if periodo["inicio"] <= votacion_id <= periodo["fin"]:
            fecha = periodo["fecha"]
            ano = int(fecha.split("-")[0])
            mes = int(fecha.split("-")[1])

            es_ano_electoral = ano in ANOS_ELECTORALES
            es_periodo_campana = (
                ano in MESES_CAMPANA and
                mes in MESES_CAMPANA.get(ano, [])
            )

            return {
                "votacion_id": votacion_id,
                "fecha_aproximada": fecha,
                "periodo_sesiones": periodo["periodo"],
                "ano": ano,
                "mes": mes,
                "ano_electoral": es_ano_electoral,
                "periodo_campana": es_periodo_campana,
            }

    # Default para votaciones fuera del rango conocido
    return {
        "votacion_id": votacion_id,
        "fecha_aproximada": "2022-01-01",
        "periodo_sesiones": "Periodo no identificado",
        "ano": 2022,
        "mes": 1,
        "ano_electoral": False,
        "periodo_campana": False,
    }


def intentar_scrape_fecha(votacion_id: int) -> str:
    """
    Intenta obtener la fecha real de una votación desde el sitio oficial.
    Si falla, retorna la fecha aproximada por período.
    """
    try:
        url = f"{BASE_URL}?partidot=1&votaciont={votacion_id}"
        response = requests.get(url, verify=False, timeout=10)
        soup = BeautifulSoup(response.text, "lxml")

        # Busca patrones de fecha en el texto (dd-Mes-yyyy o dd/mm/yyyy)
        texto = soup.get_text()
        patrones = [
            r"\d{1,2}-(?:Enero|Febrero|Marzo|Abril|Mayo|Junio|Julio|Agosto|Septiembre|Octubre|Noviembre|Diciembre)-\d{4}",
            r"\d{1,2}/\d{1,2}/\d{4}",
        ]

        meses_es = {
            "Enero": "01", "Febrero": "02", "Marzo": "03",
            "Abril": "04", "Mayo": "05", "Junio": "06",
            "Julio": "07", "Agosto": "08", "Septiembre": "09",
            "Octubre": "10", "Noviembre": "11", "Diciembre": "12"
        }

        for patron in patrones:
            match = re.search(patron, texto)
            if match:
                fecha_raw = match.group()
                # Convierte formato dd-Mes-yyyy a yyyy-mm-dd
                for mes_es, mes_num in meses_es.items():
                    if mes_es in fecha_raw:
                        partes = fecha_raw.split("-")
                        if len(partes) == 3:
                            return f"{partes[2]}-{mes_num}-{partes[0].zfill(2)}"
                return fecha_raw

    except Exception:
        pass

    return None


def construir_catalogo_fechas(votacion_ids: list[int]) -> pd.DataFrame:
    """
    Construye catálogo completo de fechas para todas las votaciones.
    Intenta scraping real primero, usa aproximación si falla.
    """
    catalogo = []

    for vid in votacion_ids:
        contexto = asignar_contexto_electoral(vid)

        # Intenta obtener fecha real
        fecha_real = intentar_scrape_fecha(vid)
        if fecha_real:
            contexto["fecha_aproximada"] = fecha_real
            contexto["fecha_fuente"] = "scraping"
            logger.info(f"Votación #{vid}: fecha real = {fecha_real}")
        else:
            contexto["fecha_fuente"] = "estimada"
            logger.info(f"Votación #{vid}: fecha estimada = {contexto['fecha_aproximada']}")

        catalogo.append(contexto)
        time.sleep(0.2)

    return pd.DataFrame(catalogo)


if __name__ == "__main__":
    logger.info("Construyendo catálogo de fechas para 80 votaciones...")
    ids = list(range(1, 81))
    df = construir_catalogo_fechas(ids)

    print("\n--- Vista previa ---")
    print(df.head(10))
    print(f"\nFechas por fuente:\n{df['fecha_fuente'].value_counts()}")
    print(f"Años cubiertos: {sorted(df['ano'].unique())}")

    ruta = RAW_DIR / "fechas_votaciones.csv"
    df.to_csv(ruta, index=False, encoding="utf-8-sig")
    logger.success(f"Guardado en {ruta}")
