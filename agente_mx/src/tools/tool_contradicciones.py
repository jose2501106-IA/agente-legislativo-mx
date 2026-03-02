"""
Detector de Contradicciones — Fase 4B
Cruza iniciativas presentadas por partidos con sus votaciones reales
y usa Claude para detectar inconsistencias semánticas
"""

import sqlite3
import pandas as pd
import anthropic
from pathlib import Path
from dotenv import load_dotenv
from agente_mx.src.utils.url_builder import url_contradicciones

load_dotenv()

DB_PATH = Path("agente_mx/data/agente_mx.db")
RAW_DIR = Path("agente_mx/data/raw")

TEMAS_KEYWORDS = {
    "seguridad": ["seguridad", "penal", "delito", "crimen", "policía", "fuerzas armadas"],
    "educación": ["educación", "escuela", "maestro", "enseñanza", "universitaria"],
    "salud": ["salud", "imss", "issste", "hospital", "médico", "enfermedad"],
    "energía": ["pemex", "cfe", "hidrocarburos", "electricidad", "energía"],
    "electoral": ["electoral", "elección", "voto", "ine", "partido"],
    "trabajo": ["trabajo", "salario", "trabajador", "laboral", "empleo"],
    "agua": ["agua", "hidráulico", "sequía", "recurso hídrico"],
    "economía": ["economía", "fiscal", "impuesto", "presupuesto", "deuda"],
}


def cargar_iniciativas() -> pd.DataFrame:
    ruta = RAW_DIR / "iniciativas_raw.csv"
    if not ruta.exists():
        return pd.DataFrame()
    return pd.read_csv(ruta, encoding="utf-8-sig")


def detectar_tema(titulo: str) -> str:
    titulo_lower = titulo.lower()
    for tema, keywords in TEMAS_KEYWORDS.items():
        if any(k in titulo_lower for k in keywords):
            return tema
    return "general"


def analizar_contradiccion_con_ia(
    partido: str,
    iniciativa: str,
    votos_relacionados: pd.DataFrame,
) -> str:
    client = anthropic.Anthropic()

    resumen_votos = votos_relacionados[["diputado", "voto", "votacion_id"]].to_string(index=False)

    prompt = f"""Analiza si existe una contradicción política entre la iniciativa presentada
y el comportamiento de votación del partido.

PARTIDO: {partido}

INICIATIVA PRESENTADA:
"{iniciativa}"

VOTACIONES DEL PARTIDO EN EL PERÍODO:
{resumen_votos}

Analiza:
1. ¿El partido presentó esta iniciativa pero luego votó de manera inconsistente?
2. ¿Hay señales de contradicción entre el discurso (iniciativa) y el voto real?
3. ¿Qué interpretación política tiene esto?

Responde de forma concisa, clara y en español. Si no hay suficiente información
para detectar contradicción, dilo claramente."""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def detectar_contradicciones(partido: str) -> tuple[str, list[dict]]:
    try:
        iniciativas_df = cargar_iniciativas()
        if iniciativas_df.empty:
            return "No hay datos de iniciativas disponibles. Ejecuta primero el scraper de iniciativas.", []

        conn = sqlite3.connect(DB_PATH)
        votaciones_df = pd.read_sql(
            "SELECT diputado, partido, voto, votacion_id FROM votaciones WHERE partido = :p",
            conn, params={"p": partido}
        )
        conn.close()

        if votaciones_df.empty:
            return f"No hay votaciones registradas para {partido}.", []

        iniciativas_partido = iniciativas_df[
            iniciativas_df["presentada_por"].str.contains(partido, case=False, na=False)
        ]

        if iniciativas_partido.empty:
            iniciativas_partido = iniciativas_df.head(4)

        reporte_partes = [f"DETECTOR DE CONTRADICCIONES — {partido}\n{'═'*50}\n"]
        fuentes = url_contradicciones(partido)
        contradicciones_encontradas = 0

        for _, iniciativa in iniciativas_partido.head(4).iterrows():
            tema = detectar_tema(iniciativa["titulo"])

            analisis = analizar_contradiccion_con_ia(
                partido=partido,
                iniciativa=iniciativa["titulo"],
                votos_relacionados=votaciones_df.head(10),
            )

            reporte_partes.append(f"""
📄 Iniciativa: {iniciativa['titulo'][:80]}...
📅 Fecha: {iniciativa.get('fecha', 'N/D')}
🏷️ Tema: {tema.upper()}
🤖 Análisis IA:
{analisis}
{'─'*50}""")

            contradicciones_encontradas += 1

        reporte_partes.append(
            f"\nTotal de iniciativas analizadas: {contradicciones_encontradas}"
        )

        return "\n".join(reporte_partes), fuentes

    except Exception as e:
        return f"Error en detector de contradicciones: {e}", []
