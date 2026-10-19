# Resumen Ejecutivo: Sistema Multi-Agente para Auditoría ISO 27001

## 1. Sintesis del Problema

Las auditorías de Sistemas de Gestion de Seguridad de la Informacion (SGSI) bajo ISO/IEC 27001 representan un proceso intensivo en conocimiento especializado que enfrenta tres limitaciones estructurales. En primer lugar, la escasez global de auditores certificados restringe la capacidad de las organizaciones para evaluar su postura de seguridad con la frecuencia que demanda el panorama actual de amenazas. En segundo lugar, la subjetividad inherente al juicio humano genera inconsistencias entre auditores al evaluar los mismos controles, particularmente en dominios técnicos donde la interpretacion normativa admite ambiguedades. En tercer lugar, el costo y la duración de una auditoría completa (entre 3 y 6 semanas para organizaciones medianas) limitan el acceso de pequeñas y medianas empresas a procesos de certificacion.

El presente proyecto propone un sistema multi-agente basado en modelos de lenguaje de gran escala (LLMs) que automatiza las fases de planificacion, recopilacion de evidencia, evaluacion de controles y consolidacion de hallazgos de una auditoría ISO 27001. El sistema opera sobre un pipeline de Retrieval-Augmented Generation (RAG) que ingesta la documentacion organizacional del auditado y la correlaciona con el texto normativo de la norma para producir evaluaciones de conformidad fundamentadas en evidencia documental.

La solucion aborda ambas versiones vigentes de la norma: ISO 27001:2022 (93 controles en 4 categorías tematicas) e ISO 27001:2013 (114 controles en 14 dominios), permitiendo evaluar organizaciones independientemente de la version adoptada.

## 2. Hallazgos del Analisis Exploratorio de Datos

### 2.1 Composicion de la Base de Conocimiento

El analisis exploratorio se realizo sobre un corpus de 23 documentos organizados en cinco categorías que constituyen la base de conocimiento del sistema RAG:

| Categoría | Documentos | Formatos | Proposito |
|-----------|-----------|----------|-----------|
| Reportes de auditoría reales | 7 | PDF, DOCX | Estructura y lenguaje de hallazgos |
| Metodología de auditoría | 4 | PDF | Frameworks de planificacion (ISO 19011) |
| Normas ISO en formato YAML | 4 | YAML | Controles legibles por maquina (27001:2013, 27001:2022, 22301, 42001) |
| Texto normativo ISO 27001 | 1 | PDF | Fuente de citacion RAG |
| Documentos del patrocinador | 7 | PDF, DOCX | Evidencia organizacional real para gap analysis |

### 2.2 Validacion Estadística de Metadatos para Filtrado

Se aplicaron pruebas de Chi-cuadrado y ANOVA para determinar que variables de metadatos discriminan efectivamente entre chunks relevantes e irrelevantes para consultas de auditoría:

| Metadato | Prueba | Estadístico | p-valor | Decision |
|----------|--------|-------------|---------|----------|
| document_type | Chi-cuadrado | 45.23 | < 0.001 | Filtro retenido (+15% Precision@5) |
| source_category | Chi-cuadrado | 38.67 | 0.0003 | Filtro retenido |
| compliance_domain | Chi-cuadrado | 52.89 | 0.00001 | Filtro prioritario |
| keyword_density | ANOVA F-test | 23.67 | 0.00001 | Predictor de relevancia |
| chunk_length | ANOVA F-test | 8.45 | 0.0034 | Retenido para analisis |
| document_language | Chi-cuadrado | 3.21 | 0.073 | Eliminado (no significativo) |

### 2.3 Seleccion de Estrategia de Chunking

La comparacion entre estrategias de fragmentacion demostro que el chunking semantico supera consistentemente a las alternativas:

| Estrategia | Recall@5 | MRR | Configuracion |
|------------|----------|-----|---------------|
| Fixed 300 tokens | 0.72 | 0.58 | Sin solapamiento |
| Fixed 512 tokens | 0.78 | 0.64 | 20% solapamiento |
| Semantico | 0.85 | 0.71 | bufferSize=1, breakpoint=95% |
| Jerarquico | 0.82 | 0.69 | Parent 1500, child 300 |

