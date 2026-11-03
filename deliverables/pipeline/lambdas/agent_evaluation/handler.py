"""
Lambda: iso27001-sast-agent-evaluation
Evaluates SAST results using a specialized Bedrock agent backed by the
ISO 27001 Knowledge Base. Maps vulnerabilities to ISO 27001:2022 controls,
generates audit findings, and stores the evaluation report.

Invoked two ways:
- As a CodePipeline action after the SAST build stage.
- By EventBridge when a pipeline execution fails, so the evaluation the frontend
  is following does not stay "en_progreso" forever.

Only rule metadata reaches the model. Source code and file paths come from the
audited party, so they stay out of the prompt.
"""
import boto3
import json
import os
import datetime
import re

s3_client = boto3.client('s3')
bedrock_agent = boto3.client('bedrock-agent-runtime')
bedrock_runtime = boto3.client('bedrock-runtime')
codepipeline_client = boto3.client('codepipeline')
dynamodb = boto3.resource('dynamodb')

RESULTS_BUCKET = os.environ['RESULTS_BUCKET']
EVALUATION_PREFIX = os.environ['EVALUATION_PREFIX']
GENERATION_MODEL_ID = os.environ['GENERATION_MODEL_ID']
SOURCE_BUCKET = os.environ['SOURCE_BUCKET']
SOURCE_KEY = os.environ['SOURCE_KEY']
AUDITS_TABLE = os.environ['AUDITS_TABLE']
KB_ID = os.environ.get('KB_ID', '')

RULES_PER_BATCH = 25
KB_QUERIES = 5
KB_RESULTS_PER_QUERY = 3
KB_CONTEXT_LIMIT = 6000
MAX_TOKENS = 4096

ANNEX_A_2022 = {
    f'A.{domain}.{number}'
    for domain, controls in {5: 37, 6: 8, 7: 14, 8: 34}.items()
    for number in range(1, controls + 1)
}
CLASSIFICATIONS = {'non_conformity_major', 'non_conformity_minor', 'observation'}
SEVERITY_ORDER = {'ERROR': 0, 'WARNING': 1, 'INFO': 2}
SEVERITY_LABEL = {'ERROR': 'high', 'WARNING': 'medium', 'INFO': 'low'}
BASELINE_CLASSIFICATION = {
    'ERROR': 'non_conformity_major',
    'WARNING': 'non_conformity_minor',
    'INFO': 'observation',
}
SCORE_PENALTY = {'non_conformity_major': 10, 'non_conformity_minor': 3, 'observation': 1}

# Fallback for rules the model leaves out or maps to a control that does not exist
DEFAULT_CONTROL = 'A.8.28'
CWE_CONTROLS = {
    **dict.fromkeys(['CWE-259', 'CWE-321', 'CWE-798'], 'A.5.17'),
    **dict.fromkeys(['CWE-326', 'CWE-327', 'CWE-328', 'CWE-916'], 'A.8.24'),
    **dict.fromkeys(['CWE-287', 'CWE-306', 'CWE-384'], 'A.8.5'),
    **dict.fromkeys(['CWE-284', 'CWE-285', 'CWE-862', 'CWE-863'], 'A.8.3'),
    **dict.fromkeys(['CWE-209', 'CWE-532'], 'A.8.15'),
    **dict.fromkeys(['CWE-319', 'CWE-614'], 'A.8.20'),
    **dict.fromkeys(['CWE-1104', 'CWE-937'], 'A.8.8'),
}
CWE_PATTERN = re.compile(r'CWE-\d+')


def lambda_handler(event, context):
    if 'CodePipeline.job' in event:
        return handle_pipeline_job(event)
    return handle_pipeline_failure(event)


