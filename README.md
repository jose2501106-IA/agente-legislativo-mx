# AgenteMX

Agente de IA para transparencia legislativa. Responde en lenguaje natural preguntas sobre las votaciones nominales de la Cámara de Diputados de México, a partir de una base de datos local construida con registros públicos de la propia Cámara, y acompaña las respuestas con citas que enlazan a los portales oficiales.

Es un proyecto en desarrollo. Este documento describe lo que el código hace hoy, su alcance y sus límites.

## Para qué sirve

Las votaciones nominales son públicas y se consultan en el sitio de la Cámara de Diputados (sitl.diputados.gob.mx). El proyecto descarga esos registros votación por votación y partido por partido, los limpia y los carga en una base SQLite local. Sobre esa base, un agente responde preguntas como cuántos registros hay, cómo se distribuyen los votos de un partido o cómo votó una persona en las votaciones cargadas.

## Preguntas de ejemplo

```
¿Cuántos registros hay en la base de datos?
¿Qué partidos están en la base y cómo se distribuyen sus votos?
Resume las votaciones de un partido.
¿Cómo votó [apellido] en las votaciones registradas?
¿Cuál es el índice de disciplina de cada partido?
¿Cuáles son las votaciones con más votos en contra?
```

## Alcance y límites

### Datos

| Conjunto | Origen | Cobertura actual |
|---|---|---|
| Votaciones nominales | sitl.diputados.gob.mx, LXV Legislatura (2021–2024) | El script descarga las votaciones 1 a 80 de siete partidos: MC, Morena, PAN, PRD, PRI, PT y PVEM. Volumen: más de 10,000 registros. Cada registro es el voto de una diputada o un diputado en una votación. |
| Iniciativas | gaceta.diputados.gob.mx; como alternativa, sil.gobernacion.gob.mx | En expansión. Si ninguna de las dos fuentes devuelve datos, el script genera una muestra de desarrollo de ocho iniciativas, identificada como tal en el archivo. |
| Fechas y contexto electoral | Tabla de periodos de sesiones incluida en el código | El script intenta leer la fecha de cada votación en el sitio oficial; si no la encuentra, usa una fecha aproximada por periodo de sesiones (2021 y 2022). La marca de año electoral sale de esa tabla y, en el rango actual, ninguna votación la tiene. El INE aparece solo como enlace de referencia. |

La base de datos y los archivos descargados no se incluyen en el repositorio: se generan al ejecutar los scripts.

### Herramientas del agente

El agente cuenta con ocho herramientas. Dos de ellas (disciplina y periodo electoral) tienen además una variante que compara todos los partidos, por lo que la interfaz registra diez definiciones.

| # | Herramienta | Qué hace | Estado |
|---|---|---|---|
| 1 | `consultar_votaciones` | Ejecuta la consulta SQL que redacta el modelo sobre la tabla `votaciones` (`diputado`, `partido`, `voto`, `votacion_id`). | Funcional |
| 2 | `resumen_base_datos` | Total de registros, partidos presentes y distribución de votos. | Funcional |
| 3 | `buscar_diputado` | Busca por nombre o apellido y devuelve el conteo y el detalle de los votos registrados. | Funcional |
| 4 | `resumen_por_partido` | Distribución de votos de un partido, las cinco personas con más ausencias y las cinco con más votos a favor. | Funcional |
| 5 | `detectar_patrones` | Lista hasta diez personas con un número de ausencias igual o mayor a un umbral (3 por defecto) y las cinco votaciones con más votos en contra. | Funcional |
| 6 | `calcular_disciplina_partido` y `comparar_disciplina_partidos` | Índice de disciplina por persona y promedio por partido. | Funcional |
| 7 | `detectar_contradicciones` | Consistencia entre iniciativas y votos. | Prototipo |
| 8 | `radar_electoral_partido` y `radar_comparativo_partidos` | Comparación entre periodo electoral y no electoral. | Prototipo |

