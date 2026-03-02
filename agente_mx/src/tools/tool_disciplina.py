"""
Termómetro de Disciplina Partidista
Calcula qué tan alineado vota cada diputado con su partido
"""

import sqlite3
import pandas as pd
from pathlib import Path
from agente_mx.src.utils.url_builder import (
    url_disciplina_partido,
    url_comparativa_partidos,
)

DB_PATH = Path("agente_mx/data/agente_mx.db")


def calcular_disciplina_partido(partido: str) -> tuple[str, list[dict]]:
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
                f"Partido '{partido}' no encontrado. Disponibles: {', '.join(partidos_disponibles)}",
                []
            )

        df = pd.read_sql(
            "SELECT diputado, voto, votacion_id FROM votaciones WHERE partido = :p",
            conn, params={"p": partido_match}
        )
        conn.close()

        if df.empty:
            return "No hay datos para ese partido.", []

        linea_oficial = (
            df[df["voto"].isin(["A favor", "En contra", "Abstención"])]
            .groupby("votacion_id")["voto"]
            .agg(lambda x: x.value_counts().idxmax())
            .reset_index()
            .rename(columns={"voto": "linea_oficial"})
        )

        df_merged = df.merge(linea_oficial, on="votacion_id", how="left")

        resultados = []
        for diputado, grupo in df_merged.groupby("diputado"):
            total = len(grupo[grupo["voto"].isin(["A favor", "En contra", "Abstención"])])
            if total == 0:
                continue
            alineados = len(grupo[grupo["voto"] == grupo["linea_oficial"]])
            ausencias = len(grupo[grupo["voto"] == "Ausente"])
            indice = round((alineados / total) * 100, 1)

            clasificacion = (
                "🟢 Muy disciplinado" if indice >= 90 else
                "🟡 Moderado" if indice >= 70 else
                "🔴 Disidente"
            )

            resultados.append({
                "diputado": diputado,
                "disciplina_%": indice,
                "alineado": alineados,
                "ausencias": ausencias,
                "total_votaciones": len(grupo),
                "clasificacion": clasificacion,
            })

        resultado_df = pd.DataFrame(resultados).sort_values(
            "disciplina_%", ascending=True
        )

        promedio = round(resultado_df["disciplina_%"].mean(), 1)
        muy_disciplinados = len(resultado_df[resultado_df["disciplina_%"] >= 90])
        disidentes = len(resultado_df[resultado_df["disciplina_%"] < 70])
        top_disidentes = resultado_df.head(5)
        top_disciplinados = resultado_df.tail(5).iloc[::-1]

        fuentes = url_disciplina_partido(partido_match)

        reporte = f"""
TERMÓMETRO DE DISCIPLINA PARTIDISTA — {partido_match}
══════════════════════════════════════════════════════

Índice promedio del partido: {promedio}%
Diputados muy disciplinados (≥90%): {muy_disciplinados}
Diputados disidentes (<70%): {disidentes}

🔴 TOP 5 DISIDENTES (más votos fuera de la línea del partido):
{top_disidentes[['diputado', 'disciplina_%', 'clasificacion']].to_string(index=False)}

🟢 TOP 5 MÁS DISCIPLINADOS:
{top_disciplinados[['diputado', 'disciplina_%', 'clasificacion']].to_string(index=False)}

Ranking completo:
{resultado_df[['diputado', 'disciplina_%', 'ausencias', 'clasificacion']].to_string(index=False)}
        """

        return reporte.strip(), fuentes

    except Exception as e:
        return f"Error al calcular disciplina: {e}", []


def comparar_disciplina_partidos() -> tuple[str, list[dict]]:
    try:
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
            reporte, _ = calcular_disciplina_partido(partido)
            for linea in reporte.split("\n"):
                if "Índice promedio" in linea:
                    try:
                        promedio = float(linea.split(":")[1].strip().replace("%", ""))
                        resultados.append({
                            "partido": partido,
                            "disciplina_promedio_%": promedio
                        })
                    except Exception:
                        pass
                    break

        df = pd.DataFrame(resultados).sort_values(
            "disciplina_promedio_%", ascending=False
        )

        fuentes = url_comparativa_partidos()

        reporte = f"""
COMPARATIVA DE DISCIPLINA ENTRE PARTIDOS
══════════════════════════════════════════
{df.to_string(index=False)}

El partido más disciplinado es {df.iloc[0]['partido']} con {df.iloc[0]['disciplina_promedio_%']}%
El partido menos disciplinado es {df.iloc[-1]['partido']} con {df.iloc[-1]['disciplina_promedio_%']}%
        """
        return reporte.strip(), fuentes

    except Exception as e:
        return f"Error en comparativa: {e}", []
