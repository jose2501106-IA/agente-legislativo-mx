"""
Agente principal de AgenteMX — versión completa con todas las tools
"""

import sqlite3
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
import anthropic
import sys
sys.path.append(".")
from agente_mx.src.tools.tools_legislativas import (
    buscar_diputado,
    resumen_por_partido,
    detectar_patrones,
)

load_dotenv()

DB_PATH = Path("agente_mx/data/agente_mx.db")
client = anthropic.Anthropic()
MODEL = "claude-haiku-4-5-20251001"

# ─────────────────────────────────────────────
# DEFINICIÓN DE TOOLS
# ─────────────────────────────────────────────

tools = [
    {
        "name": "consultar_votaciones",
        "description": """Ejecuta una consulta SQL sobre la base de datos de votaciones.
        La tabla se llama 'votaciones' con columnas:
        diputado, partido, voto (A favor/En contra/Ausente/Abstención), votacion_id.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "query_sql": {"type": "string", "description": "Consulta SQL a ejecutar"}
            },
            "required": ["query_sql"]
        }
    },
    {
        "name": "resumen_base_datos",
        "description": "Devuelve resumen general: total de registros, partidos y distribución de votos.",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "buscar_diputado",
        "description": "Busca un diputado por nombre y devuelve su historial completo de votaciones.",
        "input_schema": {
            "type": "object",
            "properties": {
                "nombre": {"type": "string", "description": "Nombre o apellido del diputado a buscar"}
            },
            "required": ["nombre"]
        }
    },
    {
        "name": "resumen_por_partido",
        "description": "Genera resumen detallado del comportamiento de votación de un partido político.",
        "input_schema": {
            "type": "object",
            "properties": {
                "partido": {"type": "string", "description": "Nombre del partido político"}
            },
            "required": ["partido"]
        }
    },
    {
        "name": "detectar_patrones",
        "description": "Detecta patrones relevantes: diputados con muchas ausencias, votaciones divisivas.",
        "input_schema": {
            "type": "object",
            "properties": {
                "umbral_ausencias": {
                    "type": "integer",
                    "description": "Mínimo de ausencias para considerar un diputado como frecuentemente ausente"
                }
            }
        }
    },
]


# ─────────────────────────────────────────────
# LÓGICA DE TOOLS
# ─────────────────────────────────────────────

def ejecutar_tool(nombre: str, inputs: dict) -> str:
    try:
        conn = sqlite3.connect(DB_PATH)

        if nombre == "consultar_votaciones":
            df = pd.read_sql(inputs["query_sql"], conn)
            conn.close()
            return df.to_string(index=False) if not df.empty else "Sin resultados."

        elif nombre == "resumen_base_datos":
            total = pd.read_sql("SELECT COUNT(*) as total FROM votaciones", conn).iloc[0]["total"]
            partidos = pd.read_sql("SELECT DISTINCT partido FROM votaciones ORDER BY partido", conn)
            votos = pd.read_sql(
                "SELECT voto, COUNT(*) as total FROM votaciones GROUP BY voto ORDER BY total DESC", conn
            )
            conn.close()
            return f"""Total registros: {total}
Partidos: {', '.join(partidos['partido'].tolist())}
Votos:
{votos.to_string(index=False)}"""

        elif nombre == "buscar_diputado":
            conn.close()
            return buscar_diputado(inputs["nombre"])

        elif nombre == "resumen_por_partido":
            conn.close()
            return resumen_por_partido(inputs["partido"])

        elif nombre == "detectar_patrones":
            conn.close()
            umbral = inputs.get("umbral_ausencias", 3)
            return detectar_patrones(umbral)

        conn.close()
        return "Tool no reconocida."

    except Exception as e:
        return f"Error: {e}"


# ─────────────────────────────────────────────
# LOOP DEL AGENTE
# ─────────────────────────────────────────────

SYSTEM_PROMPT = """Eres AgenteMX, un asistente especializado en transparencia legislativa de México.
Ayudas a ciudadanos, periodistas y analistas a entender el comportamiento de los diputados
a través de sus votaciones. Usa siempre las herramientas para responder con datos reales.
Responde en español, de forma clara y accesible. Nunca inventes datos."""


def preguntar(pregunta: str) -> str:
    messages = [{"role": "user", "content": pregunta}]

    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=tools,
            messages=messages,
        )

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"  → Usando tool: {block.name}")
                    resultado = ejecutar_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": resultado,
                    })
            messages.append({"role": "user", "content": tool_results})

        elif response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    return block.text
            return "Sin respuesta."


# ─────────────────────────────────────────────
# EJECUCIÓN DE PRUEBA
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("Iniciando AgenteMX — versión completa\n")

    preguntas_prueba = [
        "¿Cuál es el resumen general de la base de datos?",
        "Dame el resumen de votaciones del partido Morena",
        "¿Qué diputados tienen patrones de ausencia frecuente?",
    ]

    for pregunta in preguntas_prueba:
        print(f"\n{'='*60}")
        print(f"Pregunta: {pregunta}")
        print('='*60)
        respuesta = preguntar(pregunta)
        print(f"\nRespuesta:\n{respuesta}")
