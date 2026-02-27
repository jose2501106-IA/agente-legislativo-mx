"""
AgenteMX — Interfaz visual con Streamlit + citas clicables + Termómetro de Disciplina
"""

import streamlit as st
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
from agente_mx.src.tools.tool_disciplina import (
    calcular_disciplina_partido,
    comparar_disciplina_partidos,
)

load_dotenv()

DB_PATH = Path("agente_mx/data/agente_mx.db")
MODEL = "claude-haiku-4-5-20251001"

st.set_page_config(
    page_title="AgenteMX — Transparencia Legislativa",
    page_icon="🏛️",
    layout="wide",
)

st.title("🏛️ AgenteMX")
st.caption("Agente de IA para transparencia legislativa en México · Cámara de Diputados LXV Legislatura")
st.divider()

# ─────────────────────────────────────────────
# TOOLS
# ─────────────────────────────────────────────

tools = [
    {
        "name": "consultar_votaciones",
        "description": "Ejecuta SQL sobre la tabla 'votaciones' con columnas: diputado, partido, voto, votacion_id.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query_sql": {"type": "string", "description": "Consulta SQL"}
            },
            "required": ["query_sql"]
        }
    },
    {
        "name": "resumen_base_datos",
        "description": "Resumen general: total registros, partidos y distribución de votos.",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "buscar_diputado",
        "description": "Busca diputado por nombre y devuelve historial de votaciones.",
        "input_schema": {
            "type": "object",
            "properties": {
                "nombre": {"type": "string"}
            },
            "required": ["nombre"]
        }
    },
    {
        "name": "resumen_por_partido",
        "description": "Resumen de votaciones de un partido político.",
        "input_schema": {
            "type": "object",
            "properties": {
                "partido": {"type": "string"}
            },
            "required": ["partido"]
        }
    },
    {
        "name": "detectar_patrones",
        "description": "Detecta patrones: ausencias frecuentes y votaciones divisivas.",
        "input_schema": {
            "type": "object",
            "properties": {
                "umbral_ausencias": {"type": "integer"}
            }
        }
    },
    {
        "name": "calcular_disciplina_partido",
        "description": """Calcula el índice de disciplina partidista de cada diputado de un partido.
        Determina qué tan seguido cada diputado vota alineado con la línea oficial de su partido.
        Identifica disidentes internos y los más disciplinados. Devuelve un índice del 0 al 100.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "partido": {"type": "string", "description": "Nombre del partido político"}
            },
            "required": ["partido"]
        }
    },
    {
        "name": "comparar_disciplina_partidos",
        "description": """Compara el índice de disciplina promedio entre todos los partidos políticos.
        Útil para saber qué partido tiene más cohesión interna y cuál tiene más disidencia.""",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
]


# ─────────────────────────────────────────────
# EJECUTAR TOOL
# ─────────────────────────────────────────────

def ejecutar_tool(nombre: str, inputs: dict) -> tuple[str, list[dict]]:
    try:
        conn = sqlite3.connect(DB_PATH)

        if nombre == "consultar_votaciones":
            df = pd.read_sql(inputs["query_sql"], conn)
            conn.close()
            return (df.to_string(index=False) if not df.empty else "Sin resultados."), []

        elif nombre == "resumen_base_datos":
            total = pd.read_sql("SELECT COUNT(*) as total FROM votaciones", conn).iloc[0]["total"]
            partidos = pd.read_sql("SELECT DISTINCT partido FROM votaciones ORDER BY partido", conn)
            votos = pd.read_sql(
                "SELECT voto, COUNT(*) as total FROM votaciones GROUP BY voto ORDER BY total DESC", conn
            )
            conn.close()
            fuentes = [{
                "votacion_id": "general",
                "url": "https://sitl.diputados.gob.mx/LXV_leg/listados_votacionesnplxv.php",
                "label": "Portal oficial de votaciones — Cámara de Diputados LXV"
            }]
            return f"""Total registros: {total}
Partidos: {', '.join(partidos['partido'].tolist())}
Votos:
{votos.to_string(index=False)}""", fuentes

        elif nombre == "buscar_diputado":
            conn.close()
            return buscar_diputado(inputs["nombre"])

        elif nombre == "resumen_por_partido":
            conn.close()
            return resumen_por_partido(inputs["partido"])

        elif nombre == "detectar_patrones":
            conn.close()
            return detectar_patrones(inputs.get("umbral_ausencias", 3))

        elif nombre == "calcular_disciplina_partido":
            conn.close()
            return calcular_disciplina_partido(inputs["partido"])

        elif nombre == "comparar_disciplina_partidos":
            conn.close()
            return comparar_disciplina_partidos()

        conn.close()
        return "Tool no reconocida.", []

    except Exception as e:
        return f"Error: {e}", []


# ─────────────────────────────────────────────
# AGENTE
# ─────────────────────────────────────────────

SYSTEM_PROMPT = """Eres AgenteMX, asistente de transparencia legislativa de México.
Usa siempre las herramientas para responder con datos reales.
Cuando menciones votaciones específicas, incluye el número de votación entre corchetes así: [N]
donde N corresponde al índice de la fuente que te será proporcionada.
Responde en español, claro y accesible. Nunca inventes datos."""


def preguntar(pregunta: str, historial: list) -> tuple[str, list[str], list[dict]]:
    client = anthropic.Anthropic()
    messages = historial + [{"role": "user", "content": pregunta}]
    tools_usadas = []
    todas_las_fuentes = []

    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            tools=tools,
            messages=messages,
        )

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []

            for block in response.content:
                if block.type == "tool_use":
                    tools_usadas.append(block.name)
                    resultado, fuentes = ejecutar_tool(block.name, block.input)
                    todas_las_fuentes.extend(fuentes)

                    if fuentes:
                        fuentes_texto = "\n\nFuentes disponibles:\n" + "\n".join(
                            [f"[{i+1}] {f['label']}" for i, f in enumerate(fuentes)]
                        )
                        resultado += fuentes_texto

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": resultado,
                    })
            messages.append({"role": "user", "content": tool_results})

        elif response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    return block.text, tools_usadas, todas_las_fuentes
            return "Sin respuesta.", tools_usadas, todas_las_fuentes


def renderizar_citas(texto: str, fuentes: list[dict]) -> str:
    """Convierte [N] en superíndices HTML clicables."""
    for i, fuente in enumerate(fuentes):
        n = i + 1
        enlace = f'<sup><a href="{fuente["url"]}" target="_blank" title="{fuente["label"]}">[{n}]</a></sup>'
        texto = texto.replace(f"[{n}]", enlace)
    return texto


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────

with st.sidebar:
    st.header("🔍 Preguntas de ejemplo")

    preguntas_ejemplo = [
        "¿Cuántos registros hay en la base de datos?",
        "¿Qué partido tiene más ausencias?",
        "Dame el resumen del partido PAN",
        "¿Qué diputados tienen patrones de ausencia frecuente?",
        "Busca al diputado Garza",
        "¿Cuál es el índice de disciplina de Morena?",
        "Compara la disciplina entre todos los partidos",
        "¿Quiénes son los diputados más disidentes del PRI?",
    ]

    for p in preguntas_ejemplo:
        if st.button(p, use_container_width=True):
            st.session_state["pregunta_ejemplo"] = p

    st.divider()
    st.markdown("**Fuente de datos:**")
    st.markdown("[sitl.diputados.gob.mx](https://sitl.diputados.gob.mx/LXV_leg/listados_votacionesnplxv.php)")
    st.markdown("**Modelo IA:**")
    st.markdown(f"`{MODEL}`")

    if st.button("🗑️ Limpiar conversación", use_container_width=True):
        st.session_state["mensajes"] = []
        st.session_state["historial_agente"] = []
        st.rerun()


# ─────────────────────────────────────────────
# ESTADO
# ─────────────────────────────────────────────

if "mensajes" not in st.session_state:
    st.session_state["mensajes"] = []
if "historial_agente" not in st.session_state:
    st.session_state["historial_agente"] = []
if "pregunta_ejemplo" not in st.session_state:
    st.session_state["pregunta_ejemplo"] = ""


# ─────────────────────────────────────────────
# HISTORIAL DEL CHAT
# ─────────────────────────────────────────────

for mensaje in st.session_state["mensajes"]:
    with st.chat_message(mensaje["role"]):
        if mensaje["role"] == "assistant" and mensaje.get("fuentes"):
            html = renderizar_citas(mensaje["content"], mensaje["fuentes"])
            st.markdown(html, unsafe_allow_html=True)
            with st.expander("📎 Ver fuentes"):
                for i, f in enumerate(mensaje["fuentes"]):
                    st.markdown(f"**[{i+1}]** [{f['label']}]({f['url']})")
        else:
            st.markdown(mensaje["content"])

        if mensaje.get("tools_usadas"):
            st.caption(f"🔧 {' · '.join(mensaje['tools_usadas'])}")


# ─────────────────────────────────────────────
# INPUT DEL USUARIO
# ─────────────────────────────────────────────

pregunta_inicial = st.session_state.pop("pregunta_ejemplo", "") or ""
pregunta = st.chat_input("Escribe tu pregunta sobre los diputados mexicanos...")

if not pregunta and pregunta_inicial:
    pregunta = pregunta_inicial

if pregunta:
    with st.chat_message("user"):
        st.markdown(pregunta)
    st.session_state["mensajes"].append({"role": "user", "content": pregunta})

    with st.chat_message("assistant"):
        with st.spinner("Consultando datos legislativos..."):
            respuesta, tools_usadas, fuentes = preguntar(
                pregunta, st.session_state["historial_agente"]
            )

        html = renderizar_citas(respuesta, fuentes)
        st.markdown(html, unsafe_allow_html=True)

        if fuentes:
            with st.expander("📎 Ver fuentes"):
                for i, f in enumerate(fuentes):
                    st.markdown(f"**[{i+1}]** [{f['label']}]({f['url']})")

        if tools_usadas:
            st.caption(f"🔧 {' · '.join(tools_usadas)}")

    st.session_state["mensajes"].append({
        "role": "assistant",
        "content": respuesta,
        "tools_usadas": tools_usadas,
        "fuentes": fuentes,
    })

    st.session_state["historial_agente"].append({"role": "user", "content": pregunta})
    st.session_state["historial_agente"].append({"role": "assistant", "content": respuesta})
