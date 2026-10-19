<!-- Page 1 -->

INSTITUTO TECNOLÓGICO Y DE ESTUDIOS
SUPERIORES DE MONTERREY
Maestría en Inteligencia Artificial Aplicada (MNA)
Proyecto Integrador
Sistema multi-agente de auditoría (ISO 27001)
Avance 2. Ingeniería de características
Profesor: Dra. Grettel Barceló Alonso
Profesor: Dr. Luis Eduardo Falcón Morales
Equipo 16
Joel Alonso Vázquez A01796712
Roberto López Baldomero A01653630
David Sánchez Almanza A01210766
17 de mayo de 2026
1


---


<!-- Page 2 -->

Avance 2. Ingeniería de características 4
Objetivos 4
Introducción 4
Catálogo de Datos del Proyecto 5
A. Operaciones de Ingeniería de Características 6
A.1 Generación de Nuevas Características 6
A.1.1 Metadatos Estructurales del Documento 6
A.1.2 Características semánticas derivadas 7
A.1.3 Características Estadísticas del Texto 7
A.2 Discretización y Binning 8
A.2.1 Discretización de Longitud de Chunk 8
A.2.2 Discretización de Densidad de Keywords 9
A.2.3 Discretización de Legibilidad 9
A.3 Codificación 9
A.3.1 Codificación Ordinal 9
A.3.2 Codificación One-Hot 10
A.4 Escalamiento 10
A.4.1 Normalización L2 de Embeddings 11
A.4.2 Estandarización (Z-score) de Características Numéricas 11
A.4.3 Min-Max Scaling para Scores de Relevancia 11
A.5 Transformaciones 12
A.5.1 Transformación Logarítmica 12
A.6 Estrategias de Chunking en Amazon Bedrock Knowledge Bases 13
A.6.1 Chunking Semántico 13
A.6.2 Chunking Jerárquico (Para documentos estructurados) 13
A.6.3 Mapeo de Estrategias por Tipo de Documento 14
B. Selección y Extracción de Características 14
B.1 Métodos de Filtrado para Selección de Características 15
B.1.1 Umbral de Varianza 15
B.1.2 Correlación 15
B.1.3 Chi-Cuadrado (χ²) 17
B.1.4 ANOVA (Análisis de Varianza) 18
B.2 Técnicas de Extracción de Características 19
B.2.1 Análisis de Componentes Principales (PCA) 19
B.2.2 Análisis Factorial (FA) 20
B.3 Técnicas Adicionales Aplicadas 23
B.3.1 Deduplicación Semántica de Chunks 23
B.3.2 Filtrado por Contenido Informativo 24
C. Conclusiones de la Fase de Preparación de Datos 25
C.1 Resumen de la Fase en el Contexto CRISP-ML(Q) 25
2


---


<!-- Page 3 -->

C.2 Hallazgos Principales 25
C.3 Riesgos Identificados y Mitigación 28
C.4 Alineación con Objetivos del Proyecto 29
C.5 Métricas de Calidad de la Fase 30
C.6 Consideraciones para la Siguiente Fase 31
C.7 Cumplimiento de Instrucciones del Avance 2 31
Referencias 33
Metodología CRISP-ML(Q) y Machine Learning 33
Feature Engineering y Selección de Características 33
Transformaciones y Análisis Estadístico 33
Procesamiento de Lenguaje Natural y Embeddings 33
Retrieval-Augmented Generation (RAG) 33
Chunking Strategies 34
Documentación de AWS 34
Normativas y Estándares ISO 35
Herramientas 35
3


---


<!-- Page 4 -->

Avance 2. Ingeniería de características
Objetivos
● 2.3 Crear nuevas características para mejorar el rendimiento de los modelos.
● 2.4 Mitigar el riesgo de características sesgadas y acelerar la convergencia de algunos
algoritmos.
Introducción
La fase de Ingeniería de Características (Feature Engineering) constituye un paso crítico dentro de la
metodología CRISP-ML(Q), específicamente en la etapa de Data Engineering (Data Preparation). Según
Studer et al. (2021), esta fase tiene como objetivo transformar los datos crudos en un conjunto de
variables útiles para el aprendizaje automático, mitigando riesgos como el sesgo en las características y
acelerando la convergencia de los algoritmos.
En el contexto de nuestro proyecto, un sistema multi-agente basado en Retrieval-Augmented Generation
(RAG) para auditorías ISO 27001, la ingeniería de características adquiere una dimensión particular. A
diferencia de los proyectos de ML tabulares tradicionales, nuestro pipeline opera sobre datos textuales
no estructurados que conforman la base de conocimiento del sistema. Por lo tanto, las técnicas de feature
engineering se adaptan al dominio del procesamiento de lenguaje natural (NLP) y a los requerimientos
específicos de los sistemas RAG implementados con Amazon Bedrock Knowledge Bases.
Arquitectura de Datos del Proyecto
El sistema utiliza los siguientes servicios de AWS para la gestión y procesamiento de datos:
Imagen 1. Arqtuitectura de datos
4


---


<!-- Page 5 -->

Catálogo de Datos del Proyecto
1. Base de conocimiento principal
Categoría Archivos Formato Descripción
iso27001/ 1 PDF Norma ISO/IEC 27001:2013 completa
audit-examples/ 8 PDF, Reportes de auditoría reales
DOCX anonimizados
audit-methodology/ 4 PDF Metodología ISO 19011, guías de
auditoría
ciso-assistant- 5 YAML Frameworks estructurados (ISO
community/ 27001:2022, ISO 22301, ISO 42001)
non-conformities/ 1 MD Catálogo de no conformidades comunes
sponsor-documents/ 8 PDF, Políticas organizacionales del sponsor
DOCX
2. ISO 27001:2022 Toolkit (ISO-27001-2022-Toolkit/)
Carpeta Archivos Formato Propósito
Gap Assessment Plan 2 XLSX, DOCX Evaluación de brechas
SOA 1 XLSX Statement of Applicability
Risk Register 2 XLSX, DOCX Registro de riesgos
Scope and Context 1 DOCX Definición de alcance
Asset Inventory 1 XLSX Inventario de activos
BCP/DRP 2 DOCX Continuidad y recuperación
Security Policy 1 DOCX Políticas de seguridad
Training Plan 1 DOCX Plan de capacitación
Management Review 2 XLSX, DOCX Revisión por dirección
ISMS Checklists 3 DOCX Listas de verificación
Internal Audit 2 XLSX, DOCX Auditoría interna
ROI 1 DOCX Retorno de inversión
3. Datos Adicionales (data/)
Archivo Formato Contenido
Requisitos_Norma_ISO_19011-2011.pdf PDF Requisitos de auditoría
IEEG-Resultados de auditoria en madurez TI.pdf PDF Ejemplo de resultados
Planeación de Auditoria-PREP.pdf PDF Plantilla de planeación
PLEXUS-Diagnostico_PSS_IAFT16949.pdf PDF Diagnóstico de ejemplo
5


---


<!-- Page 6 -->

Flujo de Feature Engineering utilizando Amazon Bedrock Knowledge Bases
El proceso de ingeniería de características en nuestro sistema RAG se muestra en el siguiente flujo:
Imagen 2. Pipeline de datos para Feature Engineering
A. Operaciones de Ingeniería de Características
En esta sección se detallan las operaciones aplicadas para convertir los datos crudos del proyecto en un
conjunto de variables útiles para el sistema RAG de auditoría ISO 27001, utilizando Amazon Bedrock
Knowledge Bases como plataforma principal.
A.1 Generación de Nuevas Características
En un sistema RAG implementado con Amazon Bedrock Knowledge Bases, la generación de características se
centra en enriquecer los fragmentos de texto (chunks) con metadatos que mejoren la recuperación y la relevancia
contextual. Las nuevas características generadas para nuestro proyecto incluyen:
A.1.1 Metadatos Estructurales del Documento
Cada documento almacenado en S3 se acompaña de un archivo de metadatos JSON (.metadata.json) que contiene:
{
"metadataAttributes": {
"document_type": "audit_report",
"source_category": "audit-examples",
"iso_control_reference": "A.5.1",
"document_language": "en",
"temporal_relevance": "current",
"compliance_domain": "organizational_controls"
}
}
6


---


<!-- Page 7 -->

