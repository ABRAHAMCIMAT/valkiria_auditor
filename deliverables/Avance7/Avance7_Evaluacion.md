# Evaluacion del Sistema Multi-Agente ISO 27001

## Objetivo

Este documento describe la metodología de evaluacion implementada en el notebook `Avance7_Evaluacion.ipynb`. La evaluacion se estructura en tres fases progresivas: evaluacion individual de los 11 modelos de lenguaje, evaluacion de cada agente especialista, y evaluacion del flujo completo del sistema multi-agente.

## Fase 1: Evaluacion de Modelos de Lenguaje

### Proposito

Comparar el rendimiento de los 11 modelos disponibles en Amazon Bedrock en tareas representativas de auditoría ISO 27001 para validar los criterios de seleccion (razonamiento, latencia, tool use, costo, español).

### Modelos Evaluados

1. GPT-OSS-120B (OpenAI)
2. GPT-OSS-20B (OpenAI)
3. Qwen3 32B (Alibaba)
4. Claude Sonnet 4.5 (Anthropic)
5. Claude Haiku 4.5 (Anthropic)
6. Llama 4 Maverick 17B (Meta)
7. Llama 4 Scout 17B (Meta)
8. Mistral Large 3 (Mistral)
9. DeepSeek R1 (DeepSeek)
10. Nova Pro (Amazon)
11. Nova Lite (Amazon)

### Metricas Medidas

| Metrica | Tipo | Descripcion |
|---------|------|-------------|
| Latencia (TTFT + total) | Operativa | Tiempo al primer token y tiempo total de generacion |
| Tokens consumidos | Operativa | Tokens de entrada y salida por invocacion |
| Faithfulness | RAG | Proporcion de afirmaciones respaldadas por el contexto recuperado |
| Correctness | Calidad | Nivel de conformidad asignado es correcto dada la evidencia |
| Completeness | Calidad | Todos los campos requeridos estan presentes y completos |
| Following Instructions | Calidad | Adherencia al formato JSON y restricciones del prompt |
| Soporte de español | Linguistico | Calidad de output en español mexicano sin peninsularismos |

### Dataset de Evaluacion

Se utilizan 6 tareas sinteticas que cubren los tipos de operacion del sistema:

1. Evaluacion de control con evidencia suficiente (A.5.1)
2. Evaluacion de control con evidencia parcial (A.8.7)
3. Evaluacion de control con evidencia insuficiente (A.6.3)
4. Analisis de suficiencia de evidencia (A.5.15)
5. Generacion de resumen ejecutivo (consolidacion)
6. Identificacion de problemas sistemicos (razonamiento cruzado)

### Procedimiento

Para cada modelo y cada tarea:
1. Se invoca el modelo via Bedrock con el prompt estandarizado
2. Se registra latencia (TTFT, total), tokens (entrada, salida) y costo estimado
3. Se evalua la calidad de la respuesta mediante LLM-as-a-Judge (Nova Pro como evaluador)
4. Se comparan resultados entre modelos para cada dimension

## Fase 2: Evaluacion de Agentes Especialistas

### Proposito

Evaluar cada uno de los 7 agentes del sistema ISO 27001:2022 de forma aislada, utilizando evidencia sintetica predefinida para medir la calidad de sus evaluaciones de conformidad.

### Agentes Evaluados

1. Planificacion: genera plan de auditoría estructurado
2. Recopilacion de Evidencia: recupera y clasifica evidencia por control
3. Controles Organizacionales (A.5): evalua 37 controles
4. Controles de Personas (A.6): evalua 8 controles
5. Controles Fisicos (A.7): evalua 14 controles
6. Controles Tecnologicos (A.8): evalua 34 controles
7. Consolidacion: verifica consistencia y genera reporte final

### Metricas por Agente