El chunking semantico fue seleccionado como estrategia de produccion por su capacidad de mantener la coherencia de los controles ISO dentro de un mismo fragmento, aprovechando la agrupacion por similitud semantica entre oraciones adyacentes.

### 2.4 Metricas Baseline del Pipeline RAG

El pipeline de produccion alcanza las siguientes metricas con Amazon Titan Text Embeddings V2 (1024 dimensiones) y Amazon S3 Vectors:

| Metrica | Valor | Umbral Aceptable |
|---------|-------|-------------------|
| Recall@5 | 0.85 | > 0.70 |
| Precision@5 | 0.89 | > 0.40 |
| MRR (Mean Reciprocal Rank) | 0.71 | > 0.50 |
| Latencia promedio de retrieval | 68 ms | < 200 ms |

## 3. Modelos Generados y Razones de la Eleccion del Modelo Final

### 3.1 Modelos de Lenguaje Evaluados

Se evaluaron once modelos de lenguaje de gran escala disponibles en Amazon Bedrock con el proposito de determinar la asignacion optima por agente especialista dentro del sistema multi-agente:

| # | Modelo | Proveedor | Características Principales | Español Nativo |
|---|--------|-----------|---------------------------|----------------|
| 1 | GPT-OSS-120B | OpenAI | Arquitectura MoE de 120B parametros, contexto 128K tokens, razonamiento de produccion, latencia balanceada, costo medio. Sin invocacion nativa de herramientas. | No |
| 2 | GPT-OSS-20B | OpenAI | Version compacta y economica del GPT-OSS, orientada a tareas de menor complejidad. | No |
| 3 | Qwen3 32B | Alibaba | 32B parametros denso, baja latencia (TTFT < 500ms), costo bajo, invocacion nativa de herramientas, modos de pensamiento hibridos. Soporte de 100+ idiomas. | Si |
| 4 | Claude Sonnet 4.5 | Anthropic | Contexto de 200K tokens, capacidades superiores en analisis estructurado, invocacion de herramientas y comportamiento agentico. Costo medio. | Si |
| 5 | Claude Haiku 4.5 | Anthropic | Contexto de 200K tokens con latencia rapida y costo bajo. Rendimiento adecuado para clasificacion y recuperacion de evidencia. | Si |
| 6 | Llama 4 Maverick 17B | Meta | Arquitectura MoE eficiente, multimodal, costo bajo, latencia rapida, invocacion nativa de herramientas. Ajuste fino para 12 idiomas. | Si |
| 7 | Llama 4 Scout 17B | Meta | Configuracion similar a Maverick, alternativa de costo bajo para sub-agentes con soporte multilingue de 12 idiomas. | Si |
| 8 | Mistral Large 3 | Mistral | 675B parametros MoE (41B activos), rendimiento superior en invocacion de herramientas y evaluaciones estructuradas, contexto 128K, costo medio. | Si |
| 9 | DeepSeek R1 | DeepSeek | Razonamiento excepcional mediante cadenas de pensamiento extendidas, ideal para analisis cruzado complejo. Latencia elevada, sin invocacion de herramientas. Razonamiento interno en chino e ingles. | No |
| 10 | Nova Pro | Amazon | Modelo nativo de Bedrock con capacidades de parsing y generacion, costo medio. Proficiencia especial en 15 idiomas, capacidad general en 200+. | Si |
| 11 | Nova Lite | Amazon | Version ligera de Nova Pro con costo reducido y misma capacidad multilingue. | Si |

### 3.2 Criterios de Seleccion

La asignacion de modelos por agente se fundamento en cinco criterios evaluados mediante el framework de Amazon Bedrock Evaluations, utilizando un dataset de benchmark especifico para tareas de auditoría ISO 27001 compuesto por seis categorías de evaluacion: valoracion de controles, analisis de evidencia, generacion de reportes, razonamiento cruzado entre dominios, completitud de hallazgos y adherencia a formato.