def handle_pipeline_job(event):
    """
    CodePipeline Lambda invoke action handler.
    1. Loads the SAST report produced by this pipeline execution
    2. Sends findings to Bedrock for ISO 27001 evaluation
    3. Stores evaluation report in S3
    4. Reports success/failure back to CodePipeline
    """
    job_id = event['CodePipeline.job']['id']
    user_params = json.loads(
        event['CodePipeline.job']['data']['actionConfiguration']
              ['configuration']['UserParameters']
    )

    print(f"[INFO] CodePipeline job: {job_id}")
    print(f"[INFO] User parameters: {json.dumps(user_params)}")

    owner = {}
    try:
        owner = get_upload_owner(user_params['sourceVersionId'])

        # Addressed explicitly: "latest report" would mix up concurrent uploads
        sast_report = load_sast_report(user_params['reportKey'])
        print(f"[INFO] Retrieved SAST report with {len(sast_report['results'])} findings")

        evaluation = evaluate_with_agent(sast_report)

        report_key = store_evaluation_report(evaluation, sast_report, owner)
        print(f"[INFO] Evaluation report stored at s3://{RESULTS_BUCKET}/{report_key}")

        update_evaluation(owner, 'completada', report_key=report_key,
                          resultado=evaluation['summary']['compliance_score'])

        codepipeline_client.put_job_success_result(
            jobId=job_id,
            outputVariables={
                'reportKey': report_key,
                'findingsCount': str(evaluation['summary']['total_findings']),
                'criticalCount': str(evaluation['summary']['high']),
                'complianceScore': str(evaluation['summary']['compliance_score']),
            },
        )
        print(f"[INFO] Pipeline job {job_id} completed successfully")

    except Exception as e:
        print(f"[ERROR] Agent evaluation failed: {str(e)}")
        update_evaluation(owner, 'error', error='La evaluación del agente falló')
        codepipeline_client.put_job_failure_result(
            jobId=job_id,
            failureDetails={
                'type': 'JobFailed',
                'message': f'SAST agent evaluation failed: {str(e)}'[:5000],
            },
        )


def handle_pipeline_failure(event):
    """Mark the evaluation as failed when an earlier stage stopped the pipeline."""
    detail = event['detail']
    execution = codepipeline_client.get_pipeline_execution(
        pipelineName=detail['pipeline'],
        pipelineExecutionId=detail['execution-id'],
    )['pipelineExecution']

    revisions = execution.get('artifactRevisions', [])
    if not revisions:
        print(f"[WARN] Execution {detail['execution-id']} has no source revision")
        return
    owner = get_upload_owner(revisions[0]['revisionId'])
    print(f"[INFO] Pipeline execution failed for evaluation {owner.get('evaluation_id')}")
    update_evaluation(owner, 'error', error='El análisis SAST falló')


def get_upload_owner(version_id):
    """Read which tenant and evaluation an uploaded version belongs to."""
    metadata = s3_client.head_object(
        Bucket=SOURCE_BUCKET, Key=SOURCE_KEY, VersionId=version_id
    ).get('Metadata', {})
    return {
        'tenant_id': metadata.get('tenant-id', ''),
        'evaluation_id': metadata.get('evaluation-id', ''),
    }


def update_evaluation(owner, estado, **fields):
    """Update the record the frontend follows, if the upload is linked to one."""
    if not owner.get('tenant_id') or not owner.get('evaluation_id'):
        print(f"[WARN] Upload without evaluation; status {estado} not recorded")
        return

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    values = {'estado': estado, 'actualizacion': now, **fields}
    if estado == 'completada':
        values['completada'] = now

    dynamodb.Table(AUDITS_TABLE).update_item(
        Key={'tenant_id': owner['tenant_id'], 'id': owner['evaluation_id']},
        UpdateExpression='SET ' + ', '.join(f'#f{i} = :v{i}' for i in range(len(values))),
        ExpressionAttributeNames={f'#f{i}': name for i, name in enumerate(values)},
        ExpressionAttributeValues={f':v{i}': value for i, value in enumerate(values.values())},
    )


def load_sast_report(report_key):
    obj = s3_client.get_object(Bucket=RESULTS_BUCKET, Key=report_key)
    report = json.loads(obj['Body'].read().decode('utf-8'))
    if 'results' not in report:
        raise ValueError(f'Invalid SAST report: {report_key}')
    return report


def group_findings_by_rule(report):
    """Collapse findings into one entry per rule, most severe first."""
    rules = {}
    for finding in report['results']:
        extra = finding.get('extra', {})
        metadata = extra.get('metadata', {})
        rule_id = finding.get('check_id', 'unknown')
        rule = rules.setdefault(rule_id, {
            'rule_id': rule_id,
            'severity': extra.get('severity', 'INFO'),
            'message': extra.get('message', ''),
            'category': metadata.get('category', ''),
            'cwe': normalize_cwe(metadata.get('cwe', [])),
            'occurrences': [],
        })
        rule['occurrences'].append({
            'file': finding.get('path', ''),
            'line': finding.get('start', {}).get('line', 0),
        })
    return sorted(rules.values(), key=lambda r: SEVERITY_ORDER.get(r['severity'], 3))


