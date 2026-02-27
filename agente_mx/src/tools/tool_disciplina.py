"""
Termómetro de Disciplina Partidista
Calcula qué tan alineado vota cada diputado con su partido
"""

import sqlite3
import pandas as pd
from pathlib import Path

DB_PATH = Path("agente_mx/data/agente_mx.db")
BASE_URL = "https://sitl.diputados.gob.mx/LXV_leg/listados_votacionesnplxv.php"

PARTIDO_IDS = {
    "MC": 7, "Morena": 3,
    "PAN": 2, "PRD": 4, "PRI": 1, "PT": 6, "PVEM": 5
}


def calcular_disciplina_partido(partido: str) -> tuple[str, list[dict]]:
    """
    Para cada votación, determina el voto mayoritario del partido (línea oficial).
    Luego calcula qué tan seguido cada diputado siguió esa línea.
    Retorna un índice de disciplina del 0 al 100 por diputado.
    """
    try:
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

        # Determina la línea oficial por votación (voto más frecuente del partido)
        linea_oficial = (
            df[df["voto"].isin(["A favor", "En contra", "Abstención"])]
            .groupby("votacion_id")["voto"]
            .agg(lambda x: x.value_counts().idxmax())
            .reset_index()
            .rename(columns={"voto": "linea_oficial"})
        )

        # Cruza con los votos individuales
        df_merged = df.merge(linea_oficial, on="votacion_id", how="left")

        # Calcula disciplina por diputado
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

        partido_id = PARTIDO_IDS.get(partido_match, 1)

        fuentes = [
            {
                "votacion_id": f"disciplina_{partido_match}",
                "url": f"{BASE_URL}?partidot={partido_id}&votaciont=1",
                "label": f"Votaciones nominales — {partido_match} · Cámara de Diputados LXV"
            }
        ]

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
    """
    Compara el índice de disciplina promedio entre todos los partidos.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        partidos = pd.read_sql(
            "SELECT DISTINCT partido FROM votaciones ORDER BY partido", conn
        )
        conn.close()

        # Filtra Nueva Alianza si quedara algún registro
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

        fuentes = [
            {
                "votacion_id": "comparativa_disciplina",
                "url": BASE_URL,
                "label": "Votaciones nominales — Todos los partidos · Cámara de Diputados LXV"
            }
        ]

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
