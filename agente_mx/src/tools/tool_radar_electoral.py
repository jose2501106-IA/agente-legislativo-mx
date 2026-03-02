"""
Radar Electoral — Fase 4C
Analiza si el comportamiento de voto de diputados cambia
en períodos electorales vs no electorales
"""

import sqlite3
import pandas as pd
from pathlib import Path
from loguru import logger
from agente_mx.src.utils.url_builder import (
    url_radar_electoral,
    url_comparativa_partidos,
)

DB_PATH = Path("agente_mx/data/agente_mx.db")
RAW_DIR = Path("agente_mx/data/raw")

PERIODOS_SESIONES = [
    {"inicio": 1,  "fin": 15, "fecha": "2021-10-15", "periodo": "1er Periodo Ordinario 2021", "ano_electoral": False},
    {"inicio": 16, "fin": 30, "fecha": "2021-11-20", "periodo": "1er Periodo Ordinario 2021", "ano_electoral": False},
    {"inicio": 31, "fin": 45, "fecha": "2022-02-10", "periodo": "2do Periodo Ordinario 2022", "ano_electoral": False},
    {"inicio": 46, "fin": 60, "fecha": "2022-04-05", "periodo": "2do Periodo Ordinario 2022", "ano_electoral": False},
    {"inicio": 61, "fin": 80, "fecha": "2022-10-20", "periodo": "1er Periodo Ordinario 2022", "ano_electoral": False},
]

ANOS_ELECTORALES = [2024]


def cargar_contexto_electoral() -> pd.DataFrame:
    ruta = RAW_DIR / "fechas_votaciones.csv"
    if not ruta.exists():
        return pd.DataFrame()
    return pd.read_csv(ruta, encoding="utf-8-sig")


def radar_electoral_partido(partido: str) -> tuple[str, list[dict]]:
    try:
        contexto_df = cargar_contexto_electoral()
        if contexto_df.empty:
            return "Ejecuta primero el scraper de fechas (fechas_scraper.py).", []

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
            return f"Partido '{partido}' no encontrado. Disponibles: {', '.join(partidos_disponibles)}", []

        votaciones_df = pd.read_sql(
            "SELECT diputado, partido, voto, votacion_id FROM votaciones WHERE partido = :p",
            conn, params={"p": partido_match}
        )
        conn.close()

        df = votaciones_df.merge(
            contexto_df[["votacion_id", "fecha_aproximada", "periodo_sesiones", "ano_electoral", "periodo_campana"]],
            on="votacion_id",
            how="left"
        )

        if df.empty:
            return "No hay datos suficientes para el análisis.", []

        electoral = df[df["ano_electoral"] == True]
        normal = df[df["ano_electoral"] == False]

        def calcular_stats(subset: pd.DataFrame, label: str) -> dict:
            if subset.empty:
                return {"periodo": label, "total_votos": 0, "pct_a_favor": 0, "pct_ausente": 0, "pct_en_contra": 0}
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

        diff_favor = stats_electoral.get("pct_a_favor", 0) - stats_normal.get("pct_a_favor", 0)
        diff_ausente = stats_electoral.get("pct_ausente", 0) - stats_normal.get("pct_ausente", 0)

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

        fuentes = url_radar_electoral(partido_match)

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

        return reporte.strip(), fuentes

    except Exception as e:
        return f"Error en radar electoral: {e}", []


def radar_comparativo_partidos() -> tuple[str, list[dict]]:
    try:
        contexto_df = cargar_contexto_electoral()
        if contexto_df.empty:
            return "Ejecuta primero el scraper de fechas.", []

        conn = sqlite3.connect(DB_PATH)
        partidos = pd.read_sql(
            "SELECT DISTINCT partido FROM votaciones ORDER BY partido", conn
        )
        conn.close()

        partidos_lista = [
            p for p in partidos["partido"].tolist()
            if p != "Nueva Alianza"
        ]

        resultados = []
        for partido in partidos_lista:
            reporte, _ = radar_electoral_partido(partido)
            for linea in reporte.split("\n"):
                if any(k in linea for k in ["AUMENTA", "REDUCE", "marginal", "significativos"]):
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
        fuentes = url_comparativa_partidos()

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
