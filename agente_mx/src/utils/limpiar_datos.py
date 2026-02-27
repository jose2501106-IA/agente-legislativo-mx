"""
Limpieza y normalización de datos de votaciones
"""

import pandas as pd
from pathlib import Path
from loguru import logger

RAW_DIR = Path("agente_mx/data/raw")
PROCESSED_DIR = Path("agente_mx/data/processed")
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def limpiar_votaciones(nombre_archivo: str = "votaciones_raw.csv") -> pd.DataFrame:
    """
    Limpia y normaliza el CSV de votaciones descargado.
    """
    ruta = RAW_DIR / nombre_archivo

    if not ruta.exists():
        logger.error(f"No se encontró el archivo: {ruta}")
        return pd.DataFrame()

    logger.info("Cargando datos crudos...")
    df = pd.read_csv(ruta, encoding="utf-8-sig")

    logger.info(f"Registros antes de limpiar: {len(df)}")

    # 1. Eliminar filas vacías o duplicadas
    df.dropna(subset=["diputado", "voto"], inplace=True)
    df.drop_duplicates(inplace=True)

    # 2. Normalizar texto: quitar espacios extras y capitalizar
    df["diputado"] = df["diputado"].str.strip().str.title()
    df["partido"] = df["partido"].str.strip()
    df["voto"] = df["voto"].str.strip()

    # 3. Normalizar valores del voto a categorías consistentes
    mapa_votos = {
        "A Favor": "A favor",
        "a favor": "A favor",
        "En Contra": "En contra",
        "en contra": "En contra",
        "Ausente": "Ausente",
        "ausente": "Ausente",
        "Abstención": "Abstención",
        "abstención": "Abstención",
    }
    df["voto"] = df["voto"].replace(mapa_votos)

    # 4. Asegurar tipos de datos correctos
    df["votacion_id"] = df["votacion_id"].astype(int)

    logger.info(f"Registros después de limpiar: {len(df)}")
    logger.success("Limpieza completada.")

    return df


def guardar_procesado(df: pd.DataFrame, nombre: str = "votaciones_clean.csv"):
    """Guarda el DataFrame limpio en la carpeta processed."""
    ruta = PROCESSED_DIR / nombre
    df.to_csv(ruta, index=False, encoding="utf-8-sig")
    logger.success(f"Datos limpios guardados en: {ruta}")


if __name__ == "__main__":
    df = limpiar_votaciones()

    if not df.empty:
        print("\n--- Vista previa de datos limpios ---")
        print(df.head(10))
        print(f"\nDistribución de votos:\n{df['voto'].value_counts()}")
        print(f"\nPartidos presentes:\n{df['partido'].value_counts()}")
        guardar_procesado(df)
