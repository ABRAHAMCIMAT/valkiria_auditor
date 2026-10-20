# Proyecto Integrador

___ 


## Maestría en Inteligencia Artificial Aplicada

* Equipo 16


## Instrucciones


1. Clonar el repositorio localmente.

```bash
git clone https://github.com/ABRAHAMCIMAT/valkiria_auditor
cd valkiria_auditor

```
* **Nota**: Para poder acceder al código a través de la línea de comando de Git será necesario acceder a su cuenta git a través de la siguiente guía [Git](https://git-scm.com/book/es/v2/Inicio---Sobre-el-Control-de-Versiones-Configurando-Git-por-primera-vez).

2. Configuración de un ambiente de Python.

```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. Instalación de los módulos de Python.

```bash
pip install -r requirements.txt
```

4. Registrar el ambiente virtual como kernel de Jupyter.

```bash
python -m ipykernel install --user --name=mna-e16 --display-name "MNA E16"
```

5. Iniciar JupyterLab y seleccionar el kernel **"MNA E16"** en el selector de kernel (esquina superior derecha del notebook).

```bash
jupyter lab
```

---

## Estructura del Repositorio

```
valkiria_auditor/
│
├── deliverables/
│   ├── Avance1/
│   │   ├── Avance1.16.ipynb                  ← EDA del knowledge base
│   │   ├── Avance1.16.md                     ← Catálogo y descripción de la base de conocimiento
│   │   └── Avance1.16.docx                   ← Entrega formal
│   ├── Avance2/
│   │   ├── Avance2.16.ipynb                  ← Ingeniería de características y pipeline RAG
│   │   └── Avance2.16.docx                   ← Entrega formal
│   ├── Avance3/
│   │   ├── Avance3.16.ipynb                  ← Modelo baseline con S3 Vectors
│   │   ├── requirements.txt                  ← Dependencias del avance
│   │   └── utils/
│   │       └── s3_sync.py                    ← Sincronización de datos con S3
│   └── Avance4/
│       ├── Avance4.16.ipynb                  ← Benchmarking de modelos y frameworks agénticos
│       └── requirements.txt                  ← Dependencias del avance
│
├── diagrams/
│   └── iso27001-multi-agent.drawio.png       ← Arquitectura del sistema multi-agente
│
├── knowledge-base/
│   ├── audit-examples/                       ← 7 reportes reales de auditoría ISO 27001
│   ├── audit-methodology/                    ← 4 guías de planeación y metodología de auditoría
│   ├── ciso-assistant-community/             ← 4 estándares ISO en formato YAML (legible por máquina)
│   ├── iso27001/                             ← Texto completo de ISO/IEC 27001:2013 (PDF)
│   ├── non-conformities/                     ← Guía de las 10 no conformidades más frecuentes
│   └── sponsor-documents/                    ← 8 políticas de seguridad de la organización patrocinadora
│
├── src/
│   └── rag/
│       └── ingest.py                         ← Pipeline de ingesta: extracción, chunking y ChromaDB
│
├── .gitignore
├── CLAUDE.md                                 ← Guía de arquitectura para Claude Code
├── README.md
└── requirements.txt
```

---

## Avances

### Avance 1 — Análisis Exploratorio de Datos (`deliverables/Avance1/Avance1.16.ipynb`)

Se catalogaron los 23 recursos del knowledge base y se realizó un análisis exploratorio completo antes de la ingesta y vectorización. El análisis cubre cuatro dimensiones:

1. **Inventario de archivos:** Distribución de documentos por extensión (PDF, DOCX, YAML) y por subcarpeta del knowledge base, visualizada con gráficas de barras.
2. **Estadísticas por documento:** Conteo de páginas, palabras y tokens (`cl100k_base`) por archivo y subdirectorio. Permite estimar el tamaño del índice vectorial y los costos de embedding.
3. **Detección de idioma:** Identificación automática del idioma predominante (español/inglés) con `langdetect`, relevante para la selección del modelo de embeddings y la configuración de stopwords.
4. **Nubes de palabras:** Nube consolidada del knowledge base completo y una nube individual por subdirectorio, para validar la relevancia temática del corpus y detectar términos dominantes.

### Avance 2 — Ingeniería de Características (`deliverables/Avance2#16.ipynb`)

Se diseñó e implementó el pipeline de transformación de documentos no estructurados para el sistema RAG:

- Se definió la estrategia de integración por niveles: carga directa para los YAML, pipeline RAG para documentos de referencia, y lectura completa para los documentos del patrocinador.
- Se implementó `src/rag/ingest.py` con las funciones de extracción de texto (`pdfplumber`, `python-docx`), fragmentación con solapamiento, y persistencia en ChromaDB usando el modelo multilingüe `paraphrase-multilingual-MiniLM-L12-v2`.
- Se implementó `search_collection` para consultas semánticas sobre el índice y se documentó el flujo completo del patrón RAG: consulta → recuperación de chunks → ensamblaje de contexto → generación con Claude API.
- Se demostró cada función del pipeline con archivos reales de la base de conocimiento.

### Avance 3 — Modelo Baseline con S3 Vectors (`deliverables/Avance3/Avance3.16.ipynb`)

Se migró el vector store de ChromaDB local a **Amazon S3 Vectors** y los embeddings de MiniLM (384d, local) a **Amazon Titan Text Embeddings V2** (1024d, Bedrock). Esta migración establece el baseline productivo del pipeline RAG:

1. **Infraestructura cloud:** Creación del vector bucket y el vector index en S3 Vectors con métrica coseno y metadata filtrable por `source`, `folder` y `chunk`.
2. **Ingesta:** Pipeline de extracción, chunking (500 chars, solapamiento 80) y embedding con Titan V2. Los chunks procesados se persisten en `s3://mna-s3-proyecto-integrador/processed/`.
3. **Búsqueda semántica:** Función `search_s3vectors` con filtrado opcional por subcarpeta. Se valida con tres consultas representativas en español e inglés.
4. **Evaluación del baseline:** Métricas MRR, Precision@5 y score coseno promedio sobre cinco consultas de dominio. Umbral mínimo aceptable: MRR > 0.5, Precision@5 > 0.4, score > 0.5.

### Avance 4 — Benchmarking de Modelos y Frameworks Agénticos (`deliverables/Avance4/Avance4.16.ipynb`)

Se evaluó el rendimiento de los modelos generativos de Amazon Bedrock y los frameworks de orquestación agéntica para seleccionar la configuración óptima del sistema multi-agente:

1. **Benchmark de modelos base:** Evaluación de 5 modelos (Claude Sonnet 4, Claude Haiku 3.5, Claude Sonnet 3.5 v2, Nova Pro, Nova Lite) midiendo latencia de invocación, TTFT, tokens de entrada/salida y longitud de respuesta.
2. **Extended Thinking:** Comparación con y sin thinking habilitado para cuantificar el trade-off latencia/calidad en tareas de auditoría (gap analysis, generación de hallazgos).
3. **Sensibilidad a parámetros:** Análisis del impacto de temperature y max_tokens sobre latencia y calidad de respuesta.
4. **Frameworks agénticos:** Benchmark comparativo de LangChain, Strands Agents y LangGraph midiendo overhead, tokens y ciclos del agent loop, todos integrados con Amazon Bedrock AgentCore.

---

## Archivos Clave de la Base de Conocimiento

### `knowledge-base/iso27001/iso-iec-27001-2013-es.yaml`

Archivo de referencia central de la norma ISO/IEC 27001:2013 en español. Es el archivo que se usa en tiempo de ejecución para construir el texto de cada cláusula que se inyecta en el placeholder `{{CLAUSE_TO_EVALUATE}}` de los prompts de los subagentes.

**Origen:** Este archivo fue construido manualmente combinando dos fuentes:

1. `knowledge-base/ciso-assistant-community/iso27001-2013.yaml`: usado como referencia de estructura y esquema (campos `urn`, `ref_id`, `name`, `assessable`, `depth`, `parent_urn`, `reference_controls`).
2. `knowledge-base/iso27001/iso-iec-27001-2013-en-words.pdf`: texto normativo completo de la norma en inglés, traducido al español para producir los campos `description` y `components` de cada nodo evaluable.

**Contenido por nodo evaluable:**

- `ref_id`: identificador oficial de la cláusula (ej. `9.3`, `6.1.2`, `A.5.1.1`)
- `name`: nombre oficial de la cláusula en español
- `description`: requisito normativo principal ("La organización debe...")
- `components`: lista de sub-requisitos atómicos (a, b, c...) derivados del texto de la norma, que permiten al agente descomponer la cláusula en ítems verificables

**Uso en código:**

```python
# Obtener el catálogo completo de cláusulas evaluables
clauses = u.load_assessable_nodes('knowledge-base/iso27001/iso-iec-27001-2013-es.yaml')

# Construir el texto de una cláusula específica para inyectarlo en el prompt
clause_text = u.build_clause_text('knowledge-base/iso27001/iso-iec-27001-2013-es.yaml', '9.3')
```