La versión de consola (`agente_mx/src/agent/agente_principal.py`) usa solo las cinco primeras.

### Índice de disciplina partidista

1. En cada votación, la línea del partido se toma como el sentido de voto más frecuente entre sus integrantes (a favor, en contra o abstención). Es una inferencia a partir de los votos, no una posición oficial declarada.
2. El índice de cada persona es el porcentaje de sus votos emitidos que coincide con esa línea, en una escala de 0 a 100. Las ausencias no cuentan como voto emitido.
3. El índice del partido es el promedio de los índices individuales.
4. El código agrupa los resultados en tres rangos: 90 o más, de 70 a menos de 90 y menos de 70.

### Módulos en prototipo

- **Consistencia entre iniciativas y votos** (`detectar_contradicciones`). Hace una consulta al modelo por cada una de hasta cuatro iniciativas; en cada una envía el título y los mismos diez primeros registros de voto del partido. Aún no relaciona cada iniciativa con las votaciones del mismo asunto, así que su salida es exploratoria.
- **Periodo electoral** (`radar_electoral_partido`). Compara los porcentajes de votos a favor, votos en contra y ausencias entre las votaciones marcadas como de año electoral y las demás. Con el rango actual ninguna votación queda marcada como de año electoral, por lo que la comparación todavía no tiene datos de ese periodo y sus resultados no deben interpretarse.

### Citas

Las herramientas devuelven, junto con el resultado, enlaces a portales oficiales: el portal de votaciones y la página principal de la Cámara de Diputados, la Gaceta Parlamentaria, datos.gob.mx y, en el módulo de periodo electoral, el INE. La interfaz los muestra como citas numeradas. La consulta SQL directa no genera citas.

Los enlaces apuntan a los portales y no al registro de cada votación. `detectar_patrones` añade enlaces con el número de votación, pero filtran a un solo grupo parlamentario y el sitio puede no mostrar datos al abrirlos. El enlace directo por votación está pendiente.

### Otros límites conocidos

- `consultar_votaciones` ejecuta el SQL que redacta el modelo sobre la base local. Todavía no hay una validación que lo limite a consultas de lectura.
- La búsqueda por nombre usa coincidencia parcial: un apellido común puede reunir registros de más de una persona.
- Los scripts de extracción dependen de la disponibilidad y del formato de los sitios oficiales.

## Arquitectura

```
Pregunta en lenguaje natural
        │
        ▼
Claude (API de Anthropic, uso de herramientas)
elige qué herramienta llamar
        │
        ▼
Herramientas del agente
  consultar_votaciones           SQLite
  resumen_base_datos             SQLite
  buscar_diputado                SQLite
  resumen_por_partido            SQLite
  detectar_patrones              SQLite
  calcular_disciplina_partido    SQLite
  detectar_contradicciones       SQLite + CSV de iniciativas + Claude   (prototipo)
  radar_electoral_partido        SQLite + CSV de fechas                 (prototipo)
        │
        ▼
Respuesta con citas a portales oficiales
        │
        ▼
Interfaz en Streamlit
```

El modelo recibe la instrucción de usar siempre las herramientas y de no inventar datos.

## Tecnologías

| Capa | Tecnología |
|---|---|
| Agente | API de Anthropic (Claude) con uso de herramientas |
| Modelo | `claude-haiku-4-5-20251001`, definido en el código |
| Datos | SQLite y Pandas |
| Extracción | Requests y BeautifulSoup |
| Interfaz | Streamlit |
| Entorno | GitHub Codespaces (`.devcontainer/`), Python 3.11 |

## Instalación

Los comandos se ejecutan desde la raíz del repositorio.

