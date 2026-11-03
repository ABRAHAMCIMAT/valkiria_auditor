"""
Lambda: iso27001-sast-upload-url
Generates a presigned URL for the frontend to upload a .zip file
containing application source code for SAST analysis.

The uploaded .zip triggers the CodePipeline automatically via S3 events.

The caller's identity comes from the Cognito claims. The object metadata links the
upload to its tenant and evaluation so later pipeline stages can report on it.
"""
import boto3
import json
import os
import re
from datetime import datetime, timezone

from botocore.config import Config

s3_client = boto3.client('s3', config=Config(signature_version='s3v4'))
dynamodb = boto3.resource('dynamodb')

BUCKET_NAME = os.environ['BUCKET_NAME']
UPLOAD_KEY = os.environ['UPLOAD_KEY']
AUDITS_TABLE = os.environ['AUDITS_TABLE']
ALLOWED_ORIGIN = os.environ.get('ALLOWED_ORIGIN', '*')
URL_EXPIRATION = int(os.environ.get('URL_EXPIRATION_SECONDS', '3600'))
UNSAFE_METADATA = re.compile(r'[^A-Za-z0-9._ -]')
MAX_METADATA_LENGTH = 128


def json_response(status, body):
    return {
        'statusCode': status,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': ALLOWED_ORIGIN,
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        },
        'body': json.dumps(body),
    }


def get_identity(event):
    """Resolve tenant and user from the authorizer claims."""
    claims = event.get('requestContext', {}).get('authorizer', {}).get('claims') or {}
    subject = claims.get('sub')
    if not subject:
        return None, None
    groups = [g for g in re.split(r'[,\s]+', claims.get('cognito:groups', '').strip('[] ')) if g]
    return (groups[0] if groups else f'user-{subject}'), subject


def metadata_value(value):
    """S3 metadata travels in HTTP headers, so it must stay short and plain ASCII."""
    return UNSAFE_METADATA.sub('_', str(value))[:MAX_METADATA_LENGTH]


def lambda_handler(event, context):
    """Generate a presigned PUT URL for the .zip of an evaluation owned by the caller."""
    try:
        tenant_id, subject = get_identity(event)
        if not subject:
            return json_response(401, {'error': 'No autorizado'})

        try:
            body = json.loads(event.get('body') or '{}')
        except json.JSONDecodeError:
            return json_response(400, {'error': 'El cuerpo de la solicitud no es JSON válido'})

        evaluation_id = str(body.get('evaluationId', ''))
        if not evaluation_id:
            return json_response(400, {'error': 'evaluationId es obligatorio'})

        table = dynamodb.Table(AUDITS_TABLE)
        key = {'tenant_id': tenant_id, 'id': evaluation_id}
        evaluation = table.get_item(Key=key).get('Item')
        if not evaluation or evaluation.get('tipo') != 'evaluacion':
            return json_response(404, {'error': 'No encontrado'})

        print(f"[INFO] Generating presigned URL for s3://{BUCKET_NAME}/{UPLOAD_KEY}")

        metadata = {
            'tenant-id': metadata_value(tenant_id),
            'evaluation-id': metadata_value(evaluation_id),
            'uploaded-by': metadata_value(subject),
            'project-name': metadata_value(evaluation.get('nombre', 'unknown')),
        }
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': BUCKET_NAME,
                'Key': UPLOAD_KEY,
                'ContentType': 'application/zip',
                'Metadata': metadata,
            },
            ExpiresIn=URL_EXPIRATION,
        )

        table.update_item(
            Key=key,
            UpdateExpression='SET estado = :running, actualizacion = :now',
            ExpressionAttributeValues={
                ':running': 'en_progreso',
                ':now': datetime.now(timezone.utc).isoformat(),
            },
        )

        print(f"[INFO] Presigned URL generated successfully, expires in {URL_EXPIRATION}s")

        return json_response(200, {
            'uploadUrl': presigned_url,
            'bucket': BUCKET_NAME,
            'key': UPLOAD_KEY,
            'expiresIn': URL_EXPIRATION,
            'contentType': 'application/zip',
            # SigV4 signs the metadata, so S3 rejects a PUT without these exact headers
            'headers': {
                'Content-Type': 'application/zip',
                **{f'x-amz-meta-{name}': value for name, value in metadata.items()},
            },
            'instructions': 'Use HTTP PUT sending every header in "headers"',
        })

    except Exception as e:
        print(f"[ERROR] Failed to generate presigned URL: {str(e)}")
        return json_response(500, {'error': 'Failed to generate upload URL'})