1. Capacidad de razonamiento: se priorizaron modelos de mayor capacidad (GPT-OSS-120B, DeepSeek R1) para tareas que requieren analisis logico complejo y verificacion de consistencia entre multiples dominios de control.

2. Latencia: se asignaron modelos de respuesta rapida (Qwen3 32B, Claude Haiku 4.5) para operaciones de alto volumen como la recuperacion de evidencia desde la Knowledge Base y la evaluacion de dominios con menor cantidad de controles.

3. Soporte de invocacion de herramientas: se seleccionaron modelos con capacidad nativa de invocacion de funciones (Claude, Mistral, Qwen, Llama) para agentes que requieren ejecutar herramientas del pipeline RAG, consultar DynamoDB o almacenar reportes en S3.

4. Costo operativo: se asignaron modelos de costo bajo para sub-agentes de menor complejidad, reservando modelos de costo medio exclusivamente para funciones donde la calidad de salida justifica la inversion incremental.

5. Soporte nativo de español: dado que la evaluacion ISO se realiza sobre documentacion organizacional redactada en español y el reporte final se genera en el mismo idioma, se priorizaron modelos con soporte nativo documentado por el proveedor. Los tres modelos sin soporte nativo (GPT-OSS-120B, GPT-OSS-20B y DeepSeek R1) se asignaron exclusivamente a funciones de razonamiento donde el idioma del procesamiento interno no afecta la calidad de la salida final.

### 3.3 Asignacion Final por Agente

#### ISO 27001:2022 (Sistema Multi-Agente Principal)

El sistema principal implementa siete agentes especializados siguiendo el patron "Agents as Tools" del SDK Strands Agents, donde cada sub-agente se despliega como una funcion invocable por el orquestador central.

| Agente | Modelo Fase 1 (API) | Modelo Fase 2 (QLoRA) | Justificacion |
|--------|---------------------|------------------------|---------------|
| Planificacion | Nova Pro | Ministral 3 8B | Generacion estructurada con soporte nativo de español. El plan de auditoría requiere adherencia a ISO 19011:2018, no razonamiento extremo. |
| Recopilacion de Evidencia | Qwen3 32B | Ministral 3 8B | Latencia rapida para multiples consultas semanticas contra la Knowledge Base. Invocacion nativa de herramientas. Costo bajo para alto volumen de operaciones. |
| Controles Organizacionales (A.5) | GPT-OSS-120B | Ministral 3 8B | 37 controles complejos que exigen razonamiento profundo sobre interrelaciones entre politicas, riesgos, proveedores y cumplimiento regulatorio. |
| Controles de Personas (A.6) | Qwen3 32B | Ministral 3 8B | Dominio reducido de 8 controles con menor complejidad tecnica. La latencia rapida permite evaluaciones eficientes sin sacrificar calidad. |
| Controles Fisicos (A.7) | Nova Pro | Ministral 3 8B | 14 controles que requieren evaluacion precisa pero no razonamiento extremo. Balance adecuado entre calidad y costo. |
| Controles Tecnologicos (A.8) | GPT-OSS-120B | Ministral 3 8B | 34 controles tecnicos que abarcan vulnerabilidades, criptografía, redes y desarrollo seguro. Requiere capacidad analitica superior. |
| Consolidacion (Orchestrator) | GPT-OSS-120B | DeepSeek-R1-0528-Qwen3-8B | Maxima capacidad de razonamiento para verificacion cruzada entre dominios, deteccion de problemas sistemicos y generacion del reporte final consolidado. |

#### ISO 27001:2013 (Sistema de Comparacion)

El sistema de comparacion implementa tres agentes evaluadores mas un agente juez, siguiendo la estructura de 114 controles en 14 dominios de la version 2013.

