"""
Lambda: iso27001-sast-agent-evaluation
Evaluates SAST results using a specialized Bedrock agent backed by the
ISO 27001 Knowledge Base. Maps vulnerabilities to ISO 27001:2022 controls,
generates audit findings, and stores the evaluation report.

This Lambda is invoked as a CodePipeline action after the SAST build stage.
"""
import boto3
import json
import os
import datetime

s3_client = boto3.client('s3')
bedrock_agent = boto3.client('bedrock-agent-runtime')
bedrock_runtime = boto3.client('bedrock-runtime')
codepipeline_client = boto3.client('codepipeline')

RESULTS_BUCKET = os.environ['RESULTS_BUCKET']
RESULTS_PREFIX = os.environ['RESULTS_PREFIX']
EVALUATION_PREFIX = os.environ['EVALUATION_PREFIX']
GENERATION_MODEL_ID = os.environ['GENERATION_MODEL_ID']
KB_ID = os.environ.get('KB_ID', '')


def lambda_handler(event, context):
    """
    CodePipeline Lambda invoke action handler.
    1. Retrieves latest SAST results from S3
    2. Sends findings to Bedrock agent for ISO 27001 evaluation
    3. Stores evaluation report in S3
    4. Reports success/failure back to CodePipeline
    """
    # Extract CodePipeline job ID
    job_id = event['CodePipeline.job']['id']
    user_params = json.loads(
        event['CodePipeline.job']['data']['actionConfiguration']
              ['configuration']['UserParameters']
    )

    print(f"[INFO] CodePipeline job: {job_id}")
    print(f"[INFO] User parameters: {json.dumps(user_params)}")

    try:
        # Step 1: Get the latest SAST report from S3
        sast_report = get_latest_sast_report()
        if not sast_report:
            raise Exception("No SAST report found in results bucket")

        print(f"[INFO] Retrieved SAST report with {count_findings(sast_report)} findings")

        # Step 2: Evaluate findings with Bedrock agent
        evaluation = evaluate_with_agent(sast_report)

        # Step 3: Store evaluation report
        report_key = store_evaluation_report(evaluation, sast_report)
        print(f"[INFO] Evaluation report stored at s3://{RESULTS_BUCKET}/{report_key}")

        # Step 4: Report success to CodePipeline
        codepipeline_client.put_job_success_result(
            jobId=job_id,
            outputVariables={
                'reportKey': report_key,
                'findingsCount': str(count_findings(sast_report)),
                'criticalCount': str(evaluation.get('summary', {}).get('critical', 0)),
                'complianceScore': str(evaluation.get('summary', {}).get('compliance_score', 'N/A')),
            },
        )
        print(f"[INFO] Pipeline job {job_id} completed successfully")

    except Exception as e:
        print(f"[ERROR] Agent evaluation failed: {str(e)}")
        codepipeline_client.put_job_failure_result(
            jobId=job_id,
            failureDetails={
                'type': 'JobFailed',
                'message': f'SAST agent evaluation failed: {str(e)}',
            },
        )


def get_latest_sast_report():
    """Retrieve the most recent SAST consolidated report from S3."""
    response = s3_client.list_objects_v2(
        Bucket=RESULTS_BUCKET,
        Prefix=RESULTS_PREFIX,
    )

    if 'Contents' not in response:
        return None

    # Find the latest consolidated report
    reports = [
        obj for obj in response['Contents']
        if obj['Key'].endswith('sast-consolidated-report.json')
    ]

    if not reports:
        return None

    # Sort by last modified, get most recent
    latest = sorted(reports, key=lambda x: x['LastModified'], reverse=True)[0]
    print(f"[INFO] Loading report: {latest['Key']}")

    obj = s3_client.get_object(Bucket=RESULTS_BUCKET, Key=latest['Key'])
    return json.loads(obj['Body'].read().decode('utf-8'))


def count_findings(report):
    """Count total findings across all scan results."""
    total = 0
    for scan_name, scan_data in report.get('results', {}).items():
        if isinstance(scan_data, dict) and 'results' in scan_data:
            total += len(scan_data['results'])
    return total


def evaluate_with_agent(sast_report):
    """
    Use Bedrock RetrieveAndGenerate to evaluate SAST findings
    against ISO 27001:2022 controls from the Knowledge Base.
    """
    # Prepare a summary of findings for the agent
    findings_summary = prepare_findings_summary(sast_report)

    # Build the evaluation prompt
    prompt = build_evaluation_prompt(findings_summary)

    # If KB is configured, use RetrieveAndGenerate for RAG-based evaluation
    if KB_ID:
        print(f"[INFO] Using Knowledge Base {KB_ID} for RAG evaluation")
        response = bedrock_agent.retrieve_and_generate(
            input={'text': prompt},
            retrieveAndGenerateConfiguration={
                'type': 'KNOWLEDGE_BASE',
                'knowledgeBaseConfiguration': {
                    'knowledgeBaseId': KB_ID,
                    'modelArn': f'arn:aws:bedrock:{os.environ["AWS_REGION"]}::foundation-model/{GENERATION_MODEL_ID}',
                    'retrievalConfiguration': {
                        'vectorSearchConfiguration': {
                            'numberOfResults': 10,
                        },
                    },
                },
            },
        )
        agent_response = response['output']['text']
    else:
        # Fallback: direct model invocation without RAG
        print("[INFO] No KB_ID configured, using direct model invocation")
        response = bedrock_runtime.invoke_model(
            modelId=GENERATION_MODEL_ID,
            contentType='application/json',
            accept='application/json',
            body=json.dumps({
                'messages': [
                    {
                        'role': 'user',
                        'content': [{'text': prompt}],
                    }
                ],
                'inferenceConfig': {
                    'maxTokens': 4096,
                    'temperature': 0.2,
                },
            }),
        )
        result = json.loads(response['body'].read())
        agent_response = result['output']['message']['content'][0]['text']

    # Parse the agent's evaluation into structured format
    evaluation = parse_agent_evaluation(agent_response, findings_summary)
    return evaluation