| Metrica | Descripcion |
|---------|-------------|
| Precision de clasificacion de severidad | Concordancia con ground truth en nivel de conformidad |
| Precision del score de madurez CMM | Error absoluto medio respecto a referencia |
| Cobertura de controles evaluados | Porcentaje de controles que el agente evalua respecto al total en alcance |
| Trazabilidad de evidencia | Proporcion de hallazgos que citan fuente documental |
| Calidad de recomendaciones | Especificidad y accionabilidad evaluada por LLM-as-a-Judge |
| Adherencia a formato | Validacion de estructura JSON contra schema Pydantic |

### Datos Sinteticos de Entrada

Se construye un conjunto de evidencia sintetica para una organizacion ficticia (GlobalTech Mexico) con niveles de conformidad predefinidos (ground truth) que permiten medir precision:

| Control | Evidencia Proporcionada | Conformidad Esperada | Madurez Esperada |
|---------|------------------------|---------------------|-----------------|
| A.5.1 | Politica vigente, revisada anualmente | Conforme | 4 |
| A.5.7 | Sin programa de threat intelligence | NC Mayor | 1 |
| A.6.3 | Curso anual 85% completado, sin phishing sim | NC Menor | 2 |
| A.7.7 | Politica documentada, 12 hallazgos de escritorios desbloqueados | NC Menor | 3 |
| A.8.8 | Escaneo semanal, 3 altas pendientes dentro de SLA | Conforme | 3 |
| A.8.25 | SAST en CI/CD, threat modeling, DAST semanal | Conforme | 4 |

## Fase 3: Evaluacion del Flujo Completo

### Proposito

Evaluar el sistema multi-agente como unidad integrada, midiendo la calidad del reporte final consolidado y la eficiencia de la orquestacion.

### Escenarios de Prueba

Se ejecutan tres escenarios con distintas configuraciones:

| Escenario | Organizacion | Tipo Auditoría | Framework | Controles |
|-----------|-------------|----------------|-----------|-----------|
| 1 | GlobalTech Mexico (madurez media-alta) | Certificacion | Strands Agents | Todos (A.5 a A.8) |
| 2 | GlobalTech Mexico (foco tecnologico) | Seguimiento | Strands Agents | Solo A.8 |
| 3 | GlobalTech Mexico (comparacion) | Interna | Los 4 frameworks | Todos |

### Metricas del Flujo

| Metrica | Descripcion |
|---------|-------------|
| Wall time total | Duracion completa del pipeline end-to-end |
| Overhead del framework | Tiempo de coordinacion separado del tiempo de inferencia |
| Consistencia cruzada | Ausencia de contradicciones entre hallazgos de distintos dominios |
| Alineacion maturity/conformity | Coherencia entre score CMM y nivel de conformidad |
| Cobertura total | Proporcion de 93 controles evaluados |
| Costo total por auditoría | Suma de tokens procesados por todos los agentes |
| Reproducibilidad | Varianza entre ejecuciones consecutivas con temperatura 0.0 |
| Calidad del resumen ejecutivo | Coherencia del veredicto con los hallazgos reportados |

### Criterios de Aprobacion

El sistema se considera funcional si cumple:
1. Cobertura de controles mayor o igual a 95%
2. Consistencia cruzada sin contradicciones en hallazgos
3. Wall time inferior a 10 minutos para auditoría completa
4. Costo por auditoría inferior a 15 USD
5. Reproducibilidad con varianza menor a 5% entre ejecuciones

## Infraestructura

| Componente | Servicio |
|-----------|----------|
| Modelos generativos | Amazon Bedrock (11 modelos) |
| Evaluador (LLM-as-a-Judge) | Amazon Nova Pro via Bedrock |
| Base de conocimiento | Bedrock Knowledge Bases con S3 Vectors |
| Almacenamiento de resultados | S3 (bucket del proyecto) |
| Metricas de orquestacion | FlowTracker (backend/observability) |
| Ejecucion del notebook | Ambiente local con credenciales AWS configuradas |

## Dependencias

```
boto3>=1.35.0
pandas>=2.0.0
matplotlib>=3.7.0
seaborn>=0.12.0
tabulate>=0.9.0
pydantic>=2.10.0
```
