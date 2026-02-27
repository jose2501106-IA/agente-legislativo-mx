"""
Carga de datos limpios a base de datos SQLite
"""

import sqlite3
import pandas as pd
from pathlib import Path
from loguru import logger

PROCESSED_DIR = Path("agente_mx/data/processed")
DB_PATH = Path("agente_mx/data/agente_mx.db")


def cargar_a_sqlite(nombre_csv: str = "votaciones_clean.csv"):
    """
    Lee el CSV limpio y lo carga en una tabla SQLite.
    """
    ruta_csv = PROCESSED_DIR / nombre_csv

    if not ruta_csv.exists():
        logger.error(f"No se encontró: {ruta_csv}")
        return

    logger.info("Cargando CSV limpio...")
    df = pd.read_csv(ruta_csv, encoding="utf-8-sig")

    logger.info(f"Conectando a la base de datos: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)

    # Carga la tabla, reemplaza si ya existe
    df.to_sql("votaciones", conn, if_exists="replace", index=False)

    # Crea índices para búsquedas rápidas
    cursor = conn.cursor()
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_partido ON votaciones(partido)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_diputado ON votaciones(diputado)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_voto ON votaciones(voto)")
    conn.commit()

    # Verificación rápida
    total = pd.read_sql("SELECT COUNT(*) as total FROM votaciones", conn).iloc[0]["total"]
    logger.success(f"Base de datos lista. Total de registros: {total}")

    conn.close()


def consulta_prueba():
    """
    Ejecuta consultas de prueba para verificar que todo funciona.
    """
    conn = sqlite3.connect(DB_PATH)

    print("\n--- Top 5 diputados con más ausencias ---")
    query_ausencias = """
        SELECT diputado, partido, COUNT(*) as ausencias
        FROM votaciones
        WHERE voto = 'Ausente'
        GROUP BY diputado, partido
        ORDER BY ausencias DESC
        LIMIT 5
    """
    print(pd.read_sql(query_ausencias, conn))

    print("\n--- Votos por partido ---")
    query_partidos = """
        SELECT partido, voto, COUNT(*) as total
        FROM votaciones
        GROUP BY partido, voto
        ORDER BY partido, total DESC
    """
    print(pd.read_sql(query_partidos, conn))

    conn.close()


if __name__ == "__main__":
    cargar_a_sqlite()
    consulta_prueba()