```bash
# 1. Clonar el repositorio
git clone https://github.com/jose2501106-IA/agente-legislativo-mx.git
cd agente-legislativo-mx

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar la clave de la API
cp .env.example .env            # editar .env y escribir ANTHROPIC_API_KEY

# 4. Construir la base de datos
python agente_mx/src/scrapers/votaciones_scraper.py
python agente_mx/src/utils/limpiar_datos.py
python agente_mx/src/utils/cargar_sqlite.py
python agente_mx/src/scrapers/fechas_scraper.py
python agente_mx/src/scrapers/iniciativas_scraper.py   # opcional: solo para el prototipo de iniciativas

# 5. Abrir la interfaz
streamlit run agente_mx/app/streamlit_app.py
```

Notas:

- **Clave de la API.** El código solo usa `ANTHROPIC_API_KEY`.
- **Descarga.** El script de votaciones hace una pausa entre solicitudes para no saturar el servidor oficial.
- **Codespaces.** El repositorio incluye una configuración (`.devcontainer/`) con Python 3.11 que instala las dependencias y expone el puerto 8501 de Streamlit.

## Estructura del repositorio

```
agente-legislativo-mx/
├── agente_mx/
│   ├── __init__.py
│   ├── app/
│   │   └── streamlit_app.py           Interfaz principal y definición de las herramientas
│   └── src/
│       ├── agent/
│       │   └── agente_principal.py    Versión de consola
│       ├── scrapers/
│       │   ├── votaciones_scraper.py
│       │   ├── iniciativas_scraper.py
│       │   └── fechas_scraper.py
│       ├── tools/
│       │   ├── tools_legislativas.py
│       │   ├── tool_disciplina.py
│       │   ├── tool_contradicciones.py
│       │   └── tool_radar_electoral.py
│       └── utils/
│           ├── limpiar_datos.py
│           ├── cargar_sqlite.py
│           └── url_builder.py
├── .devcontainer/
│   └── devcontainer.json              Entorno de GitHub Codespaces
├── requirements.txt
├── .env.example
├── .gitignore
├── LICENSE
└── README.md
```

Al ejecutar los scripts se crea `agente_mx/data/`, con los archivos descargados (`raw/`), los datos limpios (`processed/`) y la base `agente_mx.db`. Esa carpeta no se versiona.

## Estado y siguientes pasos

Funciona hoy:

- Descarga, limpieza y carga en SQLite de votaciones nominales de la LXV Legislatura.
- Agente con la API de Anthropic y uso de herramientas.
- Interfaz en Streamlit con citas numeradas.
- Índice de disciplina partidista.

En prototipo:

- Consistencia entre iniciativas y votos.
- Comparación entre periodo electoral y no electoral.

Siguientes pasos:

- Publicar el conjunto de datos con el enlace exacto de cada votación.
- Demo pública en Streamlit Cloud; hoy se ejecuta en local o en GitHub Codespaces.
- Ampliar la cobertura de 80 a más de 200 votaciones.
- Atender los límites descritos arriba: carga completa de iniciativas, fechas por votación y relación entre iniciativas y votaciones.

## Uso responsable

- Los resultados son descriptivos. Resumen registros públicos de votación y dependen de la cobertura y la calidad de los datos cargados.
- No son un juicio sobre personas, partidos ni grupos parlamentarios. El índice de disciplina mide la coincidencia con el sentido de voto más frecuente del propio partido en las votaciones cargadas, nada más.
- Los módulos en prototipo no deben usarse para sacar conclusiones.
- Las respuestas las redacta un modelo de lenguaje a partir de esos datos. Conviene contrastarlas con los portales oficiales enlazados en las respuestas; ante cualquier diferencia, prevalece el registro oficial.

## Autor

**José Hugo Meza Vázquez**, estudiante de Ingeniería en Inteligencia Artificial (Hybridge Education) e Ingeniería Industrial (UVEG).

Portafolio: <https://jose2501106-ia.github.io> · GitHub: <https://github.com/jose2501106-IA>

## Licencia

MIT. Consulta el archivo [`LICENSE`](LICENSE).