| Agente | Modelo Asignado | Justificacion |
|--------|----------------|---------------|
| Gobernanza (Clausulas 4 a 10) | Claude Sonnet 4.5 | Analisis estructurado de requisitos normativos con adherencia estricta a formato JSON. Soporte nativo de español. |
| Organizacional (A.5 a A.8, A.15, A.16, A.18) | Claude Sonnet 4.5 | Evaluacion de 45 controles con salida JSON estricta (observations, ranking, ranking_judgement, recommendations). |
| Tecnico (A.9 a A.14, A.17) | Claude Sonnet 4.5 | Analisis de 69 controles tecnicos que demandan interpretacion de configuraciones e infraestructura. |
| Juez (LLM-as-a-Judge) | Claude Sonnet 4.5 | Evaluacion de calidad (0 a 100) en cuatro dimensiones requiere modelo imparcial con fuerte adherencia a instrucciones. |

## 4. Evaluacion de Frameworks de Orquestacion Multi-Agente

### 4.1 Frameworks Evaluados

Se implementaron y compararon cuatro frameworks de orquestacion para determinar el mas adecuado para coordinar los agentes especializados del sistema de auditoría. Los cuatro comparten la misma base de modelos y herramientas (RAG, DynamoDB, S3), diferenciandose unicamente en el patron de coordinacion y la infraestructura de runtime.

| Framework | Version | Patron de Orquestacion | Paralelismo | Integracion Bedrock |
|-----------|---------|------------------------|-------------|---------------------|
| Strands Agents | 1.20.0 | Agents as Tools (sub-agentes como funciones `@tool`) | Delegado al orquestador LLM | Nativo (SDK de Amazon) |
| LangGraph | 0.4.7 | StateGraph con nodos tipados y edges condicionales | Fan-out explicito (evaluadores en paralelo) | Via langchain-aws 0.2.17 |
| CrewAI | 1.2.0 | Agents con role/goal/backstory y Tasks secuenciales | Proceso secuencial o jerarquico | Via LiteLLM (adaptador) |
| Comp2013 (custom) | Internal | Loop secuencial por clausula con retrieval pre-invocacion | Ninguno (estrictamente secuencial) | Directo (boto3 bedrock-runtime) |

### 4.2 Criterios de Comparacion

La evaluacion se realizo mediante el unified audit runner (`backend/run_audit.py`) que ejecuta la misma auditoría sobre la misma organizacion con los cuatro frameworks y recopila metricas de observabilidad comparables:

1. Tiempo total de ejecucion (wall time): duracion completa de la auditoría desde la planificacion hasta la consolidacion del reporte.

2. Overhead del framework: tiempo consumido en coordinacion, serializacion de estado, paso de mensajes y gestion de dependencias, separado del tiempo de inferencia LLM y ejecucion de herramientas.

3. Consumo de tokens: total de tokens de entrada y salida procesados, incluyendo tokens de coordinacion internos del framework que no contribuyen directamente al contenido del reporte.

4. Consistencia de resultados: grado de concordancia entre los hallazgos producidos por cada framework al evaluar la misma evidencia con los mismos modelos.

5. Complejidad de implementacion: lineas de codigo, dependencias externas y esfuerzo de mantenimiento.

### 4.3 Analisis Comparativo

| Dimension | Strands Agents | LangGraph | CrewAI | Comp2013 |
|-----------|---------------|-----------|--------|----------|
| Patron de flujo | Orquestador LLM decide orden | Grafo DAG predefinido | Secuencial con context chaining | Loop por clausula |
| Paralelismo de evaluadores | Implicito (si el LLM invoca multiples tools) | Explicito (fan-out en grafo) | No nativo (proceso secuencial) | No disponible |
| Overhead de framework | Bajo (invocacion directa) | Medio (gestion de estado tipado) | Alto (abstracciones de Agent/Task/Crew) | Minimo (boto3 directo) |
| Tokens de coordinacion | Medios (prompts del orquestador) | Bajos (sin LLM de coordinacion) | Altos (context propagation verbose) | Bajos (sin coordinacion inter-agente) |
| Dependencias externas | 1 (strands-agents) | 2 (langgraph, langchain-aws) | 2 (crewai, litellm) | 0 (solo boto3) |
| Soporte nativo AgentCore | Completo (deploy como runtime) | Parcial (requiere wrapper) | Parcial (requiere wrapper) | No aplica |
| Gestion de memoria | Nativa (AgentCore Memory) | Manual (state persistence) | Limitada (memory experimental) | No disponible |
| Observabilidad | FlowTracker integrado | FlowTracker integrado | FlowTracker integrado | FlowTracker integrado |
| Escalabilidad a produccion | Alta (AgentCore serverless) | Media (requiere infra custom) | Media (requiere infra custom) | Baja (monolitico) |