def prepare_findings_summary(report):
    """Extract and categorize findings from the SAST report."""
    findings = []

    for scan_name, scan_data in report.get('results', {}).items():
        if isinstance(scan_data, dict) and 'results' in scan_data:
            for finding in scan_data['results']:
                findings.append({
                    'scan': scan_name,
                    'rule_id': finding.get('check_id', 'unknown'),
                    'severity': finding.get('extra', {}).get('severity', 'UNKNOWN'),
                    'message': finding.get('extra', {}).get('message', ''),
                    'file': finding.get('path', ''),
                    'line': finding.get('start', {}).get('line', 0),
                    'category': finding.get('extra', {}).get('metadata', {}).get('category', ''),
                    'cwe': finding.get('extra', {}).get('metadata', {}).get('cwe', []),
                })

    # Group by severity
    severity_counts = {}
    for f in findings:
        sev = f['severity']
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    return {
        'total_findings': len(findings),
        'severity_distribution': severity_counts,
        'findings': findings[:50],  # Limit to top 50 for prompt size
        'timestamp': report.get('timestamp', ''),
        'tool': report.get('tool', 'semgrep'),
    }


def build_evaluation_prompt(findings_summary):
    """Build the evaluation prompt for the Bedrock agent."""
    findings_json = json.dumps(findings_summary, indent=2, default=str)

    return f"""Eres un auditor especializado en ISO 27001:2022. Evalúa los siguientes hallazgos 
de un análisis SAST (Static Application Security Testing) y mapéalos a los controles 
de ISO 27001:2022 aplicables.

## Hallazgos SAST:
{findings_json}

## Instrucciones:
1. Para cada hallazgo crítico y alto, identifica el control ISO 27001:2022 aplicable 
   (Anexo A, categorías: Organizacionales, Personas, Físicos, Tecnológicos).
2. Clasifica cada hallazgo como una no-conformidad (mayor/menor) o una observación.
3. Proporciona recomendaciones de remediación alineadas con ISO 27001.
4. Genera un puntaje de cumplimiento general (0-100).
5. Identifica los riesgos más críticos para la seguridad de la información.

## Formato de respuesta (JSON):
{{
  "summary": {{
    "compliance_score": <0-100>,
    "total_findings": <int>,
    "critical": <int>,
    "high": <int>,
    "medium": <int>,
    "low": <int>,
    "non_conformities_major": <int>,
    "non_conformities_minor": <int>,
    "observations": <int>
  }},
  "control_mappings": [
    {{
      "finding_id": "<rule_id>",
      "iso_control": "<A.X.Y>",
      "control_name": "<nombre del control>",
      "classification": "non_conformity_major|non_conformity_minor|observation",
      "risk_level": "critical|high|medium|low",
      "description": "<descripción del hallazgo>",
      "remediation": "<recomendación de remediación>"
    }}
  ],
  "top_risks": [
    {{
      "risk": "<descripción del riesgo>",
      "iso_controls": ["<A.X.Y>"],
      "impact": "<impacto potencial>",
      "recommendation": "<recomendación>"
    }}
  ],
  "audit_conclusion": "<conclusión general de la evaluación>"
}}

Responde ÚNICAMENTE con el JSON válido."""


def parse_agent_evaluation(agent_response, findings_summary):
    """Parse the agent's response into a structured evaluation."""
    try:
        # Try to extract JSON from the response
        # The agent might wrap it in markdown code blocks
        response_text = agent_response.strip()
        if response_text.startswith('```'):
            # Remove markdown code block
            lines = response_text.split('\n')
            response_text = '\n'.join(lines[1:-1])

        evaluation = json.loads(response_text)
        return evaluation

    except json.JSONDecodeError:
        print("[WARN] Could not parse agent response as JSON, creating structured fallback")
        return {
            'summary': {
                'compliance_score': 'N/A',
                'total_findings': findings_summary['total_findings'],
                'critical': findings_summary['severity_distribution'].get('ERROR', 0),
                'high': findings_summary['severity_distribution'].get('WARNING', 0),
                'medium': findings_summary['severity_distribution'].get('INFO', 0),
                'low': 0,
            },
            'raw_evaluation': agent_response,
            'control_mappings': [],
            'top_risks': [],
            'audit_conclusion': 'Evaluation completed but structured parsing failed. See raw_evaluation.',
        }


def store_evaluation_report(evaluation, sast_report):
    """Store the evaluation report in S3."""
    timestamp = datetime.datetime.utcnow().strftime('%Y%m%d-%H%M%S')

    report = {
        'metadata': {
            'timestamp': timestamp,
            'pipeline': 'iso27001-sast-pipeline',
            'stage': 'agent_evaluation',
            'model': GENERATION_MODEL_ID,
            'knowledge_base_id': KB_ID or 'direct-invocation',
        },
        'sast_summary': {
            'tool': sast_report.get('tool', 'semgrep'),
            'scan_timestamp': sast_report.get('timestamp', ''),
            'total_findings': count_findings(sast_report),
        },
        'evaluation': evaluation,
    }

    key = f"{EVALUATION_PREFIX}{timestamp}/iso27001-sast-evaluation.json"

    s3_client.put_object(
        Bucket=RESULTS_BUCKET,
        Key=key,
        Body=json.dumps(report, indent=2, default=str),
        ContentType='application/json',
    )

    return key
