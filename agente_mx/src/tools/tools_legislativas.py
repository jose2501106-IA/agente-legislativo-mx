"""
Tools especializadas para AgenteMX — con URLs precisas de fuente oficial
"""

import sqlite3
import pandas as pd
from pathlib import Path
from agente_mx.src.utils.url_builder import (
    url_votacion_partido,
    url_buscar_diputado,
    url_todas_votaciones_partido,
    url_patrones_generales,
)

DB_PATH = Path("agente_mx/data/agente_mx.db")


def buscar_diputado(nombre: str) -> tuple[str, list[dict]]:
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

        fuentes = url_buscar_diputado(partido, df["votacion_id"].tolist())

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
        return resumen.strip(), fuentes

    except Exception as e:
        return f"Error al buscar diputado: {e}", []


def resumen_por_partido(partido: str) -> tuple[str, list[dict]]:
    try:
        conn = sqlite3.connect(DB_PATH)

        partidos_df = pd.read_sql(
            "SELECT DISTINCT partido FROM votaciones ORDER BY partido", conn
        )
        partidos_disponibles = [
            p for p in partidos_df["partido"].tolist()
            if p != "Nueva Alianza"
        ]

        partido_match = None
        for p in partidos_disponibles:
            if partido.lower() in p.lower():
                partido_match = p
                break

        if not partido_match:
            conn.close()
            return (
                f"Partido '{partido}' no encontrado. "
                f"Partidos disponibles: {', '.join(partidos_disponibles)}",
                []
            )

        stats = pd.read_sql(
            "SELECT voto, COUNT(*) as total FROM votaciones WHERE partido = :p GROUP BY voto ORDER BY total DESC",
            conn, params={"p": partido_match}
        )
        ausencias = pd.read_sql(
            """SELECT diputado, COUNT(*) as ausencias FROM votaciones
               WHERE partido = :p AND voto = 'Ausente'
               GROUP BY diputado ORDER BY ausencias DESC LIMIT 5""",
            conn, params={"p": partido_match}
        )
        disciplina = pd.read_sql(
            """SELECT diputado, COUNT(*) as votos_favor FROM votaciones
               WHERE partido = :p AND voto = 'A favor'
               GROUP BY diputado ORDER BY votos_favor DESC LIMIT 5""",
            conn, params={"p": partido_match}
        )
        votaciones_ids = pd.read_sql(
            "SELECT DISTINCT votacion_id FROM votaciones WHERE partido = :p ORDER BY votacion_id",
            conn, params={"p": partido_match}
        )
        conn.close()

        fuentes = [
            url_votacion_partido(partido_match, int(vid))
            for vid in votaciones_ids["votacion_id"].tolist()[:4]
        ]
        fuentes.append(url_todas_votaciones_partido(partido_match))

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
        return resumen.strip(), fuentes

    except Exception as e:
        return f"Error al generar resumen del partido: {e}", []


def detectar_patrones(umbral_ausencias: int = 3) -> tuple[str, list[dict]]:
    try:
        conn = sqlite3.connect(DB_PATH)

        ausentes = pd.read_sql(f"""
            SELECT diputado, partido, COUNT(*) as ausencias
            FROM votaciones
            WHERE voto = 'Ausente' AND partido != 'Nueva Alianza'
            GROUP BY diputado, partido
            HAVING ausencias >= {umbral_ausencias}
            ORDER BY ausencias DESC
            LIMIT 10
        """, conn)

        divisivas = pd.read_sql("""
            SELECT votacion_id,
                   SUM(CASE WHEN voto = 'A favor' THEN 1 ELSE 0 END) as a_favor,
                   SUM(CASE WHEN voto = 'En contra' THEN 1 ELSE 0 END) as en_contra,
                   SUM(CASE WHEN voto = 'Ausente' THEN 1 ELSE 0 END) as ausentes
            FROM votaciones
            GROUP BY votacion_id
            HAVING en_contra > 0
            ORDER BY en_contra DESC
            LIMIT 5
        """, conn)
        conn.close()

        fuentes = url_patrones_generales()
        for _, row in divisivas.iterrows():
            fuentes.append({
                "url": f"https://sitl.diputados.gob.mx/LXV_leg/listados_votacionesnplxv.php?partidot=1&votaciont={int(row['votacion_id'])}",
                "label": f"Votación #{int(row['votacion_id'])} — {int(row['en_contra'])} votos en contra · Registro oficial"
            })

        reporte = f"""
PATRONES DETECTADOS EN LA BASE DE DATOS
════════════════════════════════════════

Diputados con {umbral_ausencias} o más ausencias:
{ausentes.to_string(index=False) if not ausentes.empty else 'Ninguno con ese umbral'}

Votaciones más divisivas (con más votos en contra):
{divisivas.to_string(index=False) if not divisivas.empty else 'Sin datos'}
        """
        return reporte.strip(), fuentes

    except Exception as e:
        return f"Error al detectar patrones: {e}", []