### 4.4 Ventajas y Limitaciones por Framework

Strands Agents ofrece la integracion mas natural con el ecosistema AWS al ser el SDK nativo de Amazon Bedrock AgentCore. El patron "Agents as Tools" permite que el orquestador LLM decida dinamicamente el orden de invocacion basandose en el contexto de la auditoría, lo cual es ventajoso cuando ciertas evaluaciones dependen de hallazgos previos. Su limitacion principal radica en que delega decisiones de flujo al modelo, introduciendo no-determinismo en el orden de ejecucion.

LangGraph proporciona control deterministico sobre el flujo de ejecucion mediante un grafo de estados tipado. El fan-out explicito para evaluadores de dominio reduce el tiempo total al ejecutar A.5, A.6, A.7 y A.8 en paralelo tras la fase de evidencia. Su limitacion es la dependencia del ecosistema LangChain, que introduce capas de abstraccion adicionales entre el codigo y la API de Bedrock.

CrewAI facilita la definicion declarativa de agentes mediante roles, objetivos y backstories, lo cual mejora la legibilidad del codigo y permite a desarrolladores no especializados comprender la arquitectura. Su limitacion principal es el overhead de tokens: la propagacion de contexto entre tareas serializa outputs completos de etapas anteriores, incrementando significativamente el consumo de tokens de entrada en etapas posteriores.

Comp2013 (implementacion custom) ofrece el minimo overhead al interactuar directamente con la API de Bedrock sin abstracciones intermedias. Es la implementacion mas eficiente en tokens y la mas facil de depurar. Su limitacion es la ausencia de paralelismo y la rigidez del flujo secuencial que no puede adaptarse a escenarios donde la evidencia sugiere priorizar ciertos dominios.

### 4.5 Seleccion del Framework Principal

Se selecciono Strands Agents como framework principal de produccion por tres razones:

1. Compatibilidad nativa con Amazon Bedrock AgentCore, que permite desplegar cada agente como un endpoint serverless independiente con escalamiento automatico, gestion de memoria integrada y monitoreo nativo.

2. Flexibilidad del patron "Agents as Tools" que permite al sistema evolucionar hacia flujos adaptativos donde el orquestador puede repetir evaluaciones, solicitar evidencia adicional o escalar hallazgos entre dominios sin modificar la topologia del grafo.

3. Los tres frameworks restantes se mantienen como implementaciones de comparacion para validar consistencia de resultados y como opciones de fallback ante limitaciones especificas de Strands en escenarios futuros.

## 5. Recomendaciones Clave para Implementar la Solucion

### 5.1 Plataforma de Despliegue

Se selecciono Amazon Web Services como plataforma de produccion por las siguientes razones fundamentadas:

1. Amazon Bedrock AgentCore proporciona un framework nativo para despliegue de agentes con endpoints HTTP independientes, gestion de memoria (corto y largo plazo) y enrutamiento de herramientas mediante el protocolo MCP, eliminando la necesidad de infraestructura custom de orquestacion.

2. La disponibilidad de once modelos de multiples proveedores (OpenAI, Anthropic, Meta, Mistral, Alibaba, DeepSeek, Amazon) en una sola API unificada reduce la dependencia de un unico proveedor de modelos y permite rotacion sin cambios arquitectonicos.

3. Los servicios nativos de Amazon (S3 Vectors, Knowledge Bases, Step Functions, Lambda) permiten construir el pipeline RAG completo sin componentes de terceros, reduciendo la superficie de integracion y simplificando la operacion.

4. El modelo de costos pay-per-token de Bedrock elimina compromisos de capacidad reservada, alineandose con el patron de uso esporadico de un sistema de auditoría que se ejecuta por demanda.

### 5.2 Requisitos para Produccion

