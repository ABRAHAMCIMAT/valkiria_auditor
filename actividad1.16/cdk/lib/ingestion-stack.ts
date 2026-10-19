import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as sfn from 'aws-cdk-lib/aws-stepfunctions';
import * as tasks from 'aws-cdk-lib/aws-stepfunctions-tasks';
import * as s3n from 'aws-cdk-lib/aws-s3-notifications';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as opensearchserverless from 'aws-cdk-lib/aws-opensearchserverless';
import * as path from 'path';

export class IngestionStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // ─────────────────────────────────────────────
    // 1. S3 BUCKET
    // ─────────────────────────────────────────────
    const dataBucket = new s3.Bucket(this, 'Iso27001DataBucket', {
      bucketName: `iso27001-compliance-rag-${this.account}`,
      versioned: true,
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
      lifecycleRules: [
        {
          id: 'expire-temp-uploads',
          prefix: 'uploads/',
          expiration: cdk.Duration.days(1),
        },
      ],
      cors: [
        {
          allowedMethods: [s3.HttpMethods.PUT],
          allowedOrigins: ['*'],
          allowedHeaders: ['*'],
          maxAge: 3600,
        },
      ],
    });

    // ─────────────────────────────────────────────
    // 2. OPENSEARCH SERVERLESS COLLECTION
    // ─────────────────────────────────────────────

    // Encryption policy (required before collection creation)
    const encryptionPolicy = new opensearchserverless.CfnSecurityPolicy(
      this, 'OssEncryptionPolicy', {
        name: 'iso27001-encryption-policy',
        type: 'encryption',
        policy: JSON.stringify({
          Rules: [{ ResourceType: 'collection', Resource: ['collection/iso27001-rag'] }],
          AWSOwnedKey: true,
        }),
      }
    );

    // Network policy (allow public access to the collection endpoint)
    const networkPolicy = new opensearchserverless.CfnSecurityPolicy(
      this, 'OssNetworkPolicy', {
        name: 'iso27001-network-policy',
        type: 'network',
        policy: JSON.stringify([{
          Rules: [
            { ResourceType: 'collection', Resource: ['collection/iso27001-rag'] },
            { ResourceType: 'dashboard',  Resource: ['collection/iso27001-rag'] },
          ],
          AllowFromPublic: true,
        }]),
      }
    );

    // OpenSearch Serverless collection (VECTORSEARCH type)
    const ossCollection = new opensearchserverless.CfnCollection(
      this, 'OssCollection', {
        name: 'iso27001-rag',
        type: 'VECTORSEARCH',
        description: 'Vector store for ISO 27001:2022 compliance knowledge base',
      }
    );
    ossCollection.addDependency(encryptionPolicy);
    ossCollection.addDependency(networkPolicy);

    // ─────────────────────────────────────────────
    // 3. IAM ROLE FOR BEDROCK KNOWLEDGE BASE
    // Bedrock assumes this role to access S3 and OpenSearch Serverless
    // ─────────────────────────────────────────────
    const kbRole = new iam.Role(this, 'BedrockKbRole', {
      roleName: 'iso27001-bedrock-kb-role',
      assumedBy: new iam.ServicePrincipal('bedrock.amazonaws.com', {
        conditions: {
          StringEquals: { 'aws:SourceAccount': this.account },
          ArnLike: { 'aws:SourceArn': `arn:aws:bedrock:${this.region}:${this.account}:knowledge-base/*` },
        },
      }),
      inlinePolicies: {
        S3ReadAccess: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              actions: ['s3:GetObject', 's3:ListBucket'],
              resources: [dataBucket.bucketArn, `${dataBucket.bucketArn}/*`],
            }),
          ],
        }),
        BedrockModelAccess: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              actions: ['bedrock:InvokeModel'],
              resources: [
                `arn:aws:bedrock:${this.region}::foundation-model/amazon.titan-embed-text-v2:0`,
                `arn:aws:bedrock:${this.region}::foundation-model/amazon.nova-pro-v1:0`,
              ],
            }),
          ],
        }),
        OpenSearchAccess: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              actions: ['aoss:APIAccessAll'],
              resources: [ossCollection.attrArn],
            }),
          ],
        }),
      },
    });

    // Data access policy: grants kbRole and lambdaRole access to the OSS collection
    const dataAccessPolicy = new opensearchserverless.CfnAccessPolicy(
      this, 'OssDataAccessPolicy', {
        name: 'iso27001-data-access-policy',
        type: 'data',
        policy: JSON.stringify([{
          Rules: [
            {
              ResourceType: 'index',
              Resource: ['index/iso27001-rag/*'],
              Permission: [
                'aoss:CreateIndex', 'aoss:DeleteIndex', 'aoss:UpdateIndex',
                'aoss:DescribeIndex', 'aoss:ReadDocument', 'aoss:WriteDocument',
              ],
            },
            {
              ResourceType: 'collection',
              Resource: ['collection/iso27001-rag'],
              Permission: ['aoss:CreateCollectionItems', 'aoss:DescribeCollectionItems'],
            },
          ],
          Principal: [kbRole.roleArn, `arn:aws:iam::${this.account}:root`],
        }]),
      }
    );
    dataAccessPolicy.addDependency(ossCollection);

    // ─────────────────────────────────────────────
    // 4. SHARED LAMBDA EXECUTION ROLE
    // ─────────────────────────────────────────────
    const lambdaRole = new iam.Role(this, 'LambdaExecutionRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'),
      ],
      inlinePolicies: {
        S3Access: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              actions: ['s3:GetObject', 's3:PutObject', 's3:ListBucket', 's3:DeleteObject'],
              resources: [dataBucket.bucketArn, `${dataBucket.bucketArn}/*`],
            }),
          ],
        }),
        BedrockAccess: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              // Invoke models + manage Knowledge Bases + run ingestion jobs
              actions: [
                'bedrock:InvokeModel',
                'bedrock:RetrieveAndGenerate',
                'bedrock:Retrieve',
              ],
              resources: ['*'],
            }),
            new iam.PolicyStatement({
              // Bedrock Agent (Knowledge Base management) API
              actions: [
                'bedrock:CreateKnowledgeBase',
                'bedrock:GetKnowledgeBase',
                'bedrock:ListKnowledgeBases',
                'bedrock:CreateDataSource',
                'bedrock:GetDataSource',
                'bedrock:ListDataSources',
                'bedrock:StartIngestionJob',
                'bedrock:GetIngestionJob',
                'bedrock:ListIngestionJobs',
              ],
              resources: ['*'],
            }),
          ],
        }),
        OpenSearchAccess: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              actions: ['aoss:APIAccessAll'],
              resources: [ossCollection.attrArn],
            }),
          ],
        }),
        PassKbRole: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              actions: ['iam:PassRole'],
              resources: [kbRole.roleArn],
            }),
          ],
        }),
      },
    });

    // ─────────────────────────────────────────────
    // 5. LAMBDA — PRESIGNED URL
    // ─────────────────────────────────────────────
    const presignedUrlLambda = new lambda.Function(this, 'PresignedUrlLambda', {
      functionName: 'iso27001-presigned-url',
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'handler.lambda_handler',
      code: lambda.Code.fromAsset(
        path.join(__dirname, '../../lambdas/presigned_url')
      ),
      role: lambdaRole,
      timeout: cdk.Duration.seconds(30),
      memorySize: 256,
      environment: {
        BUCKET_NAME: dataBucket.bucketName,
        UPLOAD_PREFIX: 'raw/',
        URL_EXPIRATION_SECONDS: '3600',
      },
      logRetention: logs.RetentionDays.ONE_WEEK,
    });

    // ─────────────────────────────────────────────
    // 6. LAMBDA — EDA ANALYSIS (Step 1)
    // ─────────────────────────────────────────────
    const edaLambda = new lambda.Function(this, 'EdaAnalysisLambda', {
      functionName: 'iso27001-eda-analysis',
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'handler.lambda_handler',
      code: lambda.Code.fromAsset(
        path.join(__dirname, '../../lambdas/eda_analysis')
      ),
      role: lambdaRole,
      timeout: cdk.Duration.minutes(5),
      memorySize: 1024,
      environment: {
        BUCKET_NAME: dataBucket.bucketName,
        RAW_PREFIX: 'raw/',
        RESULTS_PREFIX: 'eda_results/',
      },
      logRetention: logs.RetentionDays.ONE_WEEK,
    });

    // ─────────────────────────────────────────────
    // 7. LAMBDA — KB INGESTION / CHUNKING (Step 2)
    // Uses Bedrock Knowledge Bases API:
    //   - Parsing:  BEDROCK_FOUNDATION_MODEL (amazon.nova-pro-v1:0)
    //   - Chunking: SEMANTIC (NLP-based sentence grouping)
    //   - Embedding: amazon.titan-embed-text-v2:0 (1024 dims)
    // ─────────────────────────────────────────────
    const chunkingLambda = new lambda.Function(this, 'ChunkingLambda', {
      functionName: 'iso27001-kb-ingestion',
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'handler.lambda_handler',
      code: lambda.Code.fromAsset(
        path.join(__dirname, '../../lambdas/chunking')
      ),
      role: lambdaRole,
      timeout: cdk.Duration.minutes(15),
      memorySize: 512,
      environment: {
        BUCKET_NAME:                dataBucket.bucketName,
        RAW_PREFIX:                 'raw/',
        KB_NAME:                    'iso27001-compliance-kb',
        KB_DESCRIPTION:             'ISO 27001:2022 compliance evaluation knowledge base',
        KB_ROLE_ARN:                kbRole.roleArn,
        OPENSEARCH_COLLECTION_ARN:  ossCollection.attrArn,
        OPENSEARCH_INDEX:           'iso27001-controls-index',
        // Parsing: Nova Pro vision model — extracts tables, figures, images from PDFs
        PARSING_MODEL_ID:           'amazon.nova-pro-v1:0',
        // Chunking: SEMANTIC groups sentences by NLP similarity
        // Alternative: HIERARCHICAL for parent/child chunk retrieval
        CHUNKING_STRATEGY:          'SEMANTIC',
        SEMANTIC_BUFFER_SIZE:       '1',
        SEMANTIC_BREAKPOINT_PERCENTILE: '95',
        // Embedding: Titan Text Embeddings V2, 1024 dims, float32
        EMBEDDING_MODEL_ID:         'amazon.titan-embed-text-v2:0',
        EMBEDDING_DIMENSIONS:       '1024',
        MAX_WAIT_SECONDS:           '720',
        POLL_INTERVAL_SECONDS:      '15',
      },
      logRetention: logs.RetentionDays.ONE_WEEK,
    });

    // ─────────────────────────────────────────────
    // 8. LAMBDA — RAG VALIDATION (Step 3)
    // Runs test queries against the KB using RetrieveAndGenerate
    //   - Generation: amazon.nova-pro-v1:0
    //   - Retrieval:  SEMANTIC search, top-5 chunks
    // ─────────────────────────────────────────────
    const vectorDbLambda = new lambda.Function(this, 'VectorDbLambda', {
      functionName: 'iso27001-rag-validation',
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'handler.lambda_handler',
      code: lambda.Code.fromAsset(
        path.join(__dirname, '../../lambdas/vectordb')
      ),
      role: lambdaRole,
      timeout: cdk.Duration.minutes(5),
      memorySize: 512,
      environment: {
        BUCKET_NAME:          dataBucket.bucketName,
        VALIDATION_PREFIX:    'validation/',
        // Generation model for RetrieveAndGenerate
        // Nova Pro: latest Amazon Nova, strong reasoning, available in us-east-1
        GENERATION_MODEL_ID:  'amazon.nova-pro-v1:0',
        // Must match the embedding model used during KB creation
        EMBEDDING_MODEL_ID:   'amazon.titan-embed-text-v2:0',
        NUMBER_OF_RESULTS:    '5',
      },
      logRetention: logs.RetentionDays.ONE_WEEK,
    });

    // ─────────────────────────────────────────────
    // 9. STEP FUNCTIONS STATE MACHINE
    // ─────────────────────────────────────────────

    // Step 1: EDA Analysis
    const edaTask = new tasks.LambdaInvoke(this, 'RunEdaAnalysis', {
      lambdaFunction: edaLambda,
      comment: 'Step 1: EDA — estadísticas descriptivas del dataset ISO 27001',
      outputPath: '$.Payload',
      retryOnServiceExceptions: true,
    });

    // Step 2: KB Ingestion (parsing + chunking + embedding via Bedrock Knowledge Bases)
    const chunkingTask = new tasks.LambdaInvoke(this, 'RunKbIngestion', {
      lambdaFunction: chunkingLambda,
      comment: 'Step 2: Bedrock KB ingestion — Nova Pro parsing + SEMANTIC chunking + Titan embeddings',
      outputPath: '$.Payload',
      retryOnServiceExceptions: true,
    });

    // Step 3: RAG Validation (RetrieveAndGenerate with Nova Pro)
    const vectorDbTask = new tasks.LambdaInvoke(this, 'RunRagValidation', {
      lambdaFunction: vectorDbLambda,
      comment: 'Step 3: RAG validation — RetrieveAndGenerate with Nova Pro',
      outputPath: '$.Payload',
      retryOnServiceExceptions: true,
    });

    // Success state
    const successState = new sfn.Succeed(this, 'PipelineComplete', {
      comment: 'Pipeline de ingesta completado exitosamente',
    });

    // Failure state
    const failureState = new sfn.Fail(this, 'PipelineFailed', {
      comment: 'Pipeline de ingesta falló',
      error: 'IngestionError',
    });

    // Error handling for each step
    const handleEdaError = new sfn.Pass(this, 'HandleEdaError', {
      parameters: { 'error.$': '$.Error', 'step': 'eda_analysis' },
    }).next(failureState);

    const handleChunkingError = new sfn.Pass(this, 'HandleChunkingError', {
      parameters: { 'error.$': '$.Error', 'step': 'chunking' },
    }).next(failureState);

    const handleVectorDbError = new sfn.Pass(this, 'HandleVectorDbError', {
      parameters: { 'error.$': '$.Error', 'step': 'vectordb' },
    }).next(failureState);

    edaTask.addCatch(handleEdaError, { errors: ['States.ALL'] });
    chunkingTask.addCatch(handleChunkingError, { errors: ['States.ALL'] });
    vectorDbTask.addCatch(handleVectorDbError, { errors: ['States.ALL'] });

    // Chain: EDA → Chunking → VectorDB → Success
    const definition = edaTask
      .next(chunkingTask)
      .next(vectorDbTask)
      .next(successState);

    const stateMachineLogGroup = new logs.LogGroup(this, 'StateMachineLogGroup', {
      logGroupName: '/aws/states/iso27001-ingestion-pipeline',
      retention: logs.RetentionDays.ONE_WEEK,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    const stateMachine = new sfn.StateMachine(this, 'IngestionStateMachine', {
      stateMachineName: 'iso27001-ingestion-pipeline',
      definitionBody: sfn.DefinitionBody.fromChainable(definition),
      timeout: cdk.Duration.minutes(45),
      tracingEnabled: true,
      logs: {
        destination: stateMachineLogGroup,
        level: sfn.LogLevel.ALL,
        includeExecutionData: true,
      },
    });

    // ─────────────────────────────────────────────
    // 8. S3 EVENT → STEP FUNCTIONS TRIGGER LAMBDA
    // ─────────────────────────────────────────────
    const triggerRole = new iam.Role(this, 'TriggerLambdaRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'),
      ],
      inlinePolicies: {
        StartExecution: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              actions: ['states:StartExecution'],
              resources: [stateMachine.stateMachineArn],
            }),
          ],
        }),
      },
    });

    const triggerLambda = new lambda.Function(this, 'S3TriggerLambda', {
      functionName: 'iso27001-pipeline-trigger',
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'index.handler',
      code: lambda.Code.fromInline(`
import boto3, os, json

sfn = boto3.client('stepfunctions')

def handler(event, context):
    for record in event.get('Records', []):
        bucket = record['s3']['bucket']['name']
        key    = record['s3']['object']['key']
        # Only trigger for raw/ prefix uploads
        if not key.startswith('raw/'):
            continue
        input_payload = json.dumps({
            'bucket': bucket,
            'key': key,
            'file_name': key.split('/')[-1]
        })
        sfn.start_execution(
            stateMachineArn=os.environ['STATE_MACHINE_ARN'],
            input=input_payload
        )
        print(f"Started pipeline for s3://{bucket}/{key}")
    return {'statusCode': 200}
`),
      role: triggerRole,
      timeout: cdk.Duration.seconds(30),
      environment: {
        STATE_MACHINE_ARN: stateMachine.stateMachineArn,
      },
    });

    // S3 notification: raw/ prefix → trigger lambda
    dataBucket.addEventNotification(
      s3.EventType.OBJECT_CREATED,
      new s3n.LambdaDestination(triggerLambda),
      { prefix: 'raw/' }
    );

    // ─────────────────────────────────────────────
    // 9. API GATEWAY
    // ─────────────────────────────────────────────
    const api = new apigateway.RestApi(this, 'IngestionApi', {
      restApiName: 'iso27001-ingestion-api',
      description: 'API para generación de URLs prefirmadas y gestión del pipeline de ingesta',
      defaultCorsPreflightOptions: {
        allowOrigins: apigateway.Cors.ALL_ORIGINS,
        allowMethods: apigateway.Cors.ALL_METHODS,
        allowHeaders: ['Content-Type', 'Authorization'],
      },
      deployOptions: {
        stageName: 'v1',
        loggingLevel: apigateway.MethodLoggingLevel.INFO,
        dataTraceEnabled: true,
        metricsEnabled: true,
      },
    });

    // POST /upload/presigned-url
    const uploadResource = api.root.addResource('upload');
    const presignedResource = uploadResource.addResource('presigned-url');
    presignedResource.addMethod(
      'POST',
      new apigateway.LambdaIntegration(presignedUrlLambda, {
        requestTemplates: { 'application/json': '{ "statusCode": "200" }' },
      }),
      {
        methodResponses: [
          {
            statusCode: '200',
            responseModels: { 'application/json': apigateway.Model.EMPTY_MODEL },
          },
          { statusCode: '400' },
          { statusCode: '500' },
        ],
      }
    );

    // GET /pipeline/status/{executionArn}
    const pipelineResource = api.root.addResource('pipeline');
    const statusResource = pipelineResource.addResource('status');
    const executionResource = statusResource.addResource('{executionArn}');

    const statusLambdaRole = new iam.Role(this, 'StatusLambdaRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'),
      ],
      inlinePolicies: {
        DescribeExecution: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              actions: ['states:DescribeExecution'],
              resources: ['*'],
            }),
          ],
        }),
      },
    });

    const statusLambda = new lambda.Function(this, 'PipelineStatusLambda', {
      functionName: 'iso27001-pipeline-status',
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'index.handler',
      code: lambda.Code.fromInline(`
import boto3, json, urllib.parse

sfn = boto3.client('stepfunctions')

def handler(event, context):
    arn = urllib.parse.unquote(
        event.get('pathParameters', {}).get('executionArn', '')
    )
    if not arn:
        return {'statusCode': 400, 'body': json.dumps({'error': 'executionArn required'})}
    resp = sfn.describe_execution(executionArn=arn)
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({
            'status': resp['status'],
            'startDate': resp['startDate'].isoformat(),
            'stopDate': resp.get('stopDate', ''),
            'input': json.loads(resp.get('input', '{}')),
        }, default=str)
    }
`),
      role: statusLambdaRole,
      timeout: cdk.Duration.seconds(30),
    });

    executionResource.addMethod(
      'GET',
      new apigateway.LambdaIntegration(statusLambda)
    );

    // ─────────────────────────────────────────────
    // 10. OUTPUTS
    // ─────────────────────────────────────────────
    new cdk.CfnOutput(this, 'OssCollectionArn', {
      value: ossCollection.attrArn,
      description: 'OpenSearch Serverless collection ARN',
      exportName: 'Iso27001OssCollectionArn',
    });

    new cdk.CfnOutput(this, 'OssCollectionEndpoint', {
      value: ossCollection.attrCollectionEndpoint,
      description: 'OpenSearch Serverless collection endpoint',
      exportName: 'Iso27001OssEndpoint',
    });

    new cdk.CfnOutput(this, 'KbRoleArn', {
      value: kbRole.roleArn,
      description: 'IAM role ARN for Bedrock Knowledge Base',
      exportName: 'Iso27001KbRoleArn',
    });

    new cdk.CfnOutput(this, 'BucketName', {
      value: dataBucket.bucketName,
      description: 'S3 bucket para datos ISO 27001',
      exportName: 'Iso27001BucketName',
    });

    new cdk.CfnOutput(this, 'ApiEndpoint', {
      value: api.url,
      description: 'API Gateway endpoint',
      exportName: 'Iso27001ApiEndpoint',
    });

    new cdk.CfnOutput(this, 'StateMachineArn', {
      value: stateMachine.stateMachineArn,
      description: 'Step Functions state machine ARN',
      exportName: 'Iso27001StateMachineArn',
    });

    new cdk.CfnOutput(this, 'PresignedUrlEndpoint', {
      value: `${api.url}upload/presigned-url`,
      description: 'Endpoint para generar URLs prefirmadas',
    });
  }
}
