"""
Radar Electoral — Fase 4C
Analiza si el comportamiento de voto de diputados cambia
en períodos electorales vs no electorales
"""

import sqlite3
import pandas as pd
from pathlib import Path
from loguru import logger

DB_PATH = Path("agente_mx/data/agente_mx.db")
RAW_DIR = Path("agente_mx/data/raw")
BASE_URL = "https://sitl.diputados.gob.mx/LXV_leg/listados_votacionesnplxv.php"


def cargar_contexto_electoral() -> pd.DataFrame:
    """Carga el catálogo de fechas y contexto electoral."""
    ruta = RAW_DIR / "fechas_votaciones.csv"
    if not ruta.exists():
        return pd.DataFrame()
    return pd.read_csv(ruta, encoding="utf-8-sig")


def radar_electoral_partido(partido: str) -> tuple[str, list[dict]]:
    """
    Compara el comportamiento de votación de un partido
    en períodos electorales vs no electorales.
    """
    try:
        contexto_df = cargar_contexto_electoral()
        if contexto_df.empty:
            return "Ejecuta primero el scraper de fechas (paso 52).", []

        conn = sqlite3.connect(DB_PATH)
        partidos_df = pd.read_sql(
            "SELECT DISTINCT partido FROM votaciones ORDER BY partido", conn
        )
        partidos_disponibles = partidos_df["partido"].tolist()

        partido_match = None
        for p in partidos_disponibles:
            if partido.lower() in p.lower():
                partido_match = p
                break

        if not partido_match:
            conn.close()
            return f"Partido '{partido}' no encontrado. Disponibles: {', '.join(partidos_disponibles)}", []

        votaciones_df = pd.read_sql(
            "SELECT diputado, partido, voto, votacion_id FROM votaciones WHERE partido = :p",
            conn, params={"p": partido_match}
        )
        conn.close()

        # Une votaciones con contexto electoral
        df = votaciones_df.merge(
            contexto_df[["votacion_id", "fecha_aproximada", "periodo_sesiones", "ano_electoral", "periodo_campana"]],
            on="votacion_id",
            how="left"
        )

        if df.empty:
            return "No hay datos suficientes para el análisis.", []

        # Separa períodos electorales vs normales
        electoral = df[df["ano_electoral"] == True]
        normal = df[df["ano_electoral"] == False]

        def calcular_stats(subset: pd.DataFrame, label: str) -> dict:
            if subset.empty:
                return {"periodo": label, "total": 0}
            total = len(subset)
            a_favor = len(subset[subset["voto"] == "A favor"])
            ausente = len(subset[subset["voto"] == "Ausente"])
            en_contra = len(subset[subset["voto"] == "En contra"])
            return {
                "periodo": label,
                "total_votos": total,
                "pct_a_favor": round((a_favor / total) * 100, 1),
                "pct_ausente": round((ausente / total) * 100, 1),
                "pct_en_contra": round((en_contra / total) * 100, 1),
            }

        stats_normal = calcular_stats(normal, "Periodo normal")
        stats_electoral = calcular_stats(electoral, "Periodo electoral")

        # Calcula diferencias
        diff_favor = stats_electoral.get("pct_a_favor", 0) - stats_normal.get("pct_a_favor", 0)
        diff_ausente = stats_electoral.get("pct_ausente", 0) - stats_normal.get("pct_ausente", 0)

        # Interpreta el cambio
        if abs(diff_favor) < 1 and abs(diff_ausente) < 1:
            interpretacion = "No se detectan cambios significativos de comportamiento en período electoral."
        elif diff_ausente < -2:
            interpretacion = f"El partido REDUCE sus ausencias en período electoral ({diff_ausente:+.1f}%), lo que sugiere mayor activismo legislativo ante las elecciones."
        elif diff_ausente > 2:
            interpretacion = f"El partido AUMENTA sus ausencias en período electoral ({diff_ausente:+.1f}%), posiblemente por actividad de campaña."
        elif diff_favor > 2:
            interpretacion = f"El partido vota MÁS A FAVOR en período electoral ({diff_favor:+.1f}%), posible estrategia de imagen pública."
        else:
            interpretacion = f"Cambio marginal en comportamiento electoral (diferencia de {diff_favor:+.1f}% en votos a favor)."

        # Diputados con más cambio de comportamiento
        cambios_individuales = []
        for diputado in df["diputado"].unique():
            d_normal = df[(df["diputado"] == diputado) & (df["ano_electoral"] == False)]
            d_electoral = df[(df["diputado"] == diputado) & (df["ano_electoral"] == True)]

            if len(d_normal) > 0 and len(d_electoral) > 0:
                aus_normal = len(d_normal[d_normal["voto"] == "Ausente"]) / len(d_normal) * 100
                aus_electoral = len(d_electoral[d_electoral["voto"] == "Ausente"]) / len(d_electoral) * 100
                cambio = aus_electoral - aus_normal
                cambios_individuales.append({
                    "diputado": diputado,
                    "ausencias_normal_%": round(aus_normal, 1),
                    "ausencias_electoral_%": round(aus_electoral, 1),
                    "cambio_%": round(cambio, 1),
                })

        cambios_df = pd.DataFrame(cambios_individuales)
        if not cambios_df.empty:
            cambios_df = cambios_df.sort_values("cambio_%", ascending=False)

        stats_df = pd.DataFrame([stats_normal, stats_electoral])

        reporte = f"""
RADAR ELECTORAL — {partido_match}
{'═' * 55}

Comparativa de comportamiento por período:
{stats_df.to_string(index=False)}

Interpretación:
{interpretacion}

{'─' * 55}
Diputados con mayor cambio de comportamiento electoral:
{cambios_df.head(5).to_string(index=False) if not cambios_df.empty else 'Datos insuficientes para análisis individual'}
        """

        fuentes = [
            {
                "votacion_id": "radar",
                "url": BASE_URL,
                "label": f"Votaciones nominales {partido_match} — Cámara de Diputados LXV"
            },
            {
                "votacion_id": "ine",
                "url": "https://www.ine.mx/voto-y-elecciones/elecciones-2024/",
                "label": "INE — Elecciones 2024"
            }
        ]

        return reporte.strip(), fuentes

    except Exception as e:
        return f"Error en radar electoral: {e}", []


