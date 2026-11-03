# Documentación de Implementación — AgentCore Multi-Agent ISO 27001

## 1. Descripción General

Esta implementación define un **sistema multi-agente para auditorías ISO 27001:2022** desplegado sobre **AWS Bedrock AgentCore**. El sistema utiliza el patrón "Agents as Tools" del SDK **Strands Agents**, donde un agente orquestador coordina agentes especializados por dominio de control.

Cada agente se despliega como un runtime independiente en AgentCore, con su propio endpoint HTTP (`/invocations`), configuración de memoria, y conjunto de herramientas (`@tool`). La comunicación entre agentes se realiza mediante invocaciones HTTP a los endpoints de cada sub-agente.

## 2. Arquitectura del Sistema

### 2.1 Patrón de Orquestación

```
Usuario/API Gateway
       │
       ▼
┌──────────────────────────────────────┐
│   Consolidation Agent (Orchestrator) │  ← Punto de entrada principal
│   Puerto: 8080 (prod) / 8080 (dev)  │
└──────┬──────┬──────┬──────┬──────┬──────┬──┘
       │      │      │      │      │      │
       ▼      ▼      ▼      ▼      ▼      ▼
   Planning Evidence  A.5    A.6    A.7    A.8
   :8081    :8082   :8083  :8084  :8085  :8086
```

### 2.2 Flujo de Ejecución de Auditoría

1. **Planificación** → El Planning Agent genera el plan de auditoría (alcance, cronograma, criterios)
2. **Recopilación de Evidencia** → El Evidence Agent consulta la Knowledge Base vía RAG para cada control en alcance
3. **Evaluación por Dominio** → Los agentes A.5, A.6, A.7 y A.8 evalúan sus controles respectivos con base en la evidencia
4. **Verificación de Consistencia** → El Orchestrator verifica que no haya contradicciones entre dominios
5. **Consolidación** → Se genera el reporte final unificado con resumen ejecutivo

### 2.3 Primitivas de AgentCore Utilizadas

| Primitiva | Propósito | Estado |
|-----------|-----------|--------|
| **Runtime** | Despliegue de cada agente como endpoint serverless | Definido en CDK, sin desplegar |
| **Memory (STM)** | Persistencia de conversación dentro de una sesión de auditoría | Definido en CDK, solo en el orquestador |
| **Memory (LTM)** | Conocimiento a largo plazo de hallazgos previos y contexto organizacional | Definido en CDK, aislado por tenant (`actor_id`) |
| **Gateway** | Acceso MCP de solo lectura al Knowledge Base | Definido en CDK, sin desplegar |

## 3. Definición de Agentes

### 3.1 Planning Agent (Planificación)

**Directorio:** `planning_agent/`  
**Modelo:** GPT OSS 120B (temperature=0.2)  
**Función:** Genera planes de auditoría estructurados conforme ISO 19011:2018.

**Herramientas:**
| Herramienta | Origen | Propósito |
|-------------|--------|-----------|
| `query_knowledge_base` | shared/tools/rag | Consultar KB para validar aplicabilidad de controles |
| `retrieve_control_evidence` | shared/tools/rag | Obtener requisitos por control |
| `get_iso27001_controls_list` | local | Listar 93 controles del Anexo A |
| `generate_audit_schedule` | local | Generar cronograma por tamaño de organización |
| `save_report_to_s3` | shared/tools/s3 | Persistir plan en S3 |

### 3.2 Evidence Agent (Recopilación de Evidencia)

**Directorio:** `evidence_agent/`  
**Modelo:** Nova Pro (temperature=0.1)  
**Función:** Recupera y evalúa la suficiencia de evidencia documental.

**Herramientas:**
| Herramienta | Origen | Propósito |
|-------------|--------|-----------|
| `query_knowledge_base` | shared/tools/rag | Consultas RAG generales |
| `retrieve_control_evidence` | shared/tools/rag | Recuperar evidencia por control específico |
| `get_document_content` | shared/tools/s3 | Obtener contenido de documentos en S3 |
| `get_document_metadata` | shared/tools/dynamodb | Metadata de documentos en DynamoDB |
| `collect_evidence_for_controls` | local | Recopilación batch para múltiples controles |
| `assess_evidence_sufficiency` | local | Evaluar si la evidencia es suficiente |
| `save_report_to_s3` | shared/tools/s3 | Persistir reporte de evidencia |

