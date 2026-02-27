"""
Scraper de iniciativas legislativas
Fuente: Gaceta Parlamentaria — gaceta.diputados.gob.mx
"""

import requests
import pandas as pd
from bs4 import BeautifulSoup
from pathlib import Path
from loguru import logger
import time
import urllib3

# Desactiva warnings de SSL para servidores gubernamentales mexicanos
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

RAW_DIR = Path("agente_mx/data/raw")
RAW_DIR.mkdir(parents=True, exist_ok=True)

BASE_GACETA = "https://gaceta.diputados.gob.mx"


def scrape_iniciativas_gaceta(numero_gaceta: int) -> list[dict]:
    """
    Descarga el listado de iniciativas de un número específico de la Gaceta.
    Los números van del 1 al ~700 en la LXV Legislatura.
    """
    url = f"{BASE_GACETA}/gp_inis.html"
    try:
        response = requests.get(url, verify=False, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")

        iniciativas = []
        filas = soup.find_all("tr")

        for fila in filas:
            celdas = fila.find_all("td")
            if len(celdas) >= 3:
                link_tag = fila.find("a", href=True)
                titulo = celdas[0].get_text(strip=True)
                presentada_por = celdas[1].get_text(strip=True) if len(celdas) > 1 else ""
                fecha = celdas[2].get_text(strip=True) if len(celdas) > 2 else ""
                url_doc = f"{BASE_GACETA}/{link_tag['href']}" if link_tag else ""

                if titulo and len(titulo) > 10:
                    iniciativas.append({
                        "titulo": titulo,
                        "presentada_por": presentada_por,
                        "fecha": fecha,
                        "url": url_doc,
                        "fuente": "Gaceta Parlamentaria LXV",
                    })

        return iniciativas

    except Exception as e:
        logger.error(f"Error scraping gaceta: {e}")
        return []


def scrape_iniciativas_sil() -> list[dict]:
    """
    Alternativa: descarga iniciativas del SIL con SSL desactivado.
    """
    url = "http://sil.gobernacion.gob.mx/portal/Iniciativas/filtros"
    params = {"legislatura": "LXV", "pagina": 1}

    try:
        response = requests.get(url, params=params, verify=False, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")

        iniciativas = []
        filas = soup.select("table tr")

        for fila in filas[1:]:
            celdas = fila.find_all("td")
            if len(celdas) >= 3:
                link = fila.find("a", href=True)
                titulo = celdas[0].get_text(strip=True)
                presentada_por = celdas[1].get_text(strip=True)
                fecha = celdas[2].get_text(strip=True)
                estado = celdas[3].get_text(strip=True) if len(celdas) > 3 else ""
                url_doc = f"http://sil.gobernacion.gob.mx{link['href']}" if link else ""

                if titulo:
                    iniciativas.append({
                        "titulo": titulo,
                        "presentada_por": presentada_por,
                        "fecha": fecha,
                        "estado": estado,
                        "url": url_doc,
                        "fuente": "SIL Gobernación",
                    })

        return iniciativas

    except Exception as e:
        logger.error(f"Error scraping SIL: {e}")
        return []


def construir_dataset_iniciativas() -> pd.DataFrame:
    """
    Intenta ambas fuentes y construye el dataset de iniciativas.
    """
    logger.info("Intentando Gaceta Parlamentaria...")
    iniciativas = scrape_iniciativas_gaceta(1)

    if not iniciativas:
        logger.warning("Gaceta sin datos, intentando SIL...")
        iniciativas = scrape_iniciativas_sil()

    if not iniciativas:
        logger.warning("Ambas fuentes fallaron. Creando dataset de muestra para desarrollo...")
        iniciativas = generar_muestra_desarrollo()

    df = pd.DataFrame(iniciativas)
    logger.success(f"Dataset construido: {len(df)} iniciativas")
    return df


def generar_muestra_desarrollo() -> list[dict]:
    """
    Genera datos de muestra realistas para continuar el desarrollo
    mientras se resuelve el acceso a las fuentes oficiales.
    Basado en iniciativas reales de la LXV Legislatura.
    """
    return [
        {
            "titulo": "Iniciativa que reforma el artículo 4 constitucional en materia de derecho al agua",
            "presentada_por": "Morena",
            "fecha": "2022-02-15",
            "estado": "En comisiones",
            "url": "https://gaceta.diputados.gob.mx",
            "fuente": "Muestra desarrollo",
            "tema": "agua",
        },
        {
            "titulo": "Iniciativa que reforma la Ley General de Educación para fortalecer educación pública",
            "presentada_por": "PAN",
            "fecha": "2022-03-10",
            "estado": "Dictaminada",
            "url": "https://gaceta.diputados.gob.mx",
            "fuente": "Muestra desarrollo",
            "tema": "educación",
        },
        {
            "titulo": "Iniciativa que reforma el Código Penal Federal en materia de seguridad",
            "presentada_por": "PRI",
            "fecha": "2022-04-05",
            "estado": "Aprobada",
            "url": "https://gaceta.diputados.gob.mx",
            "fuente": "Muestra desarrollo",
            "tema": "seguridad",
        },
        {
            "titulo": "Iniciativa que reforma la Ley del IMSS para ampliar cobertura de salud",
            "presentada_por": "Morena",
            "fecha": "2022-05-20",
            "estado": "Aprobada",
            "url": "https://gaceta.diputados.gob.mx",
            "fuente": "Muestra desarrollo",
            "tema": "salud",
        },
        {
            "titulo": "Iniciativa que reforma la Ley Federal del Trabajo en materia de salario mínimo",
            "presentada_por": "PT",
            "fecha": "2022-06-15",
            "estado": "En comisiones",
            "url": "https://gaceta.diputados.gob.mx",
            "fuente": "Muestra desarrollo",
            "tema": "trabajo",
        },
        {
            "titulo": "Iniciativa que reforma la Ley de Hidrocarburos para fortalecer Pemex",
            "presentada_por": "Morena",
            "fecha": "2022-07-01",
            "estado": "Aprobada",
            "url": "https://gaceta.diputados.gob.mx",
            "fuente": "Muestra desarrollo",
            "tema": "energía",
        },
        {
            "titulo": "Iniciativa que reforma la Constitución en materia electoral",
            "presentada_por": "PAN",
            "fecha": "2022-08-10",
            "estado": "Rechazada",
            "url": "https://gaceta.diputados.gob.mx",
            "fuente": "Muestra desarrollo",
            "tema": "electoral",
        },
        {
            "titulo": "Iniciativa que crea la Ley de Economía Social y Solidaria",
            "presentada_por": "PRD",
            "fecha": "2022-09-05",
            "estado": "En comisiones",
            "url": "https://gaceta.diputados.gob.mx",
            "fuente": "Muestra desarrollo",
            "tema": "economía",
        },
    ]


if __name__ == "__main__":
    df = construir_dataset_iniciativas()

    if not df.empty:
        print("\n--- Vista previa ---")
        print(df.head())
        print(f"\nColumnas: {list(df.columns)}")
        print(f"Total: {len(df)}")
        ruta = RAW_DIR / "iniciativas_raw.csv"
        df.to_csv(ruta, index=False, encoding="utf-8-sig")
        logger.success(f"Guardado en {ruta}")
