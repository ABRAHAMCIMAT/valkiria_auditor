# Evaluation Sets

## gov_eval_set.json

Dataset de evaluacion para el Agente de Gobernanza. Contiene 10 casos de prueba, 2 por cada nivel de severidad.

### Metodologia de construccion

1. Se tomaron las 26 clausulas evaluables del agente de gobernanza (Clausulas 4-10) definidas en `config.yaml`.
2. Se seleccionaron 10 clausulas al azar, 2 por nivel de severidad, para garantizar una distribucion balanceada.
3. Se utilizo el prompt del agente de gobernanza (`prompts/governance_agent.txt`) como referencia para definir la estructura esperada de cada caso: contexto recuperado (`retrieved_context`), clausula a evaluar (`clause_to_evaluate`) y severidad esperada (`expected_severity`).
4. Los casos fueron generados con Gemini usando el prompt del agente como guia, produciendo evidencia documental sintetica coherente con el nivel de severidad asignado a cada caso.

### Distribucion de severidad

| Severidad | Clausulas |
|---|---|
| No conformidad mayor | 6.1.3, 9.2 |
| No conformidad menor | 9.3, 5.2 |
| Conforme | 4.2, 6.1.2 |
| No se puede evaluar | 4.4, 7.5.1 |
| Oportunidad de Mejora (OFI) | 5.1, 7.3 |

### Estructura de cada caso

```json
{
  "clause_to_evaluate": "<texto de la clausula con requisitos especificos>",
  "retrieved_context": [{"document": "<nombre>", "content": "<texto extraido>"}],
  "expected_severity": "<nivel de severidad esperado>"
}
```
