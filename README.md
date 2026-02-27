# 🏛️ AgenteMX — Agente de IA para Transparencia Legislativa en México

> Agente de IA agéntica que permite analizar en lenguaje natural el comportamiento
> de votación de los diputados mexicanos. Construido con Python, Anthropic Claude,
> LangChain y Streamlit sobre datos abiertos de la Cámara de Diputados.

---

## ¿Qué problema resuelve?

La información legislativa en México es pública pero inaccesible para la mayoría
de ciudadanos, periodistas y analistas políticos. Está dispersa, en formatos
difíciles y requiere horas de búsqueda manual.

**AgenteMX convierte esa información en conversación.**

---

## Demo

![AgenteMX Demo](https://img.shields.io/badge/status-en%20desarrollo-yellow)

Preguntas que puedes hacerle al agente:

- *"¿Qué partido tiene más ausencias?"*
- *"Dame el índice de disciplina de Morena"*
- *"¿Quiénes son los diputados más disidentes del PRI?"*
- *"Compara la disciplina entre todos los partidos"*
- *"Busca al diputado Garza y dame su historial"*

---

## Arquitectura
```
Usuario (lenguaje natural)
        ↓
   Claude (Anthropic API)
        ↓ decide qué tool usar
   ┌────────────────────────────┐
   │  Tool: consultar_votaciones│  → SQLite
   │  Tool: buscar_diputado     │  → SQLite
   │  Tool: resumen_por_partido │  → SQLite
   │  Tool: detectar_patrones   │  → SQLite
   │  Tool: disciplina_partido  │  → SQLite
   └────────────────────────────┘
        ↓
   Respuesta en español + citas clicables a fuente oficial
```

---

## Stack tecnológico

| Capa | Tecnología |
|------|-----------|
| LLM | Anthropic Claude (claude-haiku-4-5) |
| Agente | Tool Use nativo de Anthropic API |
| Datos | SQLite + Pandas |
| Scraping | BeautifulSoup + Requests |
| Interfaz | Streamlit |
| Entorno | GitHub Codespaces |

---

## Fuente de datos

Datos abiertos oficiales de la **Cámara de Diputados de México**:
- Portal: [sitl.diputados.gob.mx](https://sitl.diputados.gob.mx)
- Legislatura: LXV (2021-2024)
- Cobertura: Votaciones nominales por diputado y partido

---

## Instalación y uso

### 1. Clona el repositorio
```bash
git clone https://github.com/tu-usuario/agente-legislativo-mx
cd agente-legislativo-mx
```

### 2. Configura las variables de entorno
```bash
cp .env.example .env
# Edita .env y agrega tu ANTHROPIC_API_KEY
```

### 3. Instala dependencias
```bash
pip install -r requirements.txt
```

### 4. Descarga los datos
```bash
python agente_mx/src/scrapers/votaciones_scraper.py
python agente_mx/src/utils/limpiar_datos.py
python agente_mx/src/utils/cargar_sqlite.py
```

### 5. Lanza la app
```bash
streamlit run agente_mx/app/streamlit_app.py
```

---

## Módulos del proyecto
```
agente_mx/
├── src/
│   ├── scrapers/          # Descarga de datos oficiales
│   ├── tools/             # Tools del agente
│   │   ├── tools_legislativas.py   # Búsqueda, resúmenes, patrones
│   │   └── tool_disciplina.py      # Termómetro de disciplina
│   ├── agent/             # Agente principal
│   └── utils/             # Limpieza y carga de datos
├── app/
│   └── streamlit_app.py   # Interfaz visual
└── data/
    ├── raw/               # Datos crudos descargados
    └── processed/         # Datos limpios
```

---

## Roadmap

- [x] Fase 1 — Scraper y pipeline de datos
- [x] Fase 2 — Agente con tool use nativo de Anthropic
- [x] Fase 3 — Interfaz Streamlit con citas clicables
- [x] Fase 4A — Termómetro de Disciplina Partidista
- [ ] Fase 4B — Detector de Contradicciones (discurso vs voto)
- [ ] Fase 4C — Radar Electoral (comportamiento en año electoral)

---

## Autor

Construido como proyecto de portafolio de IA agéntica aplicada
a transparencia política en México.

---

## Licencia

MIT