### 3.3 Organizational Controls Agent (A.5)

**Directorio:** `organizational_controls_agent/`  
**Modelo:** Nova Pro (temperature=0.0 — determinístico)  
**Función:** Evalúa 37 controles organizacionales.

**Herramientas:**
| Herramienta | Origen | Propósito |
|-------------|--------|-----------|
| `query_knowledge_base` | shared/tools/rag | Contexto de la KB |
| `retrieve_control_evidence` | shared/tools/rag | Evidencia por control |
| `evaluate_control` | local | Estructura de evaluación por control |
| `get_a5_controls_checklist` | local | Checklist completo con criterios de evaluación |
| `save_audit_finding` | shared/tools/dynamodb | Persistir hallazgos |
| `save_report_to_s3` | shared/tools/s3 | Persistir reporte de dominio |

### 3.4 People Controls Agent (A.6)

**Directorio:** `people_controls_agent/`  
**Modelo:** Nova Pro (temperature=0.0)  
**Función:** Evalúa 8 controles de personas.

**Herramientas:**
| Herramienta | Origen | Propósito |
|-------------|--------|-----------|
| `query_knowledge_base` | shared/tools/rag | Contexto de la KB |
| `retrieve_control_evidence` | shared/tools/rag | Evidencia por control |
| `get_a6_controls_checklist` | local | Checklist A.6 con tipos de evidencia esperados |
| `assess_training_effectiveness` | local | Evaluación de efectividad del programa de awareness (A.6.3) |
| `save_audit_finding` | shared/tools/dynamodb | Persistir hallazgos |
| `save_report_to_s3` | shared/tools/s3 | Persistir reporte de dominio |

### 3.5 Physical Controls Agent (A.7)

**Directorio:** `physical_controls_agent/`  
**Modelo:** Nova Pro (temperature=0.0)  
**Función:** Evalúa 14 controles físicos y ambientales.

**Herramientas:**
| Herramienta | Origen | Propósito |
|-------------|--------|-----------|
| `query_knowledge_base` | shared/tools/rag | Contexto de la KB |
| `retrieve_control_evidence` | shared/tools/rag | Evidencia por control |
| `get_a7_controls_checklist` | local | Checklist A.7 con criterios y tipos de evidencia |
| `assess_physical_site_security` | local | Evaluación de seguridad física del sitio (A.7.1–A.7.6) |
| `evaluate_environmental_controls` | local | Evaluación de controles ambientales (A.7.5, A.7.11) |
| `save_audit_finding` | shared/tools/dynamodb | Persistir hallazgos |
| `save_report_to_s3` | shared/tools/s3 | Persistir reporte de dominio |

### 3.6 Technological Controls Agent (A.8)

**Directorio:** `technological_controls_agent/`  
**Modelo:** Nova Pro (temperature=0.0)  
**Función:** Evalúa 34 controles tecnológicos.

**Herramientas:**
| Herramienta | Origen | Propósito |
|-------------|--------|-----------|
| `query_knowledge_base` | shared/tools/rag | Contexto de la KB |
| `retrieve_control_evidence` | shared/tools/rag | Evidencia por control |
| `get_a8_controls_checklist` | local | Checklist A.8 completo |
| `analyze_sast_findings` | local | Análisis de hallazgos SAST mapeados a controles |
| `evaluate_vulnerability_management` | local | Evaluación de madurez de gestión de vulnerabilidades (A.8.8) |
| `get_document_content` | shared/tools/s3 | Obtener configs y reportes |
| `save_audit_finding` | shared/tools/dynamodb | Persistir hallazgos |
| `save_report_to_s3` | shared/tools/s3 | Persistir reporte de dominio |

### 3.7 Consolidation Agent (Orchestrator)

**Directorio:** `consolidation_agent/`  
**Modelo:** Nova Pro (temperature=0.0, max_tokens=8192)  
**Función:** Coordina todos los sub-agentes y produce el reporte final consolidado.

