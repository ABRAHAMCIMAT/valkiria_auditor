"""
Lambda: iso27001-sast-upload-url
Generates a presigned URL for the frontend to upload a .zip file
containing application source code for SAST analysis.

The uploaded .zip triggers the CodePipeline automatically via S3 events.
"""
import boto3
import json
import os

s3_client = boto3.client('s3')

BUCKET_NAME = os.environ['BUCKET_NAME']
UPLOAD_KEY = os.environ['UPLOAD_KEY']
URL_EXPIRATION = int(os.environ.get('URL_EXPIRATION_SECONDS', '3600'))


def lambda_handler(event, context):
    """Generate a presigned PUT URL for .zip upload."""
    print(f"[INFO] Generating presigned URL for s3://{BUCKET_NAME}/{UPLOAD_KEY}")

    try:
        # Parse request body for optional metadata
        body = {}
        if event.get('body'):
            body = json.loads(event['body'])

        # Generate presigned URL for PUT operation
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': BUCKET_NAME,
                'Key': UPLOAD_KEY,
                'ContentType': 'application/zip',
                'Metadata': {
                    'uploaded-by': body.get('user', 'frontend'),
                    'project-name': body.get('projectName', 'unknown'),
                },
            },
            ExpiresIn=URL_EXPIRATION,
        )

        print(f"[INFO] Presigned URL generated successfully, expires in {URL_EXPIRATION}s")

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
            },
            'body': json.dumps({
                'uploadUrl': presigned_url,
                'bucket': BUCKET_NAME,
                'key': UPLOAD_KEY,
                'expiresIn': URL_EXPIRATION,
                'contentType': 'application/zip',
                'instructions': 'Use HTTP PUT with Content-Type: application/zip to upload your .zip file',
            }),
        }

    except Exception as e:
        print(f"[ERROR] Failed to generate presigned URL: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
            },
            'body': json.dumps({
                'error': 'Failed to generate upload URL',
                'details': str(e),
            }),
        }
