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
| **Runtime** | Despliegue de cada agente como endpoint serverless | Configurado (`.bedrock_agentcore.yaml`) |
| **Memory (STM)** | Persistencia de conversación dentro de una sesión de auditoría | Preparado, activar post-despliegue |
| **Memory (LTM)** | Conocimiento a largo plazo de hallazgos previos y contexto organizacional | Disponible vía estrategias semánticas |
| **Gateway** | Enrutamiento MCP para herramientas Lambda (RAG, DynamoDB, S3) | Estructura preparada, requiere creación de recurso |

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

### 5.1 Pre-requisitos

```bash
pip install bedrock-agentcore-starter-toolkit
aws configure  # Credenciales AWS con permisos para Bedrock, S3, DynamoDB
```

### 5.2 Crear Recursos de Memoria (una sola vez)

```bash
agentcore memory create audit_system_memory \
    --description "Memory for ISO 27001 audit multi-agent system" \
    --strategies '[
        {"summaryMemoryStrategy": {"name": "AuditSessionSummary", "namespaces": ["/summaries/{actorId}/{sessionId}"]}},
        {"semanticMemoryStrategy": {"name": "AuditFacts", "namespaces": ["/facts/{actorId}"]}}
    ]' \
    --region us-east-1 \
    --wait
```

### 5.3 Despliegue por Agente

```bash
# Desde cada directorio de agente:
cd backend/agentcore/planning_agent
agentcore configure --entrypoint src/main.py --non-interactive
agentcore launch

# Repetir para cada agente:
cd ../evidence_agent && agentcore configure --entrypoint src/main.py --non-interactive && agentcore launch
cd ../organizational_controls_agent && agentcore configure --entrypoint src/main.py --non-interactive && agentcore launch
cd ../people_controls_agent && agentcore configure --entrypoint src/main.py --non-interactive && agentcore launch
cd ../physical_controls_agent && agentcore configure --entrypoint src/main.py --non-interactive && agentcore launch
cd ../technological_controls_agent && agentcore configure --entrypoint src/main.py --non-interactive && agentcore launch
cd ../consolidation_agent && agentcore configure --entrypoint src/main.py --non-interactive && agentcore launch
```

### 5.4 Desarrollo Local

```bash
# Terminal 1: Planning Agent
cd backend/agentcore/planning_agent && agentcore dev --port 8081

# Terminal 2: Evidence Agent
cd backend/agentcore/evidence_agent && agentcore dev --port 8082

# Terminal 3: Organizational Controls Agent
cd backend/agentcore/organizational_controls_agent && agentcore dev --port 8083

# Terminal 4: People Controls Agent
cd backend/agentcore/people_controls_agent && agentcore dev --port 8084

# Terminal 5: Physical Controls Agent
cd backend/agentcore/physical_controls_agent && agentcore dev --port 8085

# Terminal 6: Technological Controls Agent
cd backend/agentcore/technological_controls_agent && agentcore dev --port 8086

# Terminal 7: Consolidation Agent (Orchestrator)
cd backend/agentcore/consolidation_agent && agentcore dev --port 8080

# Test from another terminal:
agentcore invoke --dev --port 8080 '{
    "prompt": "Realiza una auditoría ISO 27001:2022 completa para la organización ACME Corp, una empresa de tecnología con 200 empleados que maneja datos financieros sensibles.",
    "session_id": "audit_001",
    "actor_id": "auditor_david"
}'
```

## 6. Configuración de Gateway (Opcional — Fase 2)

Para exponer herramientas Lambda como endpoints MCP centralizados:

```bash
# Crear gateway
agentcore gateway create-mcp-gateway \
    --name AuditGateway \
    --region us-east-1 \
    --enable_semantic_search

# Agregar targets Lambda (una por herramienta expuesta)
agentcore gateway create-mcp-gateway-target \
    --gateway-arn <arn> \
    --gateway-url <url> \
    --role-arn <role> \
    --name RAGQueryTarget \
    --target-type lambda \
    --target-payload "$(cat gateway_targets/rag_query.json)"
```

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

## 10. Próximos Pasos

1. ✅ Estructura de agentes definida
2. ✅ Physical Controls Agent (A.7) implementado
3. ⬜ Crear recurso de memoria AgentCore (`agentcore memory create`)
4. ⬜ Desplegar agentes individualmente y validar
5. ⬜ Configurar endpoints de producción en el Orchestrator
6. ⬜ Crear Gateway MCP para herramientas centralizadas
7. ⬜ Activar memoria STM/LTM post-despliegue exitoso
8. ⬜ Integrar con API Gateway del frontend
9. ⬜ Tests de integración end-to-end