def radar_comparativo_partidos() -> tuple[str, list[dict]]:
    """
    Compara cómo cambia el comportamiento de TODOS los partidos
    en período electoral vs normal.
    """
    try:
        contexto_df = cargar_contexto_electoral()
        if contexto_df.empty:
            return "Ejecuta primero el scraper de fechas.", []

        conn = sqlite3.connect(DB_PATH)
        partidos = pd.read_sql(
            "SELECT DISTINCT partido FROM votaciones ORDER BY partido", conn
        )["partido"].tolist()
        conn.close()

        resultados = []
        for partido in partidos:
            reporte, _ = radar_electoral_partido(partido)
            # Extrae datos clave del reporte
            for linea in reporte.split("\n"):
                if "AUMENTA" in linea or "REDUCE" in linea or "marginal" in linea or "significativos" in linea:
                    resultados.append({
                        "partido": partido,
                        "comportamiento_electoral": linea.strip()
                    })
                    break
            else:
                resultados.append({
                    "partido": partido,
                    "comportamiento_electoral": "Sin cambio detectable"
                })

        df = pd.DataFrame(resultados)

        fuentes = [{
            "votacion_id": "comparativo",
            "url": BASE_URL,
            "label": "Radar Electoral Comparativo — Todos los partidos LXV"
        }]

        reporte = f"""
RADAR ELECTORAL COMPARATIVO — TODOS LOS PARTIDOS
{'═' * 55}

{df.to_string(index=False)}

Nota: Análisis basado en votaciones de la LXV Legislatura (2021-2024).
Las elecciones de referencia son las federales de junio 2024.
        """

        return reporte.strip(), fuentes

    except Exception as e:
        return f"Error en radar comparativo: {e}", []