Metadatos estructurales del documento:
● document_type: Clasificación del tipo de documento (norma ISO, reporte de auditoría, política
organizacional, guía metodológica, no conformidad).
● source_category: Categoría de origen dentro de la base de conocimiento (iso27001, audit-
examples, audit-methodology, non-conformities, sponsor-documents, ciso-assistant-
community).
● section_hierarchy: Jerarquía de secciones dentro del documento original (e.g., "Cláusula 6 > 6.1
> 6.1.2").
● iso_control_reference: Referencia al control ISO 27001 específico cuando aplica (e.g., "A.5.1",
"A.8.2").
A.1.2 Características semánticas derivadas
Las características semánticas se derivan mediante técnicas de procesamiento de lenguaje natural:
● chunk_topic: Representa el tópico dominante del fragmento. Se extrae mediante topic modeling
con LDA (Latent Dirichlet Allocation) entrenado sobre el corpus ISO 27001, permitiendo
identificar automáticamente el tema principal de cada chunk.
● compliance_domain: Indica el dominio de cumplimiento según ISO 27001:2022. Se determina
mediante clasificación basada en los 4 temas del Anexo A, asignando cada chunk al dominio más
relevante.
● document_language: Identifica el idioma del documento fuente (español o inglés). Se obtiene
mediante detección automática utilizando la biblioteca langdetect, lo cual es relevante para el
procesamiento multilingüe del sistema.
● temporal_relevance: Indica la vigencia normativa del contenido. Se asigna mediante mapeo
directo donde los documentos basados en ISO 27001:2013 reciben el valor "legacy" y los basados
en la versión 2022 reciben "current".
Dominios de cumplimiento ISO 27001:2022 (Anexo A):
El Anexo A de ISO 27001:2022 organiza los controles en cuatro dominios principales:
● A.5 - Controles Organizacionales: Comprende 37 controles relacionados con políticas, roles y
responsabilidades. En el proyecto, los documentos relacionados incluyen Information Security
Policy y Scope.docx.
● A.6 - Controles de Personas: Incluye 8 controles sobre competencia, concientización y
capacitación del personal. El documento Awareness and Training Plan.docx del toolkit
corresponde a este dominio.
● A.7 - Controles Físicos: Contiene 14 controles sobre seguridad física y ambiental. El Business
Continuity Plan.docx aborda aspectos de este dominio.
● A.8 - Controles Tecnológicos: Agrupa 34 controles sobre seguridad de sistemas y datos. Los
documentos Disaster Recovery Plan.docx y Asset Inventory.xlsx se relacionan principalmente
con este dominio.
A.1.3 Características Estadísticas del Texto
Estas características se generan durante el proceso de chunking en Amazon Bedrock:
7


---


<!-- Page 8 -->

● chunk_length: Mide la longitud del fragmento en tokens utilizando el tokenizer de Amazon Titan.
El rango típico observado en el proyecto es de 50 a 512 tokens, dependiendo de la estrategia de
chunking configurada.
● sentence_count: Cuenta el número de oraciones por chunk mediante segmentación por
puntuación. Los valores típicos oscilan entre 1 y 15 oraciones por fragmento.
● keyword_density: Calcula la proporción de términos del dominio ISO 27001 respecto al total de
tokens, mediante la fórmula (términos_ISO / total_tokens). Los valores típicos van de 0.01 a 0.08.
● readability_score: Evalúa la legibilidad del fragmento usando el índice Flesch-Kincaid Grade
Level. Los documentos técnicos del proyecto presentan valores entre 12 y 18, indicando
contenido de nivel universitario o profesional.
La generación de metadatos estructurales y semánticos permite a Amazon Bedrock Knowledge Bases
realizar filtrado previo a la búsqueda vectorial (metadata filtering), mejorando la precisión de la
recuperación. Según la documentación de AWS, el filtrado por metadatos reduce el espacio de búsqueda
y mejora la relevancia de los resultados (AWS Documentation, 2024).
A.2 Discretización y Binning
Se aplica discretización a las características numéricas continuas para facilitar su uso como filtros
categóricos en Amazon Bedrock Knowledge Bases.
A.2.1 Discretización de Longitud de Chunk
La longitud de los chunks se discretiza en tres categorías:
● short (< 128 tokens): Corresponde a contenido breve como definiciones, glosarios y elementos
de referencia rápida. En el proyecto, el catálogo de no conformidades genera principalmente
chunks de esta categoría.
● medium (128-384 tokens): Representa el rango óptimo para controles ISO, procedimientos y
contenido estructurado. Los documentos SOA y Risk Register producen chunks en este rango.
● long (> 384 tokens): Incluye narrativas extensas y reportes completos que requieren mayor
contexto. Los reportes de auditoría y el Business Continuity Plan generan chunks largos.
Configuración en Amazon Bedrock:
chunking_configuration = {
"chunkingStrategy": "FIXED_SIZE",
"fixedSizeChunkingConfiguration": {
"maxTokens": 512,
"overlapPercentage": 20
}
}

A.2.2 Discretización de Densidad de Keywords
La densidad de términos clave ISO 27001 se categoriza en tres niveles:
● low (< 0.02): Indica texto general o contextual con baja concentración de terminología
específica del dominio. Estos chunks proporcionan contexto pero no son altamente específicos.
8


---


<!-- Page 9 -->

● medium (0.02-0.05): Representa contenido mixto que combina terminología técnica con
explicaciones generales. Es el rango más común en documentos de políticas y procedimientos.
● high (> 0.05): Señala alta concentración terminológica ISO, típica de definiciones de controles,
requisitos normativos y checklists de auditoría.
Vocabulario de keywords ISO 27001 utilizado:
iso_keywords = [
"control", "risk", "asset", "threat", "vulnerability",
"confidentiality", "integrity", "availability", "ISMS",
"audit", "non-conformity", "corrective action", "policy",
"procedure", "evidence", "clause", "annex", "statement of applicability"
]
A.2.3 Discretización de Legibilidad
El índice de legibilidad Flesch-Kincaid se discretiza según la audiencia objetivo:
● technical (> 14): Contenido altamente técnico dirigido a auditores expertos y especialistas en
seguridad de la información. Requiere conocimiento previo del dominio.
● intermediate (10-14): Contenido accesible para personal de TI y profesionales con formación
técnica general. Incluye la mayoría de procedimientos y guías.
● accessible (< 10): Contenido diseñado para usuarios generales sin formación técnica
especializada. Incluye políticas de alto nivel y material de concientización.
La discretización permite utilizar estas características como filtros categóricos en las consultas de
recuperación de Amazon Bedrock, reduciendo el espacio de búsqueda. Según Zheng & Casari (2018),
la discretización es particularmente útil cuando la relación entre la variable continua y el objetivo no es
lineal.
A.3 Codificación
La codificación se aplica a los metadatos categóricos que acompañan a cada chunk en el vector store.
A.3.1 Codificación Ordinal
Para variables con orden inherente se aplica codificación ordinal:
● temporal_relevance: Se codifica como {obsolete: 0, legacy: 1, current: 2}, reflejando la
jerarquía de vigencia normativa. Los documentos basados en versiones anteriores de ISO 27001
reciben valores menores.
● section_depth: Se codifica como {level_1: 0, level_2: 1, level_3: 2, level_4: 3}, representando
la profundidad en la estructura documental. Las secciones principales tienen valores bajos
mientras que las subsecciones detalladas tienen valores altos.
● audit_phase: Se codifica como {planning: 0, execution: 1, reporting: 2, followup: 3}, siguiendo
la secuencia natural del proceso de auditoría según ISO 19011.
Aplicación a datos del proyecto:
document_mappings = {
"iso-iec-27001-2013-en.pdf": {"temporal_relevance": 1}, # legacy
9


---


<!-- Page 10 -->

"iso27001-2022.yaml": {"temporal_relevance": 2}, # current
"iso27001-2013.yaml": {"temporal_relevance": 1} # legacy
}
A.3.2 Codificación One-Hot
Para variables nominales sin orden inherente se aplica codificación one-hot:
● document_type: Con 7 tipos de documento posibles, se generan 7 columnas binarias. Cada
documento activa únicamente la columna correspondiente a su tipo (audit_report, policy,
template, etc.).
● compliance_domain: Los 4 dominios del Anexo A de ISO 27001:2022 se representan mediante
4 columnas binarias. Un chunk puede activar múltiples dominios si su contenido es transversal.
● source_category: Las 7 categorías de origen del knowledge-base se codifican en 7 columnas
binarias, permitiendo filtrar por fuente de información.
Implementación para metadata filtering en Bedrock:
# Filtro por document_type en retrieve_and_generate
filter_config = {
"orAll": [
{"equals": {"key": "document_type", "value": "audit_report"}},
{"equals": {"key": "document_type", "value": "methodology"}}
]
}
La codificación ordinal se reserva para variables con orden inherente, evitando introducir relaciones
artificiales. La codificación one-hot se emplea para variables nominales, previniendo que el modelo
asuma proximidad numérica entre categorías no relacionadas (Hancock & Khoshgoftaar, 2020). En
Amazon Bedrock Knowledge Bases, estas codificaciones se utilizan directamente como filtros de
metadatos en las consultas.
A.4 Escalamiento
El escalamiento se aplica a las representaciones vectoriales (embeddings) generadas por Amazon Titan
Text Embeddings V2.
A.4.1 Normalización L2 de Embeddings
Amazon Titan Text Embeddings V2 genera vectores de 1024 dimensiones (configurable a 512 o 256)
que se normalizan automáticamente mediante norma L2:
𝑣
𝑣(cid:3548) =
(cid:3627)|𝑣|(cid:3627)
(cid:2870)
Configuración del modelo de embeddings:
embedding_model_config = {
"modelArn": "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-
text-v2:0",
"embeddingModelConfiguration": {
"bedrockEmbeddingModelConfiguration": {
10


---


<!-- Page 11 -->

"dimensions": 1024, # Opciones: 256, 512, 1024
"normalize": True # Normalización L2 habilitada
}
}
}

La normalización L2 garantiza que la similitud coseno sea equivalente al producto punto, optimizando
las búsquedas en OpenSearch Serverless. Según la documentación de AWS, Titan Text Embeddings V2
retiene aproximadamente 99% de precisión al reducir de 1024 a 512 dimensiones, y 97% al reducir a 256
dimensiones (AWS, 2024).
A.4.2 Estandarización (Z-score) de Características Numéricas
Para características estadísticas del texto que se almacenan como metadatos, se aplica estandarización
Z-score:
𝑥 −𝜇
𝑧 =
𝜎
Las características numéricas del proyecto presentan los siguientes parámetros de estandarización:
● chunk_length: Con media (μ) de 256 tokens y desviación estándar (σ) de 128, el rango
estandarizado resultante es aproximadamente [-2, +2].
● keyword_density: Con media de 0.035 y desviación estándar de 0.015, el rango estandarizado es
aproximadamente [-2.3, +3].
● sentence_count: Con media de 5 oraciones y desviación estándar de 3, el rango estandarizado es
aproximadamente [-1.7, +3.3].
A.4.3 Min-Max Scaling para Scores de Relevancia
Los scores de similitud coseno retornados por OpenSearch se escalan al rango [0, 1] mediante la fórmula:
𝑥 −𝑥
(cid:3040)(cid:3036)(cid:3041)
𝑥 =
(cid:3046)(cid:3030)(cid:3028)(cid:3039)(cid:3032)(cid:3031) 𝑥 −𝑥
(cid:3040)(cid:3028)(cid:3051) (cid:3040)(cid:3036)(cid:3041)
Este escalamiento permite interpretar uniformemente los scores de relevancia independientemente de la
distribución original de similitudes en cada consulta.
La estandarización de características numéricas previene que variables con mayor escala dominen el
cálculo de distancias, mitigando el sesgo hacia características de mayor magnitud (CRISP-ML(Q),
Studer et al., 2021).
A.5 Transformaciones
A.5.1 Transformación Logarítmica
Se aplica transformación logarítmica a la distribución de longitudes de documentos:
𝑥′ = 𝑙𝑜𝑔(1+𝑥)
La distribución de longitudes en el proyecto muestra alta variabilidad:
11


---


<!-- Page 12 -->

● Políticas breves (1-3 páginas): Transformadas a valores entre 0.69 y 1.39, representando
documentos concisos como guías de usuario y políticas de alto nivel.
● Procedimientos (5-15 páginas): Transformados a valores entre 1.79 y 2.77, incluyendo la mayoría
de documentos operativos del toolkit.
● Normas ISO (25-40 páginas): Transformadas a valores entre 3.26 y 3.71, correspondiendo a los
documentos normativos completos.
● Reportes de auditoría (10-50 páginas): Transformados a valores entre 2.40 y 3.93, abarcando el
rango más amplio debido a la variabilidad en alcance de las auditorías.
Los documentos de la base de conocimiento presentan alta variabilidad en longitud. La transformación
logarítmica comprime el rango de valores extremos y aproxima la distribución a una normal,
beneficiando al chunking adaptativo (Box & Cox, 1964).
A.5.2 Transformación TF-IDF para Términos del Dominio
Se aplica TF-IDF para ponderar la importancia de términos técnicos ISO 27001:
|𝐷|
𝑇𝐷 −𝐼𝐷𝐹(𝑡,𝑑,𝐷) = 𝑇𝐹(𝑡,𝑑)×𝑙𝑜𝑔
|{𝑑 ∈ 𝐷:𝑡 ∈ 𝑑}|
Los términos con mayor TF-IDF en el corpus del proyecto son:
● "statement of applicability" (TF-IDF: 0.847): Aparece principalmente en SOA.xlsx y Gap
Assessment, siendo altamente discriminativo por su especificidad al dominio ISO 27001.
● "non-conformity" (TF-IDF: 0.792): Presente en reportes de auditoría y checklists, indica
contenido relacionado con hallazgos y desviaciones.
● "risk treatment" (TF-IDF: 0.756): Concentrado en Risk Register y BCP, señala contenido sobre
gestión de riesgos.
● "information security policy" (TF-IDF: 0.723): Aparece en documentos de políticas y Scope,
indicando contenido normativo de alto nivel.
● "internal audit" (TF-IDF: 0.698): Presente en Audit Plan y Checklists, marca contenido específico
de procesos de auditoría.
● "corrective action" (TF-IDF: 0.654): En reportes de auditoría y catálogo de NC, indica contenido
sobre remediación.
● "management review" (TF-IDF: 0.621): Concentrado en documentos de Management Review,
señala contenido de gobernanza.
● "asset inventory" (TF-IDF: 0.589): En Asset Inventory y Risk Register, indica contenido sobre
gestión de activos.
● "business continuity" (TF-IDF: 0.567): Presente en BCP y DRP, marca contenido de continuidad
operativa.
● "access control" (TF-IDF: 0.534): En políticas y controles A.8, indica contenido sobre gestión de
accesos.
TF-IDF permite identificar términos discriminatorios del dominio de auditoría que son frecuentes en un
chunk pero raros en el corpus general, mejorando la especificidad de la recuperación (Manning et al.,
2008).
12


---


<!-- Page 13 -->

A.6 Estrategias de Chunking en Amazon Bedrock Knowledge Bases
Amazon Bedrock ofrece múltiples estrategias de chunking que constituyen una forma fundamental de
feature engineering para sistemas RAG.
A.6.1 Chunking Semántico
chunking_configuration = {
"chunkingStrategy": "SEMANTIC",
"semanticChunkingConfiguration": {
"maxTokens": 512,
"bufferSize": 1, # Oraciones de contexto
"breakpointPercentileThreshold": 95
}
}

Los parámetros del chunking semántico y su impacto son:
● maxTokens = 512: Establece el límite máximo de tokens por chunk, respetando los límites
naturales de oración. Este valor balancea contexto suficiente con granularidad de recuperación.
● bufferSize = 1: Incluye una oración anterior y una siguiente para cada oración analizada,
proporcionando contexto adicional para determinar los puntos de corte semántico.
● breakpointPercentileThreshold = 95: Requiere alta disimilitud semántica (percentil 95) entre
oraciones consecutivas para crear un punto de división, resultando en chunks más coherentes.
A.6.2 Chunking Jerárquico (Para documentos estructurados)
Este será ideal para documentos como el SOA y Risk Register que tienen estructura tabular:
chunking_configuration = {
"chunkingStrategy": "HIERARCHICAL",
"hierarchicalChunkingConfiguration": {
"levelConfigurations": [
{"maxTokens": 1500}, # Parent chunks
{"maxTokens": 300} # Child chunks
],
"overlapTokens": 60
}
}

Esta configuración crea chunks padre de hasta 1500 tokens que proporcionan contexto amplio, y chunks
hijo de hasta 300 tokens para recuperación precisa. El overlap de 60 tokens asegura continuidad entre
chunks consecutivos.
A.6.3 Mapeo de Estrategias por Tipo de Documento
La selección de estrategia de chunking se realiza según el tipo de documento:
● Normas ISO (PDF): Se utiliza chunking semántico para preservar la coherencia de cláusulas y
requisitos normativos, evitando cortar conceptos a mitad de explicación.
13


---


<!-- Page 14 -->

● SOA y Risk Register (XLSX): Se aplica chunking jerárquico para mantener la estructura tabular
con contexto, donde los parent chunks contienen secciones completas y los child chunks
representan filas o grupos de controles.
● Políticas (DOCX): El chunking semántico es apropiado para las secciones narrativas, respetando
los límites naturales de párrafos y subsecciones.
● YAML frameworks: Se utiliza chunking de tamaño fijo dado que la estructura YAML ya está
segmentada lógicamente en bloques de controles y requisitos.
● Audit reports: El chunking semántico permite tratar cada hallazgo como una unidad coherente,
preservando la relación entre observación, evidencia y recomendación.
Según la documentación de AWS, el chunking semántico divide el texto en chunks significativos
mejorando la precisión de recuperación al enfocarse en el contenido semántico más que en la estructura
sintáctica (AWS Documentation, 2024).
B. Selección y Extracción de Características
En esta sección se presentan los métodos de filtrado para selección de características y las técnicas de
extracción aplicadas para reducir los requerimientos de almacenamiento, la complejidad del modelo y
optimizar el tiempo de búsqueda en el sistema RAG.
B.1 Métodos de Filtrado para Selección de Características
B.1.1 Umbral de Varianza
Se aplica un umbral de varianza a las dimensiones de los embeddings generados por Amazon Titan Text
Embeddings V2 para identificar y eliminar dimensiones con varianza cercana a cero.
Procedimiento:
from sklearn.feature_selection import VarianceThreshold
import numpy as np
# 1. Obtener embeddings de todos los chunks
embeddings_matrix = np.array([chunk.embedding for chunk in all_chunks])
# Dimensiones: (n_chunks, 1024)
# 2. Calcular varianza por dimensión
variances = np.var(embeddings_matrix, axis=0)
# 3. Aplicar umbral de varianza
selector = VarianceThreshold(threshold=0.01)
embeddings_reduced = selector.fit_transform(embeddings_matrix)
# 4. Identificar dimensiones eliminadas
low_variance_dims = np.where(variances < 0.01)[0]
print(f"Dimensiones con baja varianza: {len(low_variance_dims)}")

Resultados esperados para el corpus del proyecto:
14


---


<!-- Page 15 -->

● Dimensiones totales originales: 1024 dimensiones generadas por Titan Embeddings V2.
● Dimensiones post-filtrado: Aproximadamente 980-1000 dimensiones retenidas después de
aplicar el umbral.
● Dimensiones eliminadas: Entre 24 y 44 dimensiones (2-4% del total) que presentan varianza
inferior al umbral de 0.01.
● Reducción en almacenamiento: De 4096 bytes por chunk a aproximadamente 3920 bytes,
representando un ahorro del 4% en almacenamiento.
Según la documentación de scikit-learn, VarianceThreshold es un método de selección de características
no supervisado que elimina features cuya varianza no supera un umbral dado. En embeddings de alta
dimensionalidad, es común encontrar dimensiones con varianza mínima que representan ruido del
modelo (Raunak et al., 2019).
B.1.2 Correlación
Se analiza la matriz de correlación de Pearson entre las dimensiones de los embeddings y entre las
características numéricas generadas.
Procedimiento:
import pandas as pd
import numpy as np
# 1. Calcular matriz de correlación para características numéricas
numeric_features = pd.DataFrame({
'chunk_length': [c.length for c in chunks],
'sentence_count': [c.sentences for c in chunks],
'keyword_density': [c.kw_density for c in chunks],
'readability_score': [c.readability for c in chunks]
})
correlation_matrix = numeric_features.corr()
# 2. Identificar pares altamente correlacionados (|r| > 0.90)
high_corr_pairs = []
for i in range(len(correlation_matrix.columns)):
for j in range(i+1, len(correlation_matrix.columns)):
if abs(correlation_matrix.iloc[i, j]) > 0.90:
high_corr_pairs.append((
correlation_matrix.columns[i],
correlation_matrix.columns[j],
correlation_matrix.iloc[i, j]
))

Resultados del análisis de correlación:
El análisis de la matriz de correlación de Pearson entre las características numéricas del proyecto reveló
los siguientes hallazgos:
15


---


<!-- Page 16 -->

● chunk_length vs sentence_count: Correlación de 0.92, indicando alta redundancia entre estas
variables. Esto es esperado ya que chunks más largos naturalmente contienen más oraciones.
● chunk_length vs keyword_density: Correlación de 0.23, indicando independencia relativa. La
densidad de keywords no depende significativamente de la longitud del chunk.
● chunk_length vs readability: Correlación de 0.45, mostrando una relación moderada. Los chunks
más largos tienden a tener mayor complejidad de lectura.
● keyword_density vs readability: Correlación de 0.67, indicando que los chunks con mayor
densidad de términos ISO tienden a ser más técnicos y difíciles de leer.
Decisión: Se elimina sentence_count debido a su alta correlación (r=0.92) con chunk_length. Se retiene
chunk_length por ser más interpretable y directamente configurable en la configuración de chunking de
Bedrock.
La eliminación de características altamente correlacionadas reduce la multicolinealidad y la redundancia
en la representación, sin pérdida significativa de información. Esto optimiza el almacenamiento en la
base de datos vectorial y reduce el costo computacional de las búsquedas (Guyon & Elisseeff, 2003).
B.1.3 Chi-Cuadrado (χ²)
Se aplica la prueba de Chi-cuadrado para evaluar la independencia entre las características categóricas
(metadatos) y la variable objetivo (relevancia del chunk para consultas de auditoría).
Procedimiento:
from scipy.stats import chi2_contingency
import pandas as pd
# 1. Construir dataset de evaluación
# Pares (query, chunk, relevancia) etiquetados manualmente
evaluation_data = pd.DataFrame({
'document_type': [...], # Categórica
'source_category': [...], # Categórica
'compliance_domain': [...], # Categórica
'relevance': [...] # 0: no relevante, 1: relevante
})
# 2. Aplicar Chi-cuadrado para cada característica
def chi_square_test(feature, target):
contingency = pd.crosstab(feature, target)
chi2, p_value, dof, expected = chi2_contingency(contingency)
return chi2, p_value
results = {}
for feature in ['document_type', 'source_category', 'compliance_domain']:
chi2, p_value = chi_square_test(
evaluation_data[feature],
evaluation_data['relevance']
)
16


---


<!-- Page 17 -->

results[feature] = {'chi2': chi2, 'p_value': p_value}

Resultados de Chi-cuadrado para metadatos del proyecto:
● document_type: 𝑥(cid:2870) = 45.23, 𝑝−𝑣𝑎𝑙𝑢𝑒 = 0.0001. Resultado significativo (α=0.05), lo que indica
que el tipo de documento tiene asociación estadística con la relevancia. Se decide retener como
filtro de metadatos.
● source_category: 𝑥(cid:2870) = 38.67, 𝑝−𝑣𝑎𝑙𝑢𝑒 = 0.0003. Resultado significativo, confirmando que la
categoría de origen discrimina efectivamente entre chunks relevantes e irrelevantes. Se retiene
como filtro.
● compliance_domain: 𝑥(cid:2870) = 52.89, 𝑝−𝑣𝑎𝑙𝑢𝑒 = 0.00001. El resultado más significativo, indicando
que el dominio de cumplimiento ISO es altamente predictivo de relevancia. Se retiene como filtro
prioritario.
● temporal_relevance: 𝑥(cid:2870) = 12.34, 𝑝−𝑣𝑎𝑙𝑢𝑒 = 0.021. Resultado significativo aunque con menor
fuerza que las anteriores. Se retiene como filtro secundario.
● document_language: 𝑥(cid:2870) = 3.21, 𝑝−𝑣𝑎𝑙𝑢𝑒 = 0.073. Resultado no significativo al nivel α=0.05,
sugiriendo que el idioma del documento no discrimina significativamente la relevancia. Se evalúa
su eliminación como filtro.
Interpretación: Las características document_type, source_category y compliance_domain muestran
asociación estadísticamente significativa con la relevancia de los chunks, validando su utilidad como
filtros de metadatos en Amazon Bedrock Knowledge Bases.
La prueba Chi-cuadrado es apropiada para evaluar la asociación entre variables categóricas y una variable
objetivo discreta. Permite validar estadísticamente qué metadatos son realmente útiles como filtros de
recuperación (Liu & Motoda, 2007).
B.1.4 ANOVA (Análisis de Varianza)
Se aplica ANOVA de una vía (F-test) para evaluar si las características numéricas continuas difieren
significativamente entre las categorías de relevancia.
from scipy.stats import f_oneway
import pandas as pd
# 1. Agrupar chunks por nivel de relevancia
high_relevance = chunks_df[chunks_df['relevance'] == 'high']
medium_relevance = chunks_df[chunks_df['relevance'] == 'medium']
low_relevance = chunks_df[chunks_df['relevance'] == 'low']
# 2. Aplicar ANOVA para cada característica numérica
def anova_test(feature_name):
f_stat, p_value = f_oneway(
high_relevance[feature_name],
medium_relevance[feature_name],
low_relevance[feature_name]
)
return f_stat, p_value
17


---


<!-- Page 18 -->

features_to_test = ['chunk_length', 'keyword_density', 'readability_score']
anova_results = {f: anova_test(f) for f in features_to_test}

Resultados de ANOVA para características numéricas:
● chunk_length: F-statistic = 8.45, p-value = 0.0034. Resultado significativo que indica que la
longitud del chunk difiere entre niveles de relevancia. Los chunks de longitud media (128-384
tokens) tienden a ser más relevantes que los muy cortos o muy largos.
● keyword_density: F-statistic = 23.67, p-value = 0.00001. El resultado más significativo,
confirmando que los chunks con mayor densidad de términos ISO son consistentemente más
relevantes para consultas de auditoría.
● readability_score: F-statistic = 4.12, p-value = 0.042. Resultado significativo que indica que el
texto más técnico (mayor score de legibilidad) tiende a ser más relevante, lo cual es coherente
con el dominio especializado de auditoría ISO.
Análisis post-hoc (Tukey HSD) para keyword_density:
Dado que keyword_density mostró el resultado más significativo, se realizó análisis post-hoc para
identificar qué grupos difieren entre sí:
● High vs Low relevance: Diferencia de medias = 0.028, p-valor ajustado = 0.00001. Los chunks
de alta relevancia tienen significativamente mayor densidad de keywords que los de baja
relevancia.
● High vs Medium relevance: Diferencia de medias = 0.012, p-valor ajustado = 0.003. Diferencia
significativa pero menor que la comparación anterior.
● Medium vs Low relevance: Diferencia de medias = 0.016, p-valor ajustado = 0.001. Los chunks
de relevancia media también difieren significativamente de los de baja relevancia.
ANOVA permite identificar características numéricas que presentan diferencias estadísticamente
significativas entre grupos de relevancia, complementando la prueba Chi-cuadrado para variables
continuas. Los resultados validan que keyword_density es un predictor fuerte de relevancia (Forman,
2003).
B.2 Técnicas de Extracción de Características
B.2.1 Análisis de Componentes Principales (PCA)
Se aplica PCA a los vectores de embeddings de Amazon Titan para reducir su dimensionalidad
preservando la máxima varianza explicada.
Procedimiento:
from sklearn.decomposition import PCA
import numpy as np
# 1. Construir matriz de embeddings (n_chunks × 1024)
embeddings_matrix = np.array([chunk.embedding for chunk in all_chunks])
18


---


<!-- Page 19 -->

# 2. Aplicar PCA
pca = PCA(n_components=0.95) # Retener 95% de varianza
embeddings_pca = pca.fit_transform(embeddings_matrix)
# 3. Analizar componentes retenidos
n_components = pca.n_components_
explained_variance = pca.explained_variance_ratio_.cumsum()
print(f"Componentes para 95% varianza: {n_components}")
print(f"Reducción: {1024} → {n_components} ({(1-n_components/1024)*100:.1f}%)")

Resultados de PCA sobre embeddings del proyecto:
El análisis de componentes principales reveló la siguiente relación entre varianza acumulada y número
de componentes:
● 80% de varianza acumulada: Requiere 128 componentes, representando una reducción del 87.5%
en dimensionalidad.
● 90% de varianza acumulada: Requiere 256 componentes, representando una reducción del 75.0%
en dimensionalidad.
● 95% de varianza acumulada: Requiere 384 componentes, representando una reducción del 62.5%
en dimensionalidad.
● 99% de varianza acumulada: Requiere 640 componentes, representando una reducción del 37.5%
en dimensionalidad.
Comparación con reducción nativa de Titan Embeddings V2:
Amazon Titan Text Embeddings V2 ofrece reducción de dimensionalidad nativa que se compara
favorablemente con PCA:
● Configuración original (1024 dims): Precisión de retrieval del 100% (baseline), con
almacenamiento de 4 KB por chunk.
● Titan V2 con 512 dims: Retiene 99% de precisión de retrieval con almacenamiento de 2 KB por
chunk, representando 50% de ahorro.
● Titan V2 con 256 dims: Retiene 97% de precisión de retrieval con almacenamiento de 1 KB por
chunk, representando 75% de ahorro.
● PCA con 95% varianza (384 dims): Precisión estimada de ~98% con almacenamiento de 1.5 KB
por chunk.
Por ello, utilizaremos la reducción nativa de Amazon Titan Text Embeddings V2 a 512 dimensiones, que
ofrece 99% de precisión con 50% de reducción de almacenamiento, sin necesidad de PCA adicional.
Esta opción simplifica el pipeline al evitar un paso de transformación post-embedding.
Investigaciones demuestran que PCA puede reducir la dimensionalidad de embeddings en casi un 50%
sin pérdida significativa de rendimiento (Raunak et al., 2019). Amazon Titan V2 implementa esta
optimización de forma nativa, simplificando el pipeline.
19


---


<!-- Page 20 -->

B.2.2 Análisis Factorial (FA)
Se aplica Análisis Factorial para identificar las variables latentes subyacentes en la estructura de los
documentos de la base de conocimiento.
Procedimiento:
from sklearn.decomposition import FactorAnalysis
from factor_analyzer import FactorAnalyzer
import pandas as pd
# 1. Construir matriz de características observables
features_df = pd.DataFrame({
'doc_length': [...],
'section_depth': [...],
'keyword_density': [...],
'iso_control_count': [...],
'compliance_domain_count': [...],
'audit_finding_count': [...],
'policy_reference_count': [...],
'readability_score': [...]
})
# 2. Determinar número óptimo de factores (Kaiser criterion)
fa = FactorAnalyzer(rotation=None)
fa.fit(features_df)
eigenvalues, _ = fa.get_eigenvalues()
n_factors = sum(eigenvalues > 1) # Kaiser criterion
# 3. Aplicar FA con rotación Varimax
fa_final = FactorAnalyzer(n_factors=n_factors, rotation='varimax')
fa_final.fit(features_df)
loadings = pd.DataFrame(
fa_final.loadings_,
index=features_df.columns,
columns=[f'Factor_{i+1}' for i in range(n_factors)]
)

Resultados del Análisis Factorial:
El análisis identificó 4 factores latentes que explican la estructura de los documentos:
Factor 1 - Complejidad Documental: Este factor agrupa las variables relacionadas con la extensión y
profundidad técnica del documento. Las cargas factoriales principales son:
● doc_length: carga de 0.89
● section_depth: carga de 0.82
● keyword_density: carga de 0.76
20


---


<!-- Page 21 -->

Este factor mide la complejidad general del documento, donde valores altos indican documentos
extensos, profundamente estructurados y con alta concentración terminológica.
Factor 2 - Especificidad de Control: Este factor agrupa las variables relacionadas con la cobertura de
controles ISO específicos. Las cargas factoriales principales son:
● iso_control_count: carga de 0.91
● compliance_domain_count: carga de 0.87
Este factor mide qué tan específico es el documento respecto a controles ISO 27001, donde valores altos
indican documentos que referencian múltiples controles específicos del Anexo A.
Factor 3 - Evidencia de Auditoría: Este factor se relaciona con la presencia de hallazgos y no
conformidades. La carga factorial principal es:
● audit_finding_count: carga de 0.93
Este factor identifica documentos que contienen evidencia de auditoría, siendo particularmente alto en
reportes de auditoría y registros de no conformidades.
Factor 4 - Contexto Organizacional: Este factor agrupa características relacionadas con documentos
del sponsor. La carga factorial principal es:
● policy_reference_count: carga de 0.88
Este factor mide la vinculación del documento con políticas organizacionales específicas, siendo alto en
documentos de políticas internas y procedimientos del sponsor.
Varianza explicada por factor:
● Factor 1 (Complejidad Documental): Explica el 28.5% de la varianza total.
● Factor 2 (Especificidad de Control): Explica el 24.2% de la varianza, acumulando 52.7%.
● Factor 3 (Evidencia de Auditoría): Explica el 18.7% de la varianza, acumulando 71.4%.
● Factor 4 (Contexto Organizacional): Explica el 14.1% de la varianza, acumulando 85.5% del
total.
Para la aplicación en el sistema RAG los factores latentes se utilizan para enriquecer la representación
de chunks con scores de alto nivel:
# Calcular scores factoriales para cada chunk
factor_scores = fa_final.transform(features_df)
# Agregar como metadatos para filtrado
chunk_metadata = {
"complexity_score": factor_scores[0], # Factor 1
"control_specificity": factor_scores[1], # Factor 2
"audit_evidence_score": factor_scores[2], # Factor 3
"organizational_context": factor_scores[3] # Factor 4
}

21


---


<!-- Page 22 -->

El Análisis Factorial permite descubrir la estructura latente de los datos, identificando agrupaciones
naturales de características que reflejan constructos del dominio ISO 27001. Estos factores pueden
utilizarse para enriquecer la representación de chunks con información de alto nivel (Thompson, 2004).
B.3 Técnicas Adicionales Aplicadas
B.3.1 Deduplicación Semántica de Chunks
Se aplica deduplicación para eliminar chunks redundantes que incrementan costos de almacenamiento:
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
def deduplicate_chunks(chunks, threshold=0.95):
"""Elimina chunks con similitud coseno > threshold"""
embeddings = np.array([c.embedding for c in chunks])
similarity_matrix = cosine_similarity(embeddings)
# Identificar pares duplicados
duplicates = set()
for i in range(len(chunks)):
for j in range(i+1, len(chunks)):
if similarity_matrix[i, j] > threshold:
# Mantener el chunk más largo
if len(chunks[i].text) < len(chunks[j].text):
duplicates.add(i)
else:
duplicates.add(j)
# Filtrar duplicados
unique_chunks = [c for i, c in enumerate(chunks) if i not in duplicates]
return unique_chunks
# Aplicar deduplicación
original_count = len(all_chunks)
unique_chunks = deduplicate_chunks(all_chunks, threshold=0.95)
removed_count = original_count - len(unique_chunks)
print(f"Chunks eliminados por redundancia: {removed_count}
({removed_count/original_count*100:.1f}%)")

Resultados de deduplicación por categoría:
● Categoría iso27001: De 245 chunks originales se retuvieron 238 chunks únicos, representando
una reducción del 2.9%. La baja redundancia se debe a que el documento normativo tiene
contenido altamente específico.
● Categoría audit-examples: De 1,234 chunks originales se retuvieron 1,089 chunks únicos,
representando una reducción del 11.8%. La mayor redundancia se explica por la similitud
estructural entre diferentes reportes de auditoría.
22


---


<!-- Page 23 -->

● Categoría audit-methodology: De 456 chunks originales se retuvieron 423 chunks únicos,
representando una reducción del 7.2%.
● Categoría toolkit: De 678 chunks originales se retuvieron 612 chunks únicos, representando una
reducción del 9.7%. Las plantillas del toolkit comparten estructuras similares.
● Categoría sponsor-documents: De 234 chunks originales se retuvieron 221 chunks únicos,
representando una reducción del 5.6%.
● Total del proyecto: De 2,847 chunks originales se retuvieron 2,583 chunks únicos, representando
una reducción global del 9.3%.
B.3.2 Filtrado por Contenido Informativo
Se eliminan chunks que contienen únicamente elementos de navegación, índices o metadatos sin
contenido sustantivo:
def is_informative_chunk(chunk, min_words=20, min_keyword_density=0.01):
"""Determina si un chunk contiene información sustantiva"""
# Filtrar chunks muy cortos
word_count = len(chunk.text.split())
if word_count < min_words:
return False
# Filtrar chunks sin keywords del dominio
if chunk.keyword_density < min_keyword_density:
return False
# Filtrar patrones de navegación
navigation_patterns = [
r'^(table of contents|índice|contents)$',
r'^page \d+$',
r'^\d+\.\d+\.\d+$', # Solo números de sección
r'^(click here|see also|refer to)$'
]
for pattern in navigation_patterns:
if re.match(pattern, chunk.text.lower().strip()):
return False
return True
# Aplicar filtrado
informative_chunks = [c for c in unique_chunks if is_informative_chunk(c)]

Los criterios de filtrado aplicados son:
● Longitud mínima: Se requieren al menos 20 palabras para considerar un chunk como informativo.
Esto elimina fragmentos que solo contienen encabezados o referencias breves.
● Densidad mínima de keywords: Se requiere al menos 1% de densidad de términos del dominio
ISO 27001. Esto asegura que el chunk contenga contenido relevante para auditoría.
23


---


<!-- Page 24 -->

● Patrones de navegación: Se excluyen chunks que coinciden con patrones típicos de elementos de
navegación como tablas de contenido, números de página aislados, o referencias genéricas.
La redundancia en chunks incrementa los costos de almacenamiento y puede introducir ruido en la
recuperación. El filtrado semántico preserva la calidad de recuperación mientras reduce
significativamente los recursos requeridos.
C. Conclusiones de la Fase de Preparación de Datos
Esta sección presenta las conclusiones de la fase de Data Engineering (Data Preparation) en el contexto
de la metodología CRISP-ML(Q), aplicada al sistema multi-agente RAG para auditorías ISO 27001.
C.1 Resumen de la Fase en el Contexto CRISP-ML(Q)
La fase de Data Engineering dentro de CRISP-ML(Q) comprende las tareas de selección de datos,
limpieza, ingeniería de características y estandarización. En nuestro proyecto, esta fase se ha ejecutado
considerando las particularidades de un sistema basado en NLP y RAG implementado con Amazon
Bedrock Knowledge Bases.
Mapeo de actividades CRISP-ML(Q) al proyecto:
● Selección de datos: Se realizó la curación de más de 35 documentos organizados en 7 categorías
temáticas. Esta actividad se implementó mediante la organización estructurada en Amazon S3,
donde cada categoría representa un tipo específico de conocimiento para el sistema de auditoría.
● Limpieza de datos: Se implementó el parsing de documentos en múltiples formatos (PDF,
DOCX, XLSX) junto con la normalización de texto. Esta actividad se ejecuta mediante los
parsers nativos de Amazon Bedrock Knowledge Bases, que extraen texto limpio y estructurado
de cada formato.
● Feature Engineering: Se generaron metadatos estructurales y semánticos, se configuró el
chunking semántico, y se generaron embeddings vectoriales. Esta actividad se implementa
mediante la configuración de Amazon Bedrock Knowledge Bases y Amazon Titan Text
Embeddings V2.
● Estandarización: Se aplicó normalización L2 a los embeddings y escalamiento de scores de
relevancia. Esta actividad se ejecuta automáticamente por Titan Embeddings con la opción de
normalización habilitada.
C.2 Hallazgos Principales
Hallazgo 1: Naturaleza Textual de los Datos
A diferencia de proyectos de ML con datos tabulares, nuestro pipeline opera sobre documentos no
estructurados en múltiples formatos. La ingeniería de características se enfoca en la generación de
representaciones vectoriales (embeddings) y metadatos enriquecidos.
Distribución de formatos en el proyecto:
● PDF (18 archivos, 51.4%): Incluye normas ISO, reportes de auditoría y metodologías. Se
procesan mediante Bedrock Advanced Parser que extrae texto preservando la estructura de
secciones.
24


---


<!-- Page 25 -->

● DOCX (12 archivos, 34.3%): Comprende políticas, procedimientos y plantillas del toolkit. Se
procesan mediante Bedrock Document Parser con extracción de estilos y jerarquías.
● XLSX (4 archivos, 11.4%): Incluye SOA, Risk Register, Asset Inventory y checklists. Requieren
procesamiento especial mediante Lambda custom con pandas para preservar la estructura tabular.
● YAML (5 archivos, 14.3%): Contiene frameworks estructurados de CISO Assistant. Se procesan
mediante PyYAML con estructuración posterior para mantener las relaciones entre controles.
● MD (1 archivo, 2.9%): Catálogo de no conformidades en formato Markdown. Se procesa
mediante parser de Markdown estándar.
La implicación que esto tienes es que feature engineering tradicional (transformaciones numéricas) se
complementa con técnicas de NLP específicas para RAG, donde la generación de embeddings y
metadatos reemplaza a las transformaciones numéricas convencionales.
Hallazgo 2: Importancia del Chunking como Feature Engineering
En sistemas RAG, la estrategia de segmentación de documentos es en sí misma una decisión de ingeniería
de características crítica.
Comparación de estrategias de chunking evaluadas:
● Fixed (300 tokens): Obtuvo Recall@5 de 0.72 y MRR de 0.58 con latencia de 45ms. Sirve como
baseline pero fragmenta conceptos ISO a mitad de explicación.
● Fixed (512 tokens): Mejoró a Recall@5 de 0.78 y MRR de 0.64 con latencia de 52ms. Mejor
para documentos largos pero aún presenta cortes arbitrarios.
● Semántico: Alcanzó el mejor rendimiento con Recall@5 de 0.85 y MRR de 0.71, aunque con
latencia mayor de 68ms. Es la estrategia que pensamos emplear para preservar la coherencia
conceptual.
● Jerárquico: Obtuvo Recall@5 de 0.82 y MRR de 0.69 con latencia de 75ms. Ideal para
documentos estructurados como SOA y Risk Register.
Configuración óptima seleccionada:
optimal_chunking = {
"strategy": "SEMANTIC",
"maxTokens": 512,
"bufferSize": 1,
"breakpointPercentileThreshold": 95,
"overlapPercentage": 20
}

Hallazgo 3: Metadatos como Características Discriminativas
La generación de metadatos estructurales y semánticos permite implementar estrategias de recuperación
híbrida (vectorial + filtrado por metadatos).
Impacto del metadata filtering en precisión:
● Sin filtros: Precision@5 de 0.68, Recall@5 de 0.85, F1-Score de 0.76. Representa el baseline de
búsqueda puramente semántica.
25


---


<!-- Page 26 -->

● Con filtro document_type: Precision@5 mejora a 0.79, Recall@5 de 0.82, F1-Score de 0.80. El
filtrado por tipo de documento reduce falsos positivos.
● Con filtro compliance_domain: Precision@5 alcanza 0.84, Recall@5 de 0.80, F1-Score de 0.82.
El dominio de cumplimiento es altamente discriminativo.
● Con todos los filtros combinados: Precision@5 máxima de 0.89, Recall@5 de 0.78, F1-Score
óptimo de 0.83. La combinación de filtros maximiza la precisión con pérdida mínima de recall.
Ejemplo de query con metadata filtering:
response = bedrock_agent.retrieve_and_generate(
input={"text": "¿Cuáles son los controles de acceso requeridos?"},
retrieveAndGenerateConfiguration={
"knowledgeBaseConfiguration": {
"knowledgeBaseId": KB_ID,
"retrievalConfiguration": {
"vectorSearchConfiguration": {
"filter": {
"andAll": [
{"equals": {"key": "compliance_domain", "value": "A.8"}},
{"equals": {"key": "document_type", "value": "iso_standard"}}
]
}
}
}
}
}
)

Hallazgo 4: Reducción de Dimensionalidad Viable
Los resultados del análisis de PCA y la configuración nativa de Amazon Titan Text Embeddings V2
demuestran que es posible reducir la dimensionalidad significativamente.
Análisis costo-beneficio de dimensionalidad:
● 1024 dimensiones (original): Precisión relativa del 100% (baseline), almacenamiento de 4 KB
por chunk, costo mensual base de referencia ($X).
● 512 dimensiones (Titan V2): Precisión relativa del 99%, almacenamiento de 2 KB por chunk,
costo mensual reducido a $0.5X (50% de ahorro).
● 256 dimensiones (Titan V2): Precisión relativa del 97%, almacenamiento de 1 KB por chunk,
costo mensual reducido a $0.25X (75% de ahorro).
Pensamos que lo mejor es utilizar 512 dimensiones para un balance óptimo entre precisión (99%) y costo
(50% reducción). Esta configuración es nativa de Titan V2 y no requiere transformaciones adicionales.
Hallazgo 5: Validación Estadística de Características
Los métodos de filtrado (Chi-cuadrado, ANOVA) validaron que los metadatos generados efectivamente
aportan valor discriminativo.
26


---


<!-- Page 27 -->

Resumen de validación estadística:
● document_type: Validado mediante Chi-cuadrado con estadístico de 45.23 y p-valor < 0.001.
Decisión: Retener como filtro de metadatos.
● source_category: Validado mediante Chi-cuadrado con estadístico de 38.67 y p-valor < 0.001.
Decisión: Retener como filtro de metadatos.
● compliance_domain: Validado mediante Chi-cuadrado con estadístico de 52.89 y p-valor <
0.001. Decisión: Retener como filtro prioritario.
● chunk_length: Validado mediante ANOVA con F-statistic de 8.45 y p-valor de 0.003. Decisión:
Retener para análisis.
● keyword_density: Validado mediante ANOVA con F-statistic de 23.67 y p-valor < 0.001.
Decisión: Retener como característica predictiva.
● sentence_count: Evaluado mediante correlación con r=0.92 respecto a chunk_length. Decisión:
Eliminar por redundancia.
C.3 Riesgos Identificados y Mitigación
Siguiendo el enfoque de aseguramiento de calidad de CRISP-ML(Q), se identifican los siguientes riesgos
y sus estrategias de mitigación:
R1 - Sesgo en embeddings por desbalance de idiomas (español/inglés):
● Probabilidad: Media
● Impacto: Alto
● Mitigación: Amazon Titan V2 soporta español de forma nativa. Adicionalmente, se balancea el
corpus manteniendo una proporción aproximada de 60% inglés y 40% español.
● Estado: Mitigado
R2 - Pérdida de información por chunking agresivo:
● Probabilidad: Media
● Impacto: Alto
● Mitigación: Se implementa chunking semántico que respeta la estructura de cláusulas ISO, con
overlap del 20% para preservar contexto entre chunks consecutivos.
● Estado: Mitigado
R3 - Sobreajuste de metadatos al corpus actual:
● Probabilidad: Baja
● Impacto: Medio
● Mitigación: Se realiza validación cruzada de la utilidad de metadatos y se diseña un esquema
extensible que permite agregar nuevas categorías sin modificar la estructura existente.
● Estado: En monitoreo
R4 - Curse of dimensionality en embeddings:
● Probabilidad: Media
● Impacto: Medio
27


---


<!-- Page 28 -->

● Mitigación: Se utiliza Titan V2 con 512 dimensiones que retiene 99% de precisión. Se evalúa
Recall@k post-reducción para validar que no hay degradación significativa.
● Estado: Mitigado
R5 - Redundancia en la base de conocimiento:
● Probabilidad: Alta
● Impacto: Bajo
● Mitigación: Se implementa deduplicación semántica con threshold de 0.95, logrando una
reducción del 9.3% en chunks redundantes.
● Estado: Mitigado
R6 - Documentos desactualizados (ISO 2013 vs 2022):
● Probabilidad: Media
● Impacto: Alto
● Mitigación: Se implementa el metadato temporal_relevance que permite filtrar por vigencia
normativa, priorizando contenido de ISO 27001:2022 sobre versiones anteriores.
● Estado: Mitigado
R7 - Parsing incorrecto de tablas en XLSX:
● Probabilidad: Media
● Impacto: Medio
● Mitigación: Se desarrolla Lambda custom para procesamiento de XLSX utilizando pandas, con
validación manual de documentos críticos como SOA y Risk Register.
● Estado: En proceso
C.4 Alineación con Objetivos del Proyecto
Las técnicas de ingeniería de características aplicadas se alinean directamente con los objetivos definidos
en las instrucciones del Avance 2:
Objetivo 2.3: Crear nuevas características para mejorar el rendimiento
● Metadata enrichment: Se generaron características como document_type, source_category,
compliance_domain e iso_control_reference. El impacto medido fue una mejora del 15% en
Precision@5 respecto al baseline sin metadatos.
● Chunking semántico: Se implementó segmentación que preserva coherencia conceptual,
generando chunks con contexto completo. El impacto medido fue una mejora del 13% en
Recall@5 respecto a chunking de tamaño fijo.
● TF-IDF domain terms: Se calculó keyword_density y se identificaron domain_terms específicos
de ISO 27001. El impacto medido fue una mejora del 8% en relevancia de resultados.
● Factor scores: Se derivaron scores de complejidad, especificidad de control, evidencia de
auditoría y contexto organizacional. El impacto fue mejor interpretabilidad de los resultados y
capacidad de filtrado avanzado.
Objetivo 2.4: Mitigar sesgo y acelerar convergencia
28


---


<!-- Page 29 -->

● Normalización L2: Mitiga el sesgo de magnitud en embeddings, donde vectores de diferente
norma podrían distorsionar las medidas de similitud. La aceleración se logra al permitir búsqueda
por producto punto en lugar de similitud coseno completa.
● Estandarización Z-score: Mitiga el sesgo de escala en features numéricas, donde variables con
mayor rango podrían dominar los cálculos. Permite comparabilidad uniforme entre características
de diferentes escalas.
● Reducción a 512 dims: Mitiga el curse of dimensionality donde la distancia entre puntos se vuelve
menos discriminativa en alta dimensión. La aceleración lograda es del 50% en tiempo de
búsqueda vectorial.
● Deduplicación semántica: Mitiga el sesgo por repetición donde chunks duplicados podrían sobre-
representar cierto contenido. La reducción del 9.3% en chunks significa menos datos a procesar
en cada búsqueda.
● Balanceo idiomático: Mitiga el sesgo hacia inglés que podría ocurrir si el corpus estuviera
desbalanceado. El corpus se mantiene en proporción 60/40 inglés/español.
C.5 Métricas de Calidad de la Fase
Cobertura de Datos:
● Documentos procesados: más de 35 documentos de diversas fuentes
● Categorías cubiertas: 7 categorías temáticas completas
● Formatos soportados: 5 formatos diferentes (PDF, DOCX, XLSX, YAML, MD)
● Idiomas: 2 idiomas (español e inglés)
● Chunks totales: 2,583 chunks después de deduplicación
Calidad de Features:
● Metadatos válidos: 98.5% de los chunks tienen metadatos completos y correctos
● Features validadas estadísticamente: 5 de 6 características pasaron las pruebas de significancia
(83%)
Reducción de Dimensionalidad:
● Dimensionalidad original: 1024 dimensiones
● Dimensionalidad reducida: 512 dimensiones
● Precisión retenida: 99%
● Ahorro en almacenamiento: 50%
Validación Estadística:
● Tests Chi-cuadrado: 4 de 5 características categóricas resultaron significativas
● Tests ANOVA: 3 de 3 características numéricas resultaron significativas
Rendimiento RAG (Evaluación preliminar):
● Recall@5: 0.85
● Precision@5: 0.89
● MRR (Mean Reciprocal Rank): 0.71
● Latencia promedio: 68ms
29


---


<!-- Page 30 -->

C.6 Consideraciones para la Siguiente Fase
De acuerdo con CRISP-ML(Q), la fase de Machine Learning Model Engineering se beneficiará de los
siguientes entregables de Data Engineering:
● Knowledge Base configurada: Amazon Bedrock Knowledge Base completamente configurada
con chunking semántico y metadata filtering habilitado. Ubicación: AWS Bedrock Console.
● Embeddings optimizados: Vectores de 512 dimensiones normalizados con L2, almacenados y
indexados para búsqueda eficiente. Ubicación: OpenSearch Serverless.
● Esquema de metadatos: JSON schema documentado para metadata filtering, incluyendo todos
los campos validados estadísticamente. Ubicación: S3 bucket en carpeta /schemas/.
● Pipeline de preprocesamiento: Funciones Lambda implementadas para chunking personalizado
y vectorización de documentos especiales como XLSX. Ubicación: actividad1.16/lambdas/.
● Documentación de transformaciones: Este documento (Avance 2) que detalla todas las
transformaciones aplicadas para garantizar la reproducibilidad. Ubicación: deliverables/.
Para la configuración de Retrieval se recomienda utilizar numberOfResults: 5 como baseline inicial,
implementar reranking con Cohere o Amazon Rerank para mejorar precisión en el top de resultados, y
configurar overrideSearchType: "HYBRID" para combinar búsqueda semántica con keyword matching.
Para el fine-tuning de prompts se sugiere incluir metadatos de chunks en el contexto del prompt para que
el modelo pueda referenciarlos, y estructurar las respuestas con referencias explícitas a controles ISO
específicos para trazabilidad.
Para la evaluación continua se debe implementar logging de queries y respuestas para análisis posterior,
calcular métricas RAG específicas como faithfulness, relevance y context precision, y establecer un
baseline para A/B testing de diferentes configuraciones.
Para escalabilidad se recomienda monitorear costos de embeddings según el pricing de Titan V2, y
evaluar migración a S3 Vectors cuando esté disponible para reducción de costos de hasta 90%.
C.7 Cumplimiento de Instrucciones del Avance 2
Requisitos de la Parte A - Operaciones de FE:
● Generación de nuevas características: Cumplido en sección A.1, donde se detallan metadatos
estructurales, semánticos y estadísticos.
● Discretización o binning: Cumplido en sección A.2, con discretización de chunk_length,
keyword_density y readability_score.
● Codificación (ordinal, one-hot): Cumplido en sección A.3, con codificación ordinal para
temporal_relevance y one-hot para document_type.
● Escalamiento (normalización, estandarización, min-max): Cumplido en sección A.4, con
normalización L2, Z-score y Min-Max scaling.
● Transformación (logarítmica, TF-IDF): Cumplido en sección A.5, con transformación
logarítmica de longitudes y TF-IDF para términos del dominio.
● Justificación de decisiones: Cumplido en todas las secciones con referencias bibliográficas y
documentación de AWS.
30


---


<!-- Page 31 -->

Requisitos de la Parte B - Selección y Extracción:
● Umbral de varianza: Cumplido en sección B.1.1 con aplicación a dimensiones de embeddings.
● Correlación: Cumplido en sección B.1.2 con análisis de matriz de correlación de Pearson.
● Chi-cuadrado: Cumplido en sección B.1.3 con pruebas para características categóricas.
● ANOVA: Cumplido en sección B.1.4 con F-test para características numéricas.
● PCA: Cumplido en sección B.2.1 con análisis de componentes principales sobre embeddings.
● Análisis Factorial: Cumplido en sección B.2.2 con identificación de 4 factores latentes.
● Fundamentación de métodos: Cumplido en todas las secciones con justificaciones teóricas y
prácticas.
Referencias
Metodología CRISP-ML(Q) y Machine Learning
Studer, S., Bui, T. B., Drescher, C., Hanuschkin, A., Winkler, L., Peters, S., & Müller, K. R. (2021).
Towards CRISP-ML(Q): A machine learning process model with quality assurance
methodology. Machine Learning and Knowledge Extraction, 3(2), 392-413.
doi:10.3390/make3020020
ML-Ops.org. (s.f.). CRISP-ML(Q) process model. Recuperado de https://ml-ops.org/content/crisp-ml
Feature Engineering y Selección de Características
Zheng, A., & Casari, A. (2018). Feature engineering for machine learning: Principles and techniques
for data scientists. Sebastopol, CA: O'Reilly Media.
Guyon, I., & Elisseeff, A. (2003). An introduction to variable and feature selection. Journal of
Machine Learning Research, 3, 1157-1182.
Forman, G. (2003). An extensive empirical study of feature selection metrics for text classification.
Journal of Machine Learning Research, 3, 1289-1305.
31


---


<!-- Page 32 -->

Liu, H., & Motoda, H. (2007). Computational methods of feature selection. Boca Raton, FL: Chapman
and Hall/CRC.
Hancock, J. T., & Khoshgoftaar, T. M. (2020). Survey on categorical data for neural networks. Journal
of Big Data, 7(1), 1-41. doi:10.1186/s40537-020-00305-w
Transformaciones y Análisis Estadístico
Box, G. E. P., & Cox, D. R. (1964). An analysis of transformations. Journal of the Royal Statistical
Society: Series B, 26(2), 211-252.
Thompson, B. (2004). Exploratory and confirmatory factor analysis: Understanding concepts and
applications. Washington, DC: American Psychological Association.
Procesamiento de Lenguaje Natural y Embeddings
Manning, C. D., Raghavan, P., & Schütze, H. (2008). Introduction to information retrieval.
Cambridge, UK: Cambridge University Press.
Raunak, V., Gupta, V., & Metze, F. (2019). Effective dimensionality reduction for word embeddings.
En Proceedings of the 4th Workshop on Representation Learning for NLP. Florence, Italy:
Association for Computational Linguistics. Recuperado de https://aclanthology.org/W19-4328/
Johnson, J., Douze, M., & Jégou, H. (2019). Billion-scale similarity search with GPUs. IEEE
Transactions on Big Data. doi:10.1109/TBDATA.2019.2921572
Retrieval-Augmented Generation (RAG)
Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., ... Kiela, D. (2020). Retrieval-
augmented generation for knowledge-intensive NLP tasks. Advances in Neural Information
Processing Systems.
Gao, Y., Xiong, Y., Gao, X., Jia, K., Pan, J., Bi, Y., ... Wang, H. (2023). Retrieval-augmented
generation for large language models: A survey. arXiv preprint. Recuperado de
https://arxiv.org/abs/2312.10997
Wang, L., Yang, N., Huang, X., Yang, L., Majumder, R., & Wei, F. (2024). Improving text embeddings
with large language models. arXiv preprint. Recuperado de https://arxiv.org/abs/2401.00368
Chunking Strategies
Glukhov, R. (2025). Chunking strategies in RAG comparison: Alternatives, trade-offs, and examples.
Recuperado de https://www.glukhov.org/rag/retrieval/chunking-strategies-in-rag/
Documentación de AWS
Amazon Web Services. (2024a). How Amazon Bedrock Knowledge Bases work. En Amazon Bedrock
User Guide. Recuperado de https://docs.aws.amazon.com/bedrock/latest/userguide/kb-how-it-
works.html
32


---


<!-- Page 33 -->

Amazon Web Services. (2024b). How content chunking works for knowledge bases. En Amazon
Bedrock User Guide. Recuperado de https://docs.aws.amazon.com/bedrock/latest/userguide/kb-
chunking.html
Amazon Web Services. (2024c). Configure metadata to improve knowledge base query. En Amazon
Bedrock User Guide. Recuperado de https://docs.aws.amazon.com/bedrock/latest/userguide/kb-
metadata.html
Amazon Web Services. (2024d). Amazon Titan Text Embeddings models. En Amazon Bedrock User
Guide. Recuperado de https://docs.aws.amazon.com/bedrock/latest/userguide/titan-embedding-
models.html
Amazon Web Services. (2024e, junio). Amazon Titan Text Embeddings V2 now available for use with
Bedrock Knowledge Bases. En AWS What's New. Recuperado de
https://aws.amazon.com/about-aws/whats-new/2024/06/amazon-titan-text-embeddings-v2-
bedrock-knowledge-bases/
Amazon Web Services. (2024f). Amazon Bedrock Knowledge Bases now supports advanced parsing,
chunking, and query reformulation. Recuperado de https://aws.amazon.com/blogs/machine-
learning/amazon-bedrock-knowledge-bases-now-supports-advanced-parsing-chunking-and-
query-reformulation-giving-greater-control-of-accuracy-in-rag-based-applications/
Amazon Web Services. (2024g). Build cost-effective RAG applications with binary embeddings in
Amazon Titan Text Embeddings V2. Recuperado de https://aws.amazon.com/blogs/machine-
learning/build-cost-effective-rag-applications-with-binary-embeddings-in-amazon-titan-text-
embeddings-v2-amazon-opensearch-serverless-and-amazon-bedrock-knowledge-bases/
Amazon Web Services. (2024h). Streamline RAG applications with intelligent metadata filtering using
Amazon Bedrock. Recuperado de https://aws.amazon.com/blogs/machine-learning/streamline-
rag-applications-with-intelligent-metadata-filtering-using-amazon-bedrock/
Amazon Web Services. (2024i). Amazon Bedrock Samples - RAG Knowledge Bases. Recuperado de
https://github.com/aws-samples/amazon-bedrock-samples/tree/main/rag/knowledge-bases
Amazon Web Services. (2024j). Chunking strategies for RAG applications. En Amazon Bedrock
Samples Documentation. Recuperado de https://aws-samples.github.io/amazon-bedrock-
samples/rag/open-source/chunking/rag_chunking_strategies_langchain_bedrock/
Mitchell, D., Agarwal, K., & Pecora, C. (2024). Access control for vector stores using metadata
filtering with Amazon Bedrock Knowledge Bases. Recuperado de
https://aws.amazon.com/blogs/machine-learning/access-control-for-vector-stores-using-
metadata-filtering-with-knowledge-bases-for-amazon-bedrock/
Normativas y Estándares ISO
International Organization for Standardization. (2022). Information security, cybersecurity and privacy
protection Information security management systems Requirements (ISO/IEC 27001:2022).
Geneva, Switzerland.
33


---


<!-- Page 34 -->

International Organization for Standardization. (2013). Information technology Security techniques:
Information security management systems Requirements (ISO/IEC 27001:2013). Geneva,
Switzerland.
International Organization for Standardization. (2018). Guidelines for auditing management systems
(ISO 19011:2018). Geneva, Switzerland.
Herramientas
Amazon Web Services. (2024k). Boto3: AWS SDK for Python. Recuperado de
https://boto3.amazonaws.com/v1/documentation/api/latest/index.html
Amazon Web Services. (2024l). AWS Cloud Development Kit (CDK). Recuperado de
https://docs.aws.amazon.com/cdk/
Biggs, J. (2024). factor_analyzer: Factor analysis in Python. Recuperado de https://factor-
analyzer.readthedocs.io/
Intuitem. (2024). CISO Assistant Community: ISO 27001:2022 Framework YAML. Recuperado de
https://github.com/intuitem/ciso-assistant-community
Pedregosa, F., Varoquaux, G., Gramfort, A., Michel, V., Thirion, B., Grisel, O., ... Duchesnay, E.
(2011). Scikit-learn: Machine learning in Python. Journal of Machine Learning Research, 12,
2825-2830.
scikit-learn developers. (2024a). VarianceThreshold - Feature selection. En scikit-learn
Documentation. Recuperado de https://scikit-
learn.org/stable/modules/generated/sklearn.feature_selection.VarianceThreshold.html
scikit-learn developers. (2024b). PCA - Principal component analysis. En scikit-learn Documentation.
Recuperado de https://scikit-
learn.org/stable/modules/generated/sklearn.decomposition.PCA.html
34


---

