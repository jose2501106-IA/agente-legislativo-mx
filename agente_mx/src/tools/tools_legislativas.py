"""
Tools especializadas para AgenteMX — con URLs de fuente oficial
"""

import sqlite3
import pandas as pd
from pathlib import Path

DB_PATH = Path("agente_mx/data/agente_mx.db")

# URL base del sistema oficial
BASE_URL = "https://sitl.diputados.gob.mx/LXV_leg/listados_votacionesnplxv.php"


def url_votacion(partido_id: int, votacion_id: int) -> str:
    return f"{BASE_URL}?partidot={partido_id}&votaciont={votacion_id}"


PARTIDO_IDS = {
    "MC": 7, "Morena": 3,
    "PAN": 2, "PRD": 4, "PRI": 1, "PT": 6, "PVEM": 5
}


def buscar_diputado(nombre: str) -> tuple[str, list[dict]]:
    """
    Retorna (resumen_texto, lista_de_fuentes)
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        query = """
            SELECT diputado, partido, voto, votacion_id
            FROM votaciones
            WHERE LOWER(diputado) LIKE LOWER(:nombre)
            ORDER BY votacion_id
        """
        df = pd.read_sql(query, conn, params={"nombre": f"%{nombre}%"})
        conn.close()

        if df.empty:
            return f"No se encontró ningún diputado con el nombre '{nombre}'.", []

        diputado_nombre = df["diputado"].iloc[0]
        partido = df["partido"].iloc[0]
        total = len(df)
        a_favor = len(df[df["voto"] == "A favor"])
        en_contra = len(df[df["voto"] == "En contra"])
        ausente = len(df[df["voto"] == "Ausente"])
        abstencion = len(df[df["voto"] == "Abstención"])

        partido_id = PARTIDO_IDS.get(partido, 1)

        # Genera fuentes con URL por cada votación
        fuentes = []
        for _, row in df.iterrows():
            fuentes.append({
                "votacion_id": int(row["votacion_id"]),
                "url": url_votacion(partido_id, int(row["votacion_id"])),
                "label": f"Votación #{int(row['votacion_id'])} — {row['voto']}"
            })

        resumen = f"""
Diputado: {diputado_nombre}
Partido: {partido}
Total votaciones: {total}
- A favor: {a_favor}
- En contra: {en_contra}
- Ausente: {ausente}
- Abstención: {abstencion}

Detalle:
{df[['votacion_id', 'voto']].to_string(index=False)}
        """
        return resumen.strip(), fuentes

    except Exception as e:
        return f"Error: {e}", []


def resumen_por_partido(partido: str) -> tuple[str, list[dict]]:
    try:
        conn = sqlite3.connect(DB_PATH)
        partidos_df = pd.read_sql("SELECT DISTINCT partido FROM votaciones ORDER BY partido", conn)
        partidos_disponibles = partidos_df["partido"].tolist()

        partido_match = None
        for p in partidos_disponibles:
            if partido.lower() in p.lower():
                partido_match = p
                break

        if not partido_match:
            conn.close()
            return f"Partido '{partido}' no encontrado. Disponibles: {', '.join(partidos_disponibles)}", []

        stats = pd.read_sql(
            "SELECT voto, COUNT(*) as total FROM votaciones WHERE partido=:p GROUP BY voto ORDER BY total DESC",
            conn, params={"p": partido_match}
        )
        ausencias = pd.read_sql(
            """SELECT diputado, COUNT(*) as ausencias FROM votaciones
               WHERE partido=:p AND voto='Ausente'
               GROUP BY diputado ORDER BY ausencias DESC LIMIT 5""",
            conn, params={"p": partido_match}
        )
        disciplina = pd.read_sql(
            """SELECT diputado, COUNT(*) as votos_favor FROM votaciones
               WHERE partido=:p AND voto='A favor'
               GROUP BY diputado ORDER BY votos_favor DESC LIMIT 5""",
            conn, params={"p": partido_match}
        )
        votaciones_ids = pd.read_sql(
            "SELECT DISTINCT votacion_id FROM votaciones WHERE partido=:p ORDER BY votacion_id",
            conn, params={"p": partido_match}
        )
        conn.close()

        partido_id = PARTIDO_IDS.get(partido_match, 1)
        fuentes = [
            {
                "votacion_id": int(vid),
                "url": url_votacion(partido_id, int(vid)),
                "label": f"Votación #{int(vid)} — {partido_match}"
            }
            for vid in votaciones_ids["votacion_id"]
        ]

        resumen = f"""
Partido: {partido_match}
Distribución de votos:
{stats.to_string(index=False)}

Top 5 con más ausencias:
{ausencias.to_string(index=False) if not ausencias.empty else 'Sin datos'}

Top 5 más disciplinados:
{disciplina.to_string(index=False) if not disciplina.empty else 'Sin datos'}
        """
        return resumen.strip(), fuentes

    except Exception as e:
        return f"Error: {e}", []


def detectar_patrones(umbral_ausencias: int = 3) -> tuple[str, list[dict]]:
    try:
        conn = sqlite3.connect(DB_PATH)

        ausentes = pd.read_sql(f"""
            SELECT diputado, partido, COUNT(*) as ausencias
            FROM votaciones WHERE voto='Ausente'
            GROUP BY diputado, partido
            HAVING ausencias >= {umbral_ausencias}
            ORDER BY ausencias DESC LIMIT 10
        """, conn)

        divisivas = pd.read_sql("""
            SELECT votacion_id,
                   SUM(CASE WHEN voto='A favor' THEN 1 ELSE 0 END) as a_favor,
                   SUM(CASE WHEN voto='En contra' THEN 1 ELSE 0 END) as en_contra,
                   SUM(CASE WHEN voto='Ausente' THEN 1 ELSE 0 END) as ausentes
            FROM votaciones GROUP BY votacion_id
            HAVING en_contra > 0 ORDER BY en_contra DESC LIMIT 5
        """, conn)
        conn.close()

        # Fuentes de las votaciones divisivas
        fuentes = [
            {
                "votacion_id": int(row["votacion_id"]),
                "url": f"{BASE_URL}?partidot=1&votaciont={int(row['votacion_id'])}",
                "label": f"Votación #{int(row['votacion_id'])} — {int(row['en_contra'])} votos en contra"
            }
            for _, row in divisivas.iterrows()
        ]

        reporte = f"""
Diputados con {umbral_ausencias}+ ausencias:
{ausentes.to_string(index=False) if not ausentes.empty else 'Ninguno'}

Votaciones más divisivas:
{divisivas.to_string(index=False) if not divisivas.empty else 'Sin datos'}
        """
        return reporte.strip(), fuentes

    except Exception as e:
        return f"Error: {e}", []
