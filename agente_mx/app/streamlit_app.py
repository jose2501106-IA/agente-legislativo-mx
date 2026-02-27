"""
AgenteMX — Interfaz visual con Streamlit
Fases: Datos + Agente + Disciplina + Contradicciones + Radar Electoral
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
from agente_mx.src.tools.tool_contradicciones import detectar_contradicciones
from agente_mx.src.tools.tool_radar_electoral import (
    radar_electoral_partido,
    radar_comparativo_partidos,
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

tools = [
    {
        "name": "consultar_votaciones",
        "description": "Ejecuta SQL sobre la tabla votaciones con columnas: diputado, partido, voto, votacion_id.",
        "input_schema": {
            "type": "object",
            "properties": {"query_sql": {"type": "string"}},
            "required": ["query_sql"]
        }
    },
    {
        "name": "resumen_base_datos",
        "description": "Resumen general: total registros, partidos y distribucion de votos.",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "buscar_diputado",
        "description": "Busca diputado por nombre y devuelve historial de votaciones.",
        "input_schema": {
            "type": "object",
            "properties": {"nombre": {"type": "string"}},
            "required": ["nombre"]
        }
    },
    {
        "name": "resumen_por_partido",
        "description": "Resumen de votaciones de un partido politico.",
        "input_schema": {
            "type": "object",
            "properties": {"partido": {"type": "string"}},
            "required": ["partido"]
        }
    },
    {
        "name": "detectar_patrones",
        "description": "Detecta patrones: ausencias frecuentes y votaciones divisivas.",
        "input_schema": {
            "type": "object",
            "properties": {"umbral_ausencias": {"type": "integer"}}
        }
    },
    {
        "name": "calcular_disciplina_partido",
        "description": "Calcula indice de disciplina partidista del 0 al 100 por diputado. Identifica disidentes.",
        "input_schema": {
            "type": "object",
            "properties": {"partido": {"type": "string"}},
            "required": ["partido"]
        }
    },
    {
        "name": "comparar_disciplina_partidos",
        "description": "Compara indice de disciplina promedio entre todos los partidos.",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "detectar_contradicciones",
        "description": "Detecta contradicciones entre iniciativas presentadas y votaciones reales de un partido.",
        "input_schema": {
            "type": "object",
            "properties": {"partido": {"type": "string"}},
            "required": ["partido"]
        }
    },
    {
        "name": "radar_electoral_partido",
        "description": """Analiza si el comportamiento de voto de un partido cambia
        en periodos electorales vs normales. Detecta si los diputados reducen ausencias
        o cambian su voto cerca de las elecciones. Muy util para analisis politico estrategico.""",
        "input_schema": {
            "type": "object",
            "properties": {"partido": {"type": "string"}},
            "required": ["partido"]
        }
    },
    {
        "name": "radar_comparativo_partidos",
        "description": "Compara como cambia el comportamiento electoral de todos los partidos en periodo electoral.",
        "input_schema": {"type": "object", "properties": {}}
    },
]


def ejecutar_tool(nombre, inputs):
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
                "label": "Portal oficial de votaciones — Camara de Diputados LXV"
            }]
            return (
                f"Total registros: {total}\n"
                f"Partidos: {', '.join(partidos['partido'].tolist())}\n"
                f"Votos:\n{votos.to_string(index=False)}"
            ), fuentes

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

        elif nombre == "detectar_contradicciones":
            conn.close()
            return detectar_contradicciones(inputs["partido"])

        elif nombre == "radar_electoral_partido":
            conn.close()
            return radar_electoral_partido(inputs["partido"])

        elif nombre == "radar_comparativo_partidos":
            conn.close()
            return radar_comparativo_partidos()

        conn.close()
        return "Tool no reconocida.", []

    except Exception as e:
        return f"Error: {e}", []


SYSTEM_PROMPT = """Eres AgenteMX, asistente de transparencia legislativa de Mexico.
Usa siempre las herramientas para responder con datos reales.
Cuando menciones votaciones especificas incluye el numero entre corchetes asi: [N]
donde N corresponde al indice de la fuente proporcionada.
Responde en espanol, claro y accesible. Nunca inventes datos."""


def preguntar(pregunta, historial):
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
                        "content": resultado
                    })
            messages.append({"role": "user", "content": tool_results})

        elif response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    return block.text, tools_usadas, todas_las_fuentes
            return "Sin respuesta.", tools_usadas, todas_las_fuentes


def renderizar_citas(texto, fuentes):
    for i, fuente in enumerate(fuentes):
        n = i + 1
        enlace = (
            f'<sup><a href="{fuente["url"]}" target="_blank" '
            f'title="{fuente["label"]}">[{n}]</a></sup>'
        )
        texto = texto.replace(f"[{n}]", enlace)
    return texto


with st.sidebar:
    st.header("🔍 Preguntas de ejemplo")
    preguntas_ejemplo = [
        "¿Cuantos registros hay en la base de datos?",
        "¿Que partido tiene mas ausencias?",
        "Dame el resumen del partido PAN",
        "¿Que diputados tienen patrones de ausencia frecuente?",
        "Busca al diputado Garza",
        "¿Cual es el indice de disciplina de Morena?",
        "Compara la disciplina entre todos los partidos",
        "¿Quienes son los diputados mas disidentes del PRI?",
        "¿Hay contradicciones entre las iniciativas y votos del PAN?",
        "Analiza las contradicciones politicas de Morena",
        "¿Cambia el comportamiento electoral de Morena en año electoral?",
        "Compara el radar electoral de todos los partidos",
    ]
    for p in preguntas_ejemplo:
        if st.button(p, use_container_width=True):
            st.session_state["pregunta_ejemplo"] = p
    st.divider()
    st.markdown("**Fuente de datos:**")
    st.markdown("[sitl.diputados.gob.mx](https://sitl.diputados.gob.mx/LXV_leg/listados_votacionesnplxv.php)")
    st.markdown("**Modelo IA:**")
    st.markdown(f"`{MODEL}`")
    if st.button("🗑️ Limpiar conversacion", use_container_width=True):
        st.session_state["mensajes"] = []
        st.session_state["historial_agente"] = []
        st.rerun()

if "mensajes" not in st.session_state:
    st.session_state["mensajes"] = []
if "historial_agente" not in st.session_state:
    st.session_state["historial_agente"] = []
if "pregunta_ejemplo" not in st.session_state:
    st.session_state["pregunta_ejemplo"] = ""

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