1. Configurar Amazon Bedrock Knowledge Bases con chunking semantico (bufferSize=1, breakpointPercentileThreshold=95) y el modelo de parsing Amazon Nova Pro para documentos PDF con tablas e imagenes.

2. Desplegar cada agente como un runtime independiente en AgentCore con su propio endpoint, permitiendo escalamiento horizontal por dominio segun la carga de auditorías concurrentes.

3. Implementar memoria de corto plazo (sesion de auditoría) y largo plazo (hallazgos previos, contexto organizacional) mediante las primitivas de AgentCore Memory con estrategias de resumen y busqueda semantica.

4. Establecer pipelines de evaluacion continua mediante Bedrock Evaluations para monitorear degradacion de calidad conforme los modelos base se actualizan.

### 5.3 Acciones para las Partes Interesadas

Para auditores: el sistema no reemplaza el juicio profesional, sino que automatiza las fases de recopilacion y analisis inicial, permitiendo que el auditor humano se enfoque en la interpretacion contextual y la validacion de hallazgos.

Para organizaciones auditadas: deben digitalizar su documentacion de SGSI en formatos procesables (PDF con texto, Markdown, YAML) y mantener un repositorio actualizado que el sistema pueda ingestar.

Para la direccion: el sistema habilita auditorías internas mas frecuentes (mensuales en lugar de anuales) con costo marginal reducido, mejorando la postura de seguridad de forma continua.

## 6. Analisis Costo-Beneficio

### 6.1 Costos por Fase CRISP-ML(Q)

| Fase | Componente | Costo Estimado (USD) | Frecuencia |
|------|-----------|---------------------|-----------|
| Comprension del negocio | Licenciamiento de normas ISO | 200 | Unico |
| Ingeniería de datos | S3 almacenamiento (100 GB) | 2.30/mes | Mensual |
| Ingeniería de datos | Titan Embeddings V2 (ingesta 23 docs) | 0.15 | Por ingesta |
| Ingeniería de datos | S3 Vectors (almacenamiento index) | 5.00/mes | Mensual |
| Ingeniería de datos | Lambda (pipeline Step Functions) | 1.50/mes | Mensual |
| Modelado | Bedrock API tokens (desarrollo y evaluacion) | 150/mes | Desarrollo |
| Modelado | SageMaker QLoRA fine-tuning (ml.g5.2xlarge) | 45/ejecucion | Por modelo |
| Evaluacion | Bedrock Evaluations (benchmark jobs) | 20/ejecucion | Trimestral |
| Despliegue | AgentCore Runtime (7 agentes) | 0 (pay-per-invocation) | Por uso |
| Operacion | Tokens consumidos por auditoría completa | 8 a 15 | Por auditoría |

### 6.2 Costos de Operacion y Mantenimiento

| Concepto | Costo Mensual Estimado (USD) | Supuesto |
|----------|------------------------------|----------|
| Infraestructura base (S3, Vectors, DynamoDB) | 12 | Almacenamiento < 100 GB |
| Tokens de modelo por auditoría (7 agentes) | 8 a 15 | 1 auditoría completa (~200K tokens entrada, ~50K salida) |
| Monitoreo y logging (CloudWatch) | 5 | Retención 30 dias |
| Actualizacion de Knowledge Base (re-ingesta mensual) | 2 | < 50 documentos |
| Total mensual (operacion pasiva) | 19 | Sin auditorías activas |
| Total por auditoría ejecutada | 27 a 34 | Incluyendo infra + tokens |

### 6.3 Beneficios Potenciales

Eficiencia operativa: una auditoría completa de 93 controles que tradicionalmente requiere entre 3 y 6 semanas de trabajo de un equipo de 2 a 3 auditores puede ejecutarse en menos de una hora de procesamiento computacional. Asumiendo un costo de auditor de 150 USD/hora y un equipo de 2 personas durante 4 semanas (320 horas), el costo tradicional asciende a aproximadamente 48,000 USD frente a los 30 USD del sistema automatizado por ejecucion.

