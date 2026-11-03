# Fine-tuning (Fase 2)

Entrena un adaptador QLoRA por agente en SageMaker y solo lo adopta si supera al modelo de la Fase 1 sobre datos que no vio en el entrenamiento.

## Estado

El pipeline está probado en CPU con un modelo diminuto. **No se ha entrenado ningún adaptador real**: faltan datos revisados por personas y credenciales de AWS.

## Por qué no se reutilizó el notebook del Avance 3

1. Etiquetas aleatorias: `generate_control_evaluation_examples` asignaba clasificación, riesgo y control con `random.choice`, sin relación con la evidencia. Entrenar con eso enseña ruido con aspecto de auditoría.
2. Modelo incompatible: Ministral 3 8B es multimodal y con pesos FP8. No carga con `AutoModelForCausalLM` ni con transformers 4.44, y LoRA también habría modificado su torre de visión.
3. Cobertura: no había job para el agente de controles físicos (A.7).

## Flujo

```bash
# 1. Borradores desde reportes reales, en estado pending_review
python draft_examples.py --input ../../knowledge-base/audit-examples/<reporte>.pdf --out data/drafts/<reporte>.jsonl

# 2. Una persona compara cada borrador con su fuente. Los aprobados pasan a
#    data/curated/<agente>.jsonl con review_status=approved y reviewed_by

# 3. Validación y construcción del dataset
python build_dataset.py --out build/datasets

# 4. Subir build/datasets a S3 y entrenar. Sin --execute solo muestra plan y costo
aws s3 sync build/datasets s3://<bucket>/fine-tuning/datasets
python launch_training.py --agent controls_a7 --role-arn <arn> --train-s3 s3://<bucket>/fine-tuning/datasets

# 5. Comparar contra la Fase 1 sobre el conjunto de evaluación
MODEL_ID=us.amazon.nova-pro-v1:0 python evaluate_model.py --out baseline.jsonl
SAGEMAKER_ENDPOINT_NAME=<endpoint> python evaluate_model.py --out adapter.jsonl
python promotion_gate.py --baseline baseline.jsonl --candidate adapter.jsonl
```

## Reglas del dataset

`build_dataset.py` rechaza:
1. Ejemplos sin aprobación humana o sin revisor
2. Controles fuera de los 93 del Anexo A 2022, o de otro dominio
3. Evidencia que aparece en los conjuntos de evaluación (`testsets/`, `gov_eval_set.json`)
4. Agentes con menos de 100 ejemplos de entrenamiento o menos de 10 por etiqueta

El reparto entrenamiento/validación se hace por documento fuente, para que fragmentos de un mismo reporte no queden en ambos lados.

## Criterio de adopción

`promotion_gate.py` exige, sobre los 30 controles de `testsets/iso27001_controls_assessment.json`:
1. Salida válida en al menos 95% de los casos
2. Concordancia al menos 5 puntos porcentuales mayor que la Fase 1
3. Error de madurez no peor que la Fase 1

Ese conjunto es sintético y pequeño, y cubre 30 de 93 controles. Sirve para detectar regresiones, pero conviene ampliarlo antes de tomar una decisión definitiva.

## Costos

1. Entrenamiento: ml.g5.2xlarge a unos 1.5 USD/hora, con tope de 6 horas por job (9 USD). Los 7 agentes cuestan como máximo unos 64 USD. Confirmar el precio vigente.
2. Servir el modelo: **es el costo que cambia el caso de negocio**. Un endpoint de SageMaker con vLLM corriendo todo el mes cuesta unos 1,100 USD por instancia, frente al pago por token de Bedrock de la Fase 1. El análisis de 30 USD por auditoría del Resumen Ejecutivo no lo incluye.

## Pendiente de validar en GPU

Probado en CPU: tokenización real de Ministral 3, exclusión de la torre de visión, ejecución completa de `train_qlora.py` y guardado del adaptador.

Sin probar, porque requiere GPU y los pesos completos: la conversión de FP8 a BF16 seguida de cuantización a 4 bits, el consumo de VRAM en una A10G de 24 GB, y el modelo orquestador. Conviene empezar con un solo job piloto.
