"""
Tools especializadas para el agente AgenteMX
"""

import sqlite3
import pandas as pd
from pathlib import Path

DB_PATH = Path("agente_mx/data/agente_mx.db")


def buscar_diputado(nombre: str) -> str:
    """
    Busca un diputado por nombre (búsqueda parcial) y devuelve
    su historial completo de votaciones.
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
            return f"No se encontró ningún diputado con el nombre '{nombre}'."

        diputado_nombre = df["diputado"].iloc[0]
        partido = df["partido"].iloc[0]
        total = len(df)
        a_favor = len(df[df["voto"] == "A favor"])
        en_contra = len(df[df["voto"] == "En contra"])
        ausente = len(df[df["voto"] == "Ausente"])
        abstencion = len(df[df["voto"] == "Abstención"])

        resumen = f"""
Diputado: {diputado_nombre}
Partido: {partido}
Total de votaciones registradas: {total}
- A favor: {a_favor}
- En contra: {en_contra}
- Ausente: {ausente}
- Abstención: {abstencion}

Detalle por votación:
{df[['votacion_id', 'voto']].to_string(index=False)}
        """
        return resumen.strip()

    except Exception as e:
        return f"Error al buscar diputado: {e}"


def resumen_por_partido(partido: str) -> str:
    """
    Genera un resumen detallado del comportamiento de votación
    de todos los diputados de un partido específico.
    """
    try:
        conn = sqlite3.connect(DB_PATH)

        # Verifica que el partido existe
        partidos_query = "SELECT DISTINCT partido FROM votaciones ORDER BY partido"
        partidos_df = pd.read_sql(partidos_query, conn)
        partidos_disponibles = partidos_df["partido"].tolist()

        partido_match = None
        for p in partidos_disponibles:
            if partido.lower() in p.lower():
                partido_match = p
                break

        if not partido_match:
            conn.close()
            return f"Partido '{partido}' no encontrado. Partidos disponibles: {', '.join(partidos_disponibles)}"

        # Estadísticas generales del partido
        stats_query = """
            SELECT voto, COUNT(*) as total
            FROM votaciones
            WHERE partido = :partido
            GROUP BY voto
            ORDER BY total DESC
        """
        stats = pd.read_sql(stats_query, conn, params={"partido": partido_match})

        # Diputados con más ausencias
        ausencias_query = """
            SELECT diputado, COUNT(*) as ausencias
            FROM votaciones
            WHERE partido = :partido AND voto = 'Ausente'
            GROUP BY diputado
            ORDER BY ausencias DESC
            LIMIT 5
        """
        ausencias = pd.read_sql(ausencias_query, conn, params={"partido": partido_match})

        # Diputados más disciplinados (más votos a favor)
        disciplina_query = """
            SELECT diputado, COUNT(*) as votos_favor
            FROM votaciones
            WHERE partido = :partido AND voto = 'A favor'
            GROUP BY diputado
            ORDER BY votos_favor DESC
            LIMIT 5
        """
        disciplina = pd.read_sql(disciplina_query, conn, params={"partido": partido_match})

        conn.close()

        resumen = f"""
Partido: {partido_match}
─────────────────────────────
Distribución de votos:
{stats.to_string(index=False)}

Top 5 diputados con más ausencias:
{ausencias.to_string(index=False) if not ausencias.empty else 'Sin datos'}

Top 5 diputados más disciplinados (más votos a favor):
{disciplina.to_string(index=False) if not disciplina.empty else 'Sin datos'}
        """
        return resumen.strip()

    except Exception as e:
        return f"Error al generar resumen del partido: {e}"


def detectar_patrones(umbral_ausencias: int = 3) -> str:
    """
    Detecta patrones relevantes en los datos:
    - Diputados con alta tasa de ausencias
    - Partidos con más votos en contra
    - Votaciones más polémicas (más votos divididos)
    """
    try:
        conn = sqlite3.connect(DB_PATH)

        # Diputados con muchas ausencias
        ausentes_query = f"""
            SELECT diputado, partido, COUNT(*) as ausencias
            FROM votaciones
            WHERE voto = 'Ausente'
            GROUP BY diputado, partido
            HAVING ausencias >= {umbral_ausencias}
            ORDER BY ausencias DESC
            LIMIT 10
        """
        ausentes = pd.read_sql(ausentes_query, conn)

        # Votaciones más divididas (con votos en contra)
        divisivas_query = """
            SELECT votacion_id,
                   SUM(CASE WHEN voto = 'A favor' THEN 1 ELSE 0 END) as a_favor,
                   SUM(CASE WHEN voto = 'En contra' THEN 1 ELSE 0 END) as en_contra,
                   SUM(CASE WHEN voto = 'Ausente' THEN 1 ELSE 0 END) as ausentes
            FROM votaciones
            GROUP BY votacion_id
            HAVING en_contra > 0
            ORDER BY en_contra DESC
            LIMIT 5
        """
        divisivas = pd.read_sql(divisivas_query, conn)

        conn.close()

        reporte = f"""
PATRONES DETECTADOS EN LA BASE DE DATOS
════════════════════════════════════════

Diputados con {umbral_ausencias} o más ausencias:
{ausentes.to_string(index=False) if not ausentes.empty else 'Ninguno con ese umbral'}

Votaciones más divisivas (con más votos en contra):
{divisivas.to_string(index=False) if not divisivas.empty else 'Sin datos'}
        """
        return reporte.strip()

    except Exception as e:
        return f"Error al detectar patrones: {e}"