Frecuencia de evaluacion: el costo marginal reducido habilita auditorías internas mensuales (12 por año a un costo de 360 USD anuales) frente a la practica actual de una auditoría interna anual (48,000 USD), representando un ahorro del 99.2% y un incremento de 12 veces en la frecuencia de evaluacion.

Consistencia: la eliminacion de variabilidad entre auditores produce evaluaciones reproducibles donde el mismo conjunto de evidencia genera los mismos hallazgos independientemente del momento de ejecucion, siempre que se utilice temperatura 0.0 en los modelos evaluadores.

Accesibilidad: organizaciones pequeñas y medianas que actualmente no pueden costear auditorías externas obtienen acceso a evaluaciones de conformidad de calidad profesional con una inversion inferior a 400 USD anuales.

Generacion de oportunidades: el sistema puede posicionarse como servicio SaaS de evaluacion continua de conformidad, creando una nueva linea de negocio para firmas de consultoría que deseen escalar su capacidad de auditoría sin incrementar proporcionalmente su plantilla de auditores certificados.

## 7. Riesgos y Desafíos de la Solucion

### 7.1 Riesgos Relacionados con los Datos

1. Calidad de la documentacion de entrada: si la organizacion auditada mantiene documentacion desactualizada, incompleta o en formatos no procesables (imagenes escaneadas sin OCR), la calidad de la evaluacion se degrada proporcionalmente. El sistema no puede generar hallazgos correctos a partir de evidencia incorrecta.

2. Sesgo en la base de conocimiento: los 7 reportes de auditoría reales provienen predominantemente de organizaciones anglosajonas, lo cual puede introducir sesgos culturales en la interpretacion de controles que varian segun jurisdiccion (por ejemplo, requisitos de privacidad, legislacion laboral).

3. Temporal drift: las actualizaciones de la norma, cambios regulatorios o nuevas interpretaciones de los organismos de certificacion requieren actualizacion periodica de la Knowledge Base. Sin mantenimiento, el sistema producira evaluaciones basadas en criterios obsoletos.

### 7.2 Riesgos Relacionados con Ataques

1. Inyeccion de prompt via documentos: un actor malicioso podria insertar instrucciones adversarias dentro de la documentacion organizacional que, al ser ingestada por el RAG, manipulen las evaluaciones del agente para ocultar no conformidades reales.

2. Exfiltracion de datos sensibles: la documentacion del SGSI contiene información confidencial sobre controles de seguridad, vulnerabilidades conocidas y arquitectura de red. El procesamiento mediante APIs de modelos en la nube implica transmision de esta información a infraestructura de terceros.

3. Manipulacion del vector store: el acceso no autorizado al indice vectorial permitiria modificar o eliminar chunks críticos, alterando los resultados de las consultas RAG sin dejar evidencia visible en los documentos fuente.

### 7.3 Riesgos Relacionados con Prueba y Confianza

1. Alucinaciones del modelo: los LLMs pueden generar hallazgos que no estan fundamentados en la evidencia recuperada, citando documentos inexistentes o atribuyendo requisitos incorrectos a controles especificos. La verificacion cruzada del orchestrator mitiga pero no elimina este riesgo.

2. Falta de explicabilidad granular: aunque el sistema cita fuentes RAG, el razonamiento interno que lleva de la evidencia al nivel de conformidad asignado no es completamente transparente, limitando la capacidad del auditor humano para validar la logica de evaluacion.

3. Variabilidad entre ejecuciones: incluso con temperatura 0.0, diferencias en el orden de recuperacion de chunks o en la version del modelo pueden producir resultados ligeramente distintos entre ejecuciones, complicando la reproducibilidad estricta requerida en contextos de certificacion.

4. Sobrecarga de confianza: el riesgo de que las organizaciones acepten los resultados del sistema como definitivos sin validacion humana, especialmente cuando los hallazgos son favorables y no incentivan escrutinio adicional.

### 7.4 Riesgos Relacionados con Cumplimiento

1. Aceptacion por organismos de certificacion: actualmente ningun organismo acreditado reconoce evaluaciones generadas por inteligencia artificial como evidencia valida en auditorías de certificacion. El sistema puede soportar auditorías internas pero no sustituir la evaluacion humana requerida para certificacion externa.

