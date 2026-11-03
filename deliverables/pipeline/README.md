# Pipeline SAST — ISO 27001 Compliance Evaluation

Pipeline de análisis estático de seguridad (SAST) que se activa cuando la aplicación frontend sube un archivo `.zip` con código fuente a S3. Utiliza AWS CodePipeline para orquestar el proceso completo.

## Arquitectura

```
┌─────────────┐     S3 PutObject      ┌──────────────────┐
│  Frontend   │ ──── (.zip upload) ──→ │  S3 Source Bucket │
│  Application│                        │  uploads/app.zip  │
└─────────────┘                        └────────┬─────────┘
                                                │
                                    S3 Event (versioned)
                                                │
                                                ▼
                                   ┌────────────────────────┐
                                   │   AWS CodePipeline      │
                                   │   iso27001-sast-pipeline│
                                   └────────────┬───────────┘
                                                │
                          ┌─────────────────────┼─────────────────────┐
                          │                     │                     │
                          ▼                     ▼                     ▼
                ┌─────────────────┐  ┌──────────────────┐  ┌─────────────────────┐
                │  Stage: Source  │  │ Stage: SAST      │  │ Stage: Agent        │
                │  S3 .zip input  │  │ CodeBuild:       │  │ Evaluation          │
                │                 │  │ - Unzip          │  │ Lambda:             │
                │                 │  │ - Semgrep scan   │  │ - Bedrock RAG       │
                │                 │  │ - OWASP rules    │  │ - ISO 27001 mapping │
                │                 │  │ - Security audit │  │ - Audit findings    │
                └─────────────────┘  └────────┬─────────┘  └──────────┬──────────┘
                                              │                       │
                                              ▼                       ▼
                                   ┌──────────────────┐    ┌──────────────────────┐
                                   │ S3 Results Bucket│    │ S3 Results Bucket    │
                                   │ sast-reports/    │    │ agent-evaluations/   │
                                   │ (raw findings)   │    │ (ISO 27001 report)   │
                                   └──────────────────┘    └──────────────────────┘
```

## Flujo del Pipeline

1. **Source** — El frontend sube un `.zip` a `s3://iso27001-sast-source-{account}/uploads/application.zip`. El bucket tiene versionamiento habilitado, lo que dispara CodePipeline automáticamente.

2. **SAST Analysis** (CodeBuild): descomprime el código y ejecuta Semgrep una sola vez con dos conjuntos de reglas, para no contar dos veces las que se solapan. Un error del escaneo, o un `.zip` sin código analizable, detiene el pipeline.
   - `p/owasp-top-ten`: OWASP Top 10
   - `p/security-audit`: Auditoría de seguridad avanzada

3. **Agent Evaluation** (Lambda + Bedrock): evalúa los hallazgos de esa misma ejecución.
   - Recupera contexto del Knowledge Base con `Retrieve` y mapea cada regla a un control con `Converse`
   - Valida cada control contra los 93 del Anexo A. Lo que el modelo omite o inventa se mapea con una tabla CWE a control, marcado como `mapping_source: baseline`
   - Calcula el puntaje con una fórmula fija, reproducible y documentada en el reporte
   - Solo envía al modelo metadatos de las reglas: el código y las rutas de archivo no salen del pipeline
   - Una respuesta truncada o no parseable falla la ejecución
   - Actualiza el estado de la evaluación que sigue el frontend, también si falla una etapa anterior

Las subidas concurrentes se ejecutan en cola: cada una fija su propia versión del objeto en S3, y sus metadatos la vinculan con su tenant y evaluación.

## Estructura

```
deliverables/pipeline/
├── cdk/
│   ├── bin/app.ts                    # CDK app entry point
│   ├── lib/sast-pipeline-stack.ts    # Stack principal
│   ├── package.json
│   └── tsconfig.json
├── lambdas/
│   ├── sast_upload/                  # Genera presigned URL para subir .zip
│   │   ├── handler.py
│   │   └── requirements.txt
│   └── agent_evaluation/             # Evalúa SAST con agente Bedrock
│       ├── handler.py
│       └── requirements.txt
├── scripts/consolidate_sast.py       # Valida y consolida la salida de Semgrep
├── tests/                            # pytest deliverables/pipeline/tests
└── README.md
```

## Despliegue

Se despliega con `backend/deploy.sh`, después del stack de AgentCore que crea la tabla `ValkiriaAudits`. Por separado:

```bash
cd deliverables/pipeline/cdk
npm install
npx cdk deploy -c knowledgeBaseId=<KB_ID> -c allowedOrigin=https://<sitio>
```

## Uso

### 1. Obtener URL de subida

La ruta `POST /sast/upload-url` de la API de la plataforma requiere un token de Cognito y una evaluación del mismo tenant:

```bash
curl -X POST "$API/sast/upload-url" -H "Authorization: Bearer $TOKEN" \
  -d '{"evaluationId": "<id>"}'
```

### 2. Subir archivo .zip

La firma cubre los metadatos, así que S3 rechaza la subida si falta alguno de los headers de la respuesta:

```bash
curl -X PUT --upload-file mi-aplicacion.zip \
  -H "Content-Type: application/zip" \
  -H "x-amz-meta-tenant-id: ..." \
  -H "x-amz-meta-evaluation-id: ..." \
  -H "x-amz-meta-uploaded-by: ..." \
  -H "x-amz-meta-project-name: ..." \
  "<uploadUrl>"
```

### 3. Monitorear pipeline

```bash
# Ver estado del pipeline
aws codepipeline get-pipeline-state --name iso27001-sast-pipeline
```

## Configuración

### Variables de entorno (Agent Evaluation Lambda)

| Variable | Descripción |
|----------|-------------|
| `RESULTS_BUCKET` | Bucket S3 para resultados |
| `EVALUATION_PREFIX` | Prefijo para evaluaciones del agente (`agent-evaluations/`) |
| `GENERATION_MODEL_ID` | Modelo Bedrock para generación (`us.anthropic.claude-sonnet-4-5-20250929-v1:0`) |
| `KB_ID` | ID del Knowledge Base de Bedrock (ISO 27001) |
| `SOURCE_BUCKET`, `SOURCE_KEY` | Objeto subido, para leer sus metadatos |
| `AUDITS_TABLE` | Tabla con el estado de las evaluaciones |

### Prerequisitos

- Knowledge Base de Bedrock creado (stack `actividad1.16`)
- Documentos ISO 27001 ingestados en el Knowledge Base
- Permisos de Bedrock habilitados en la cuenta

## Resultados

### Reporte SAST (CodeBuild output)
```json
{
  "timestamp": "2026-11-02T10:30:00+00:00",
  "scan_type": "SAST",
  "tool": "semgrep",
  "files_scanned": 120,
  "scan_errors": 0,
  "results": [ ... ]
}
```

### Evaluación del Agente (ISO 27001 mapping)
```json
{
  "metadata": { "model": "us.anthropic.claude-sonnet-4-5-20250929-v1:0", "knowledge_base_id": "..." },
  "evaluation": {
    "summary": {
      "compliance_score": 72,
      "score_method": "100 - (10 x mayores + 3 x menores + 1 x observaciones), por regla",
      "non_conformities_major": 2,
      "non_conformities_minor": 2,
      "mapped_by_baseline": 0
    },
    "control_mappings": [
      {
        "finding_id": "python.lang.security.injection.sql-injection",
        "iso_control": "A.8.28",
        "control_name": "Secure coding",
        "classification": "non_conformity_major",
        "mapping_source": "model",
        "remediation": "Implementar consultas parametrizadas..."
      }
    ],
    "audit_conclusion": "..."
  }
}
```
