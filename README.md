# 🏛️ AgenteMX — Agente de IA para Transparencia Legislativa en México

> *"¿Tu diputado realmente vota como dice? Ahora puedes saberlo."*

AgenteMX es un agente de inteligencia artificial que democratiza el acceso a la información legislativa en México. Cualquier ciudadano puede preguntarle en lenguaje natural sobre el comportamiento de sus diputados y obtener respuestas respaldadas por datos oficiales de la Cámara de Diputados.

---

## 🎯 El Problema que Resuelve

En México, los datos legislativos **son públicos pero inaccesibles en la práctica**:

- Las votaciones nominales están en portales gubernamentales complejos, difíciles de navegar
- Un ciudadano promedio no puede responder preguntas como: *"¿Mi diputado faltó más en año electoral?"* o *"¿El PAN vota diferente a lo que propone?"*
- Los periodistas y analistas tardan horas en extraer y cruzar datos que el agente responde en segundos
- La opacidad legislativa alimenta la desconfianza ciudadana en las instituciones

**AgenteMX convierte datos gubernamentales complejos en conversaciones simples.**

---

## 🚀 Demo — Preguntas que puedes hacer

```
¿Cuántos registros hay en la base de datos?
¿Qué partido tiene más ausencias?
Dame el resumen del partido PAN
¿Qué diputados tienen patrones de ausencia frecuente?
¿Cuál es el índice de disciplina de Morena?
Compara la disciplina entre todos los partidos
¿Quiénes son los diputados más disidentes del PRI?
¿Hay contradicciones entre las iniciativas y votos del PAN?
¿Cambia el comportamiento electoral de Morena en año electoral?
Compara el radar electoral de todos los partidos
```

---

## 🏗️ Arquitectura

```
Usuario (lenguaje natural)
        ↓
Claude — Anthropic API (decide qué herramienta usar)
        ↓
┌─────────────────────────────────────────────┐
│  8 Tools Especializadas                     │
│                                             │
│  consultar_votaciones   → SQLite            │
│  resumen_base_datos     → SQLite            │
│  buscar_diputado        → SQLite            │
│  resumen_por_partido    → SQLite            │
│  detectar_patrones      → SQLite            │
│  calcular_disciplina    → SQLite + IA       │
│  detectar_contradicc.   → SQLite + IA       │
│  radar_electoral        → SQLite + CSV      │
└─────────────────────────────────────────────┘
        ↓
Respuesta + citas clicables a fuentes oficiales
        ↓
Interfaz Streamlit
```

---

## 🧠 Módulos Estratégicos

### 🌡️ Termómetro de Disciplina Partidista
Calcula un índice del 0 al 100 que mide qué tan seguido cada diputado vota alineado con la línea oficial de su partido. Identifica disidentes internos que los medios no cubren.

### 🔍 Detector de Contradicciones
Cruza las iniciativas que presentó un partido con su comportamiento real de votación. Usa análisis semántico con Claude para detectar inconsistencias entre el discurso político y el voto.

### 📡 Radar Electoral
Analiza si el comportamiento de voto de los diputados cambia en períodos electorales vs normales. Detecta estrategias de visibilidad legislativa preelectoral.

---

## 🛠️ Stack Tecnológico

| Capa | Tecnología |
|---|---|
| Agente IA | Anthropic Claude API (tool use nativo) |
| Modelo | claude-haiku-4-5-20251001 |
| Base de datos | SQLite + Pandas |
| Scraping | BeautifulSoup + Requests |
| Interfaz | Streamlit |
| Entorno | GitHub Codespaces |
| Lenguaje | Python 3.11 |

---

## 📊 Fuente de Datos

| Dataset | Fuente | Registros |
|---|---|---|
| Votaciones nominales | sitl.diputados.gob.mx | ~10,000+ |
| Iniciativas legislativas | gaceta.diputados.gob.mx | En expansión |
| Contexto electoral | ine.mx | 2021–2024 |

**Partidos cubiertos:** Morena · PAN · PRI · PRD · PT · PVEM · MC

---

## ⚙️ Instalación

```bash
# 1. Clonar repositorio
git clone https://github.com/jose2501106-IA/agente-legislativo-mx.git
cd agente-legislativo-mx

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar variables de entorno
cp .env.example .env
# Editar .env y agregar tu ANTHROPIC_API_KEY

# 4. Ejecutar pipeline de datos
python agente_mx/src/scrapers/votaciones_scraper.py
python agente_mx/src/utils/limpiar_datos.py
python agente_mx/src/utils/cargar_sqlite.py
python agente_mx/src/scrapers/fechas_scraper.py

# 5. Lanzar aplicación
streamlit run agente_mx/app/streamlit_app.py
```

---

## 📁 Estructura del Proyecto

```
agente-legislativo-mx/
├── agente_mx/
│   ├── data/
│   │   ├── raw/                    # Datos crudos descargados
│   │   └── processed/              # Datos limpios
│   ├── src/
│   │   ├── scrapers/
│   │   │   ├── votaciones_scraper.py
│   │   │   ├── iniciativas_scraper.py
│   │   │   └── fechas_scraper.py
│   │   ├── tools/
│   │   │   ├── tools_legislativas.py
│   │   │   ├── tool_disciplina.py
│   │   │   ├── tool_contradicciones.py
│   │   │   └── tool_radar_electoral.py
│   │   └── utils/
│   │       ├── limpiar_datos.py
│   │       ├── cargar_sqlite.py
│   │       └── url_builder.py
│   └── app/
│       └── streamlit_app.py        # Interfaz principal
├── .devcontainer/
│   └── devcontainer.json           # Configuración Codespaces
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🗺️ Roadmap

### Completado ✅
- [x] Fase 0 — Entorno Codespaces configurado
- [x] Fase 1 — Scraper + pipeline de datos + SQLite
- [x] Fase 2 — Agente con API nativa de Anthropic (tool use)
- [x] Fase 3A — 8 tools especializadas funcionando
- [x] Fase 3B — Interfaz Streamlit con citas clicables
- [x] Fase 4A — Termómetro de Disciplina Partidista
- [x] Fase 4B — Detector de Contradicciones con análisis IA
- [x] Fase 4C — Radar Electoral (comportamiento en año electoral)

### En desarrollo 🔄
- [ ] Fase 5A — Exportar dataset a Google Sheets público (URLs exactas por votación)
- [ ] Fase 5B — Deploy público en Streamlit Cloud (demo sin Codespaces)
- [ ] Fase 5C — Expandir dataset a 200+ votaciones divisivas

---

## 👤 Autor

**José Pepe** — AI Engineering Student  
Hybridge Education · Oracle Next Education · UVEG Industrial Engineering  
[GitHub](https://github.com/jose2501106-IA)

---

## 📄 Licencia

MIT License — Libre para uso educativo y periodístico.

---

> *Datos abiertos del gobierno mexicano, procesados con IA para servir a la ciudadanía.*
