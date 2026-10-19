# ISO 27001:2022 — Data Ingestion Pipeline

Pipeline de carga de datos para la plataforma de evaluación de cumplimiento ISO 27001:2022.
Implementado como un stack CDK con Step Functions, Lambda, API Gateway, S3, Bedrock y OpenSearch Serverless.

## Arquitectura

Ver `docs/arquitectura-ingesta.md` para el diagrama completo.

## Estructura del proyecto

```
code/
├── cdk/                          # CDK stack (TypeScript)
│   ├── bin/
│   │   └── app.ts
│   ├── lib/
│   │   └── ingestion-stack.ts
│   ├── package.json
│   └── tsconfig.json
├── lambdas/
│   ├── presigned_url/            # Genera URL prefirmada para upload a S3
│   │   ├── handler.py
│   │   └── requirements.txt
│   ├── eda_analysis/             # Parte 1: EDA sobre dataset ISO 27001
│   │   ├── handler.py
│   │   └── requirements.txt
│   ├── chunking/                 # Parte 2: Chunking semántico con Bedrock
│   │   ├── handler.py
│   │   └── requirements.txt
│   └── vectordb/                 # Parte 3: Embeddings + indexación OpenSearch
│       ├── handler.py
│       └── requirements.txt
└── statemachine/
    └── ingestion_pipeline.json   # Definición ASL de Step Functions
```

## Despliegue

```bash
cd code/cdk
npm install
npx cdk bootstrap
npx cdk deploy
```

## Flujo de ejecución

1. Cliente solicita URL prefirmada vía API Gateway → Lambda `presigned_url`
2. Cliente sube archivo directamente a S3 con la URL prefirmada
3. S3 Event Notification dispara Step Functions
4. Step Functions ejecuta en secuencia:
   - Estado 1: `eda_analysis` — estadísticas del dataset
   - Estado 2: `chunking` — chunking semántico con Claude
   - Estado 3: `vectordb` — embeddings + indexación OpenSearch Serverless