def normalize_cwe(cwe):
    """Semgrep reports CWE as a string or list like 'CWE-89: SQL Injection'."""
    values = cwe if isinstance(cwe, list) else [cwe]
    return sorted({match for value in values for match in CWE_PATTERN.findall(str(value))})


def baseline_control(rule):
    for cwe in rule['cwe']:
        if cwe in CWE_CONTROLS:
            return CWE_CONTROLS[cwe]
    return DEFAULT_CONTROL


def retrieve_context(rules):
    """Retrieve ISO 27001 passages for the most severe distinct weaknesses."""
    if not KB_ID:
        print("[INFO] No KB_ID configured, evaluating without RAG context")
        return ''

    queries = []
    for rule in rules:
        query = f"ISO 27001:2022 control aplicable a: {rule['message'][:200]}"
        if query not in queries:
            queries.append(query)
    passages = []
    for query in queries[:KB_QUERIES]:
        response = bedrock_agent.retrieve(
            knowledgeBaseId=KB_ID,
            retrievalQuery={'text': query},
            retrievalConfiguration={
                'vectorSearchConfiguration': {'numberOfResults': KB_RESULTS_PER_QUERY},
            },
        )
        passages.extend(r['content'].get('text', '') for r in response.get('retrievalResults', []))
    return '\n---\n'.join(dict.fromkeys(passages))[:KB_CONTEXT_LIMIT]


def evaluate_with_agent(sast_report):
    """Map every rule to a control and build the deterministic summary."""
    rules = group_findings_by_rule(sast_report)

    mappings = {}
    conclusion = (
        'El análisis SAST no reportó hallazgos. Esto cubre únicamente las reglas ejecutadas '
        'sobre el código entregado y no demuestra conformidad con los controles.'
    )
    if rules:
        context = retrieve_context(rules)
        for start in range(0, len(rules), RULES_PER_BATCH):
            batch = rules[start:start + RULES_PER_BATCH]
            answer = invoke_model(build_evaluation_prompt(batch, context))
            mappings.update(parse_agent_evaluation(answer))
        conclusion = None

    control_mappings = [build_mapping(rule, mappings.get(rule['rule_id'])) for rule in rules]
    summary = build_summary(sast_report, rules, control_mappings)
    if conclusion is None:
        conclusion = (
            f"{summary['total_findings']} hallazgos SAST en {len(rules)} reglas: "
            f"{summary['non_conformities_major']} no conformidades mayores, "
            f"{summary['non_conformities_minor']} menores y {summary['observations']} observaciones."
        )
    return {
        'summary': summary,
        'control_mappings': control_mappings,
        'audit_conclusion': conclusion,
    }


def invoke_model(prompt):
    response = bedrock_runtime.converse(
        modelId=GENERATION_MODEL_ID,
        messages=[{'role': 'user', 'content': [{'text': prompt}]}],
        inferenceConfig={'maxTokens': MAX_TOKENS, 'temperature': 0.0},
    )
    if response.get('stopReason') == 'max_tokens':
        raise ValueError('Model response was truncated')
    return response['output']['message']['content'][0]['text']


def build_evaluation_prompt(rules, context):
    """Build the evaluation prompt for the Bedrock agent."""
    rules_for_model = [
        {
            'rule_id': rule['rule_id'],
            'severity': rule['severity'],
            'message': rule['message'],
            'category': rule['category'],
            'cwe': rule['cwe'],
            'occurrences': len(rule['occurrences']),
        }
        for rule in rules
    ]
    context_section = f"\n## Extractos de la norma:\n{context}\n" if context else ''

    return f"""Eres un auditor especializado en ISO 27001:2022. Mapea cada regla SAST al control
del Anexo A de ISO 27001:2022 más aplicable.
{context_section}
## Reglas SAST:
{json.dumps(rules_for_model, indent=2, ensure_ascii=False)}

## Instrucciones:
1. Devuelve exactamente una entrada por cada rule_id.
2. iso_control debe ser un control real del Anexo A 2022 (A.5.1 a A.5.37, A.6.1 a A.6.8, A.7.1 a A.7.14, A.8.1 a A.8.34).
3. Clasifica cada regla como non_conformity_major, non_conformity_minor u observation.
4. Da una recomendación de remediación concreta y breve, en español.

## Formato de respuesta (JSON):
{{"mappings": [{{"rule_id": "<rule_id>", "iso_control": "<A.X.Y>", "control_name": "<nombre>",
"classification": "<clasificación>", "remediation": "<recomendación>"}}]}}

Responde ÚNICAMENTE con el JSON válido."""