**Herramientas:**
| Herramienta | Origen | Propósito |
|-------------|--------|-----------|
| `invoke_planning_agent` | local | Invoca al agente de planificación |
| `invoke_evidence_agent` | local | Invoca al agente de evidencia |
| `invoke_organizational_controls_agent` | local | Invoca evaluación A.5 |
| `invoke_people_controls_agent` | local | Invoca evaluación A.6 |
| `invoke_physical_controls_agent` | local | Invoca evaluación A.7 |
| `invoke_technological_controls_agent` | local | Invoca evaluación A.8 |
| `verify_findings_consistency` | local | Verificar consistencia entre hallazgos |
| `generate_executive_summary` | local | Generar resumen ejecutivo con veredicto |
| `query_knowledge_base` | shared/tools/rag | Consultas RAG directas |
| `save_audit_finding` | shared/tools/dynamodb | Persistir hallazgos consolidados |
| `list_audit_findings` | shared/tools/dynamodb | Listar todos los hallazgos de una auditoría |
| `save_report_to_s3` | shared/tools/s3 | Persistir reporte final |

## 4. Módulo Compartido (`shared/`)

### 4.1 Cargador de Modelos (`model_loader.py`)

Centraliza la configuración de modelos Bedrock. Parámetros configurables vía variables de entorno:
- `MODEL_ID`: ID del modelo (default: `us.amazon.nova-pro-v1:0`)
- `MODEL_TEMPERATURE`: Temperatura de muestreo (default: 0.2)
- `MODEL_MAX_TOKENS`: Tokens máximos (default: 4096)
- `MODEL_TOP_P`: Top-P (default: 0.9)

### 4.2 Modelos de Datos (`models.py`)

Define contratos de datos Pydantic para comunicación inter-agente:
- `AuditFinding` — Hallazgo de auditoría con control, severidad, evidencia
- `ControlAssessment` — Resultado de evaluación por control
- `AuditPlan` — Plan de auditoría estructurado
- `EvidencePackage` — Paquete de evidencia por control
- `DomainReport` — Reporte por dominio (A.5, A.6, A.7, A.8)
- `ConsolidatedAuditReport` — Reporte final consolidado

### 4.3 Herramientas Compartidas (`tools/`)

| Módulo | Herramientas | Descripción |
|--------|-------------|-------------|
| `rag_tools.py` | `query_knowledge_base`, `retrieve_control_evidence` | Consultas RAG contra Bedrock Knowledge Bases |
| `dynamodb_tools.py` | `get_document_metadata`, `save_audit_finding`, `list_audit_findings` | CRUD de hallazgos y metadata |
| `s3_tools.py` | `get_document_content`, `save_report_to_s3` | Lectura/escritura de documentos y reportes |

### 4.4 System Prompts (`prompts/`)

Cada agente tiene un system prompt especializado que define:
- Responsabilidades específicas
- Controles ISO 27001:2022 que evalúa
- Criterios de conformidad
- Escala de madurez CMM
- Formato de salida esperado
- Restricciones y reglas de evaluación

## 5. Despliegue

El despliegue es infraestructura como código (`backend/cdk/lib/agentcore-stack.ts`), con los recursos nativos de CloudFormation para AgentCore. No usa `bedrock-agentcore-starter-toolkit`, que AWS ya no soporta.

### 5.1 Pre-requisitos

```bash
aws configure          # Credenciales con permisos para CloudFormation, ECR, Bedrock, S3 y DynamoDB
docker info            # Las imágenes ARM64 se construyen localmente
```

La cuenta necesita acceso habilitado en Bedrock a los modelos asignados y el Knowledge Base `iso27001-compliance-kb` en estado ACTIVE.

### 5.2 Verificación previa

```bash
python backend/agentcore/preflight.py --knowledge-base-id <KB_ID>
```

Comprueba credenciales, acceso a modelos, **invocación de herramientas en cada modelo** y el Knowledge Base. El orquestador usa Claude Sonnet 4.5, que depende de la invocación de herramientas. Para cambiar de modelo usa `-c orchestratorModelId=<id>`.

Claude Sonnet 4.5 está deprecado: su retiro en la API de Claude es el 30 de noviembre de 2026. Bedrock define su propio calendario, así que hay que confirmarlo antes de desplegar.

### 5.3 Despliegue completo

```bash
./backend/deploy.sh
```

Orden de los stacks: Frontend, AgentCore (memoria, 7 runtimes, Gateway), SAST y Backend (API, Lambdas, sitio).

### 5.4 Empaquetado

