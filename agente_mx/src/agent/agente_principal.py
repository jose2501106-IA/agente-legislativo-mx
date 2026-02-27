"""
Agente principal de AgenteMX
Usa la API de Anthropic directamente con tool_use nativo
"""

import sqlite3
import json
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
import anthropic

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
        La tabla se llama 'votaciones' y tiene las columnas:
        - diputado: nombre completo
        - partido: partido político
        - voto: A favor, En contra, Ausente, Abstención
        - votacion_id: identificador numérico de la votación""",
        "input_schema": {
            "type": "object",
            "properties": {
                "query_sql": {
                    "type": "string",
                    "description": "La consulta SQL a ejecutar"
                }
            },
            "required": ["query_sql"]
        }
    },
    {
        "name": "resumen_base_datos",
        "description": "Devuelve un resumen general de los datos: total de registros, partidos y distribución de votos.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    }
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
            if df.empty:
                return "La consulta no devolvió resultados."
            return df.to_string(index=False)

        elif nombre == "resumen_base_datos":
            total = pd.read_sql("SELECT COUNT(*) as total FROM votaciones", conn).iloc[0]["total"]
            partidos = pd.read_sql("SELECT DISTINCT partido FROM votaciones ORDER BY partido", conn)
            votos = pd.read_sql(
                "SELECT voto, COUNT(*) as total FROM votaciones GROUP BY voto ORDER BY total DESC",
                conn
            )
            conn.close()
            return f"""Total de registros: {total}
Partidos: {', '.join(partidos['partido'].tolist())}
Distribución de votos:
{votos.to_string(index=False)}"""

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

        # Si el agente quiere usar una tool
        if response.stop_reason == "tool_use":
            # Agregamos la respuesta del agente al historial
            messages.append({"role": "assistant", "content": response.content})

            # Ejecutamos cada tool que pidió
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

            # Agregamos los resultados al historial
            messages.append({"role": "user", "content": tool_results})

        # Si el agente ya tiene la respuesta final
        elif response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    return block.text
            return "Sin respuesta."


# ─────────────────────────────────────────────
# EJECUCIÓN DE PRUEBA
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("Iniciando AgenteMX...\n")

    preguntas_prueba = [
        "¿Cuántos registros hay en total en la base de datos?",
        "¿Qué partido tiene más ausencias?",
        "¿Cuáles son los 5 diputados con más votos en contra?",
    ]

    for pregunta in preguntas_prueba:
        print(f"\n{'='*60}")
        print(f"Pregunta: {pregunta}")
        print('='*60)
        respuesta = preguntar(pregunta)
        print(f"\nRespuesta: {respuesta}")