2. Responsabilidad legal: la atribucion de responsabilidad ante un hallazgo incorrecto (falso negativo que resulta en una brecha de seguridad post-certificacion) no esta definida cuando la evaluacion fue generada por un sistema autonomo.

3. Proteccion de datos personales: el procesamiento de documentos que contienen datos personales de empleados (registros de RRHH, verificaciones de antecedentes) mediante APIs de modelos en la nube puede entrar en conflicto con regulaciones de proteccion de datos como la LFPDPPP en Mexico o el RGPD en la Union Europea.

4. Requisitos de retencion: la norma ISO 27001 exige retencion de registros de auditoría por periodos definidos. Los logs de conversacion entre agentes y los tokens procesados por modelos de terceros pueden no cumplir con los requisitos de cadena de custodia de evidencia de auditoría.

## Referencias

Chapman, P., Clinton, J., Kerber, R., Khabaza, T., Reinartz, T., Shearer, C. y Wirth, R. (2000). *CRISP-DM 1.0: Step-by-step data mining guide*. SPSS Inc. https://github.com/almirgouvea/The-Crisp-DM-Methodology/blob/main/The_CRISP_DM_user_guide.pdf

Forman, G. (2003). An extensive empirical study of feature selection metrics for text classification. *Journal of Machine Learning Research*, *3*. https://www.jmlr.org/papers/v3/forman03a.html

Gao, Y., Xiong, Y., Gao, X., Jia, K., Pan, J., Bi, Y., ... Wang, H. (2023). Retrieval-augmented generation for large language models: A survey. *arXiv*. https://arxiv.org/abs/2312.10997

Guyon, I. y Elisseeff, A. (2003). An introduction to variable and feature selection. *Journal of Machine Learning Research*, *3*. https://www.jmlr.org/papers/v3/guyon03a.html

International Organization for Standardization. (2013). *Information technology: Security techniques: Information security management systems: Requirements* (ISO/IEC 27001:2013). https://www.iso.org/standard/54534.html

International Organization for Standardization. (2018). *Guidelines for auditing management systems* (ISO 19011:2018). https://www.iso.org/standard/70017.html

International Organization for Standardization. (2022). *Information security, cybersecurity and privacy protection: Information security management systems: Requirements* (ISO/IEC 27001:2022). https://www.iso.org/standard/27001

Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., ... Kiela, D. (2020). Retrieval-augmented generation for knowledge-intensive NLP tasks. *Advances in Neural Information Processing Systems*, *33*. https://proceedings.neurips.cc/paper/2020/hash/6b493230205f780e1bc26945df7481e5-Abstract.html

Manning, C. D., Raghavan, P. y Schutze, H. (2008). *Introduction to information retrieval*. Cambridge University Press. https://nlp.stanford.edu/IR-book/

OpenAI. (2025). *GPT-OSS-120B and GPT-OSS-20B model card*. https://openai.com/index/gpt-oss-model-card/

Raunak, V., Gupta, V. y Metze, F. (2019). Effective dimensionality reduction for word embeddings. *Proceedings of the 4th Workshop on Representation Learning for NLP*. https://aclanthology.org/W19-4328/

Studer, S., Bui, T. B., Drescher, C., Hanuschkin, A., Winkler, L., Peters, S. y Muller, K. R. (2021). Towards CRISP-ML(Q): A machine learning process model with quality assurance methodology. *Machine Learning and Knowledge Extraction*, *3*(2). https://www.mdpi.com/2504-4990/3/2/20

Wang, L., Yang, N., Huang, X., Yang, L., Majumder, R. y Wei, F. (2024). Improving text embeddings with large language models. *Proceedings of the 62nd Annual Meeting of the ACL*. https://arxiv.org/abs/2401.00368

Zheng, A. y Casari, A. (2018). *Feature engineering for machine learning: Principles and techniques for data scientists*. O'Reilly Media. https://www.oreilly.com/library/view/feature-engineering-for/9781491953235/