Todas las imágenes salen de `backend/agentcore/Dockerfile`, seleccionando el agente con `--build-arg AGENT_DIR=<agente>`. El contexto de build es `backend/agentcore/` para que `shared/` entre en cada imagen.

### 5.5 Desarrollo Local

```bash
# Puertos de cada sub-agente, definidos en shared/invocation.py:
# 8081 planning, 8082 evidence, 8083 organizational, 8084 people, 8085 physical, 8086 technological
export LOCAL_DEV=1
```

`backend/tests/integration/test_agentcore_local_flow.py` levanta el flujo completo por HTTP sin AWS, reemplazando solo el LLM.

## 6. Configuración de Gateway

El stack crea un MCP Gateway con autorización `AWS_IAM` y un target Lambda (`gateway_tools/handler.py`) que expone `query_knowledge_base` en modo de solo lectura, para clientes MCP externos.

Los agentes siguen usando sus herramientas en proceso (`shared/tools/`), con los permisos de su rol: no pasan por el Gateway. Moverlos implica agregar un cliente MCP con firma SigV4 a cada agente y solo aporta valor si hay más consumidores de esas herramientas.

## 7. Cobertura de Controles ISO 27001:2022

| Dominio | Controles | Agente Responsable | Tipo de Evaluación |
|---------|-----------|-------------------|-------------------|
| A.5 Organizacionales | 37 | `organizational_controls_agent` | Políticas, roles, proveedores, incidentes |
| A.6 Personas | 8 | `people_controls_agent` | RRHH, awareness, trabajo remoto |
| A.7 Físicos | 14 | `physical_controls_agent` | Perímetros, acceso, monitoreo, ambiental, equipos |
| A.8 Tecnológicos | 34 | `technological_controls_agent` | Acceso, crypto, redes, desarrollo seguro |

**Total evaluable:** 93 controles (A.5 + A.6 + A.7 + A.8) — cobertura completa de Annex A

## 8. Modelo de Datos de Salida

### Hallazgo de Auditoría (AuditFinding)

```json
{
    "finding_id": "NC-001",
    "control_id": "A.5.1",
    "control_name": "Políticas de seguridad de la información",
    "conformity_level": "minor_nonconformity",
    "risk_level": "medium",
    "description": "La política de seguridad no ha sido revisada en los últimos 18 meses...",
    "evidence": ["policy_v2.1.pdf", "management_review_2024.docx"],
    "root_cause": "Falta de proceso formal de revisión periódica",
    "recommendation": "Establecer ciclo de revisión anual con aprobación por dirección",
    "remediation_timeline": "30 días",
    "rag_sources": ["s3://bucket/raw/iso27001_policy.pdf"]
}
```

### Reporte Consolidado (Executive Summary)

```json
{
    "total_controls_assessed": 93,
    "conforming": 58,
    "major_nonconformities": 3,
    "minor_nonconformities": 12,
    "opportunities_for_improvement": 6,
    "conformity_rate_percent": 73.4,
    "average_maturity_score": 3.2,
    "verdict": "CONDITIONAL CERTIFICATION — Major non-conformities must be resolved within 90 days",
    "maturity_assessment": "Defined"
}
```

## 9. Consideraciones de Seguridad

- **Aislamiento de tenant:** Cada invocación incluye `actor_id` y `session_id` para trazabilidad
- **Least privilege:** Cada agente solo tiene las herramientas necesarias para su función
- **Determinismo:** Temperature=0.0 para evaluaciones de auditoría (reproducibilidad)
- **Validación:** Modelos Pydantic para verificar estructura de datos inter-agente
- **Sin secrets en código:** Toda configuración sensible vía variables de entorno
- **Audit trail:** Todos los hallazgos se persisten en DynamoDB con timestamps y actor

## 10. Estado

1. ✅ Estructura de agentes definida
2. ✅ Los 7 agentes construyen imagen e importan con dependencias resolubles
3. ✅ Invocación entre agentes con `InvokeAgentRuntime` (SigV4), incluido A.7
4. ✅ Memoria STM/LTM y Gateway MCP definidos en CDK
5. ✅ API Gateway con Cognito conectada al frontend, con ejecución asíncrona
6. ✅ Prueba de integración local del flujo completo
7. ⬜ Desplegar en una cuenta de AWS (`backend/deploy.sh`)
8. ⬜ Ejecutar la prueba end-to-end sobre el despliegue (`backend/tests/e2e/`)
