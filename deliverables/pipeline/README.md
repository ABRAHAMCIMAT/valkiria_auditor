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

2. **SAST Analysis** (CodeBuild) — Descomprime el código y ejecuta Semgrep con tres conjuntos de reglas:
   - `--config=auto` — Reglas generales de seguridad
   - `--config=p/owasp-top-ten` — OWASP Top 10
   - `--config=p/security-audit` — Auditoría de seguridad avanzada

3. **Agent Evaluation** (Lambda + Bedrock) — Un agente especializado evalúa los hallazgos SAST:
   - Usa `RetrieveAndGenerate` con el Knowledge Base de ISO 27001
   - Mapea vulnerabilidades a controles del Anexo A (ISO 27001:2022)
   - Clasifica hallazgos como no-conformidades (mayores/menores) u observaciones
   - Genera un puntaje de cumplimiento y recomendaciones de remediación
   - Almacena el reporte de evaluación en S3

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
└── README.md
```

## Despliegue

```bash
cd deliverables/pipeline/cdk
npm install
npx cdk bootstrap   # Solo la primera vez
npx cdk deploy
```

## Uso

### 1. Obtener URL de subida

```bash
# Invocar Lambda para obtener presigned URL
aws lambda invoke \
  --function-name iso27001-sast-upload-url \
  --payload '{"body": "{\"projectName\": \"mi-app\", \"user\": \"dev@example.com\"}"}' \
  response.json
```

### 2. Subir archivo .zip

```bash
# Usar la URL presignada para subir el código
curl -X PUT \
  -H "Content-Type: application/zip" \
  --upload-file mi-aplicacion.zip \
  "<presigned-url-from-step-1>"
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
| `RESULTS_PREFIX` | Prefijo para reportes SAST (`sast-reports/`) |
| `EVALUATION_PREFIX` | Prefijo para evaluaciones del agente (`agent-evaluations/`) |
| `GENERATION_MODEL_ID` | Modelo Bedrock para generación (`amazon.nova-pro-v1:0`) |
| `KB_ID` | ID del Knowledge Base de Bedrock (ISO 27001) |

### Prerequisitos

- Knowledge Base de Bedrock creado (stack `actividad1.16`)
- Documentos ISO 27001 ingestados en el Knowledge Base
- Permisos de Bedrock habilitados en la cuenta

## Resultados

### Reporte SAST (CodeBuild output)
```json
{
  "timestamp": "2025-01-15T10:30:00",
  "scan_type": "SAST",
  "tool": "semgrep",
  "results": {
    "semgrep-results": { ... },
    "semgrep-owasp": { ... },
    "semgrep-security": { ... }
  }
}
```

### Evaluación del Agente (ISO 27001 mapping)
```json
{
  "metadata": { "model": "amazon.nova-pro-v1:0", "knowledge_base_id": "..." },
  "evaluation": {
    "summary": {
      "compliance_score": 72,
      "non_conformities_major": 3,
      "non_conformities_minor": 8
    },
    "control_mappings": [
      {
        "finding_id": "python.lang.security.injection.sql-injection",
        "iso_control": "A.8.25",
        "control_name": "Secure development life cycle",
        "classification": "non_conformity_major",
        "remediation": "Implementar consultas parametrizadas..."
      }
    ],
    "audit_conclusion": "..."
  }
}
```