def parse_agent_evaluation(agent_response):
    """Parse the model answer into mappings by rule. Unparseable output is a failure."""
    response_text = agent_response.strip()
    if response_text.startswith('```'):
        response_text = '\n'.join(response_text.split('\n')[1:-1])

    parsed = json.loads(response_text)
    return {
        entry['rule_id']: entry
        for entry in parsed['mappings']
        if isinstance(entry, dict) and entry.get('rule_id')
    }


def build_mapping(rule, answer):
    """Combine rule and model answer, falling back when the answer is not usable."""
    answer = answer or {}
    control = answer.get('iso_control')
    classification = answer.get('classification')
    from_model = control in ANNEX_A_2022 and classification in CLASSIFICATIONS

    return {
        'finding_id': rule['rule_id'],
        'iso_control': control if from_model else baseline_control(rule),
        'control_name': answer.get('control_name', '') if from_model else '',
        'classification': classification if from_model else BASELINE_CLASSIFICATION.get(rule['severity'], 'observation'),
        'risk_level': SEVERITY_LABEL.get(rule['severity'], 'low'),
        'description': rule['message'],
        'remediation': answer.get('remediation', '') if from_model else '',
        'mapping_source': 'model' if from_model else 'baseline',
        'cwe': rule['cwe'],
        'occurrences': rule['occurrences'],
    }


def build_summary(report, rules, mappings):
    """Count findings and score them with a fixed formula, so results are reproducible."""
    classifications = [m['classification'] for m in mappings]
    severities = [rule['severity'] for rule in rules for _ in rule['occurrences']]
    penalty = sum(SCORE_PENALTY[c] for c in classifications)
    return {
        'compliance_score': max(0, 100 - penalty),
        'score_method': '100 - (10 x mayores + 3 x menores + 1 x observaciones), por regla',
        'total_findings': len(report['results']),
        'rules_triggered': len(rules),
        'files_scanned': report.get('files_scanned', 0),
        'scan_errors': report.get('scan_errors', 0),
        'high': severities.count('ERROR'),
        'medium': severities.count('WARNING'),
        'low': severities.count('INFO'),
        'non_conformities_major': classifications.count('non_conformity_major'),
        'non_conformities_minor': classifications.count('non_conformity_minor'),
        'observations': classifications.count('observation'),
        'mapped_by_baseline': sum(1 for m in mappings if m['mapping_source'] == 'baseline'),
    }


def store_evaluation_report(evaluation, sast_report, owner):
    """Store the evaluation report in S3."""
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S')

    report = {
        'metadata': {
            'timestamp': timestamp,
            'pipeline': 'iso27001-sast-pipeline',
            'stage': 'agent_evaluation',
            'model': GENERATION_MODEL_ID,
            'knowledge_base_id': KB_ID or 'direct-invocation',
            'evaluation_id': owner.get('evaluation_id', ''),
        },
        'sast_summary': {
            'tool': sast_report.get('tool', 'semgrep'),
            'scan_timestamp': sast_report.get('timestamp', ''),
            'total_findings': len(sast_report['results']),
        },
        'evaluation': evaluation,
    }

    scope = f"{owner.get('tenant_id') or 'unlinked'}/{owner.get('evaluation_id') or 'unlinked'}"
    key = f"{EVALUATION_PREFIX}{scope}/{timestamp}/iso27001-sast-evaluation.json"

    s3_client.put_object(
        Bucket=RESULTS_BUCKET,
        Key=key,
        Body=json.dumps(report, indent=2, default=str),
        ContentType='application/json',
    )

    return key
