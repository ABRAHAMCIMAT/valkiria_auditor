import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as cloudwatch from 'aws-cdk-lib/aws-cloudwatch';
import * as sns from 'aws-cdk-lib/aws-sns';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as s3deploy from 'aws-cdk-lib/aws-s3-deployment';
import * as cloudfront from 'aws-cdk-lib/aws-cloudfront';
import * as cognito from 'aws-cdk-lib/aws-cognito';
import * as ecrAssets from 'aws-cdk-lib/aws-ecr-assets';
import * as kms from 'aws-cdk-lib/aws-kms';
import * as path from 'path';

export interface BackendStackProps extends cdk.StackProps {
  userPool: cognito.IUserPool;
  userPoolClient: cognito.IUserPoolClient;
  siteBucket: s3.IBucket;
  distribution: cloudfront.IDistribution;
  /** Audit records table, shared with the AgentCore and SAST stacks */
  auditsTable: dynamodb.ITable;
  dataBucket: s3.IBucket;
  /** Consolidation runtime: when set, Strands audits run on AgentCore */
  orchestratorRuntimeArn?: string;
  /** Lambda that issues SAST upload URLs, from Iso27001SastPipelineStack */
  sastUploadFunctionArn?: string;
  sastResultsBucketName?: string;
}

/**
 * BackendStack — Deploys the multi-agent ISO 27001 audit backend:
 *
 * - Lambda functions for each orchestration framework (Strands, LangGraph, CrewAI)
 * - DynamoDB table for metrics persistence
 * - API Gateway with the Cognito authorizer, backed by the platform API Lambda
 * - The frontend assets with its runtime configuration
 * - CloudWatch dashboard and alarms
 * - IAM roles with least-privilege Bedrock access
 *
 * Imports from IngestionStack: bucket name, KB role ARN, OpenSearch endpoint
 */
export class BackendStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: BackendStackProps) {
    super(scope, id, props);

    // ─────────────────────────────────────────────────────────────────────
    // CROSS-STACK IMPORTS (from IngestionStack)
    // ─────────────────────────────────────────────────────────────────────
    const bucketName = cdk.Fn.importValue('Iso27001BucketName');
    const bucketArn = `arn:aws:s3:::${bucketName}`;

    // ─────────────────────────────────────────────────────────────────────
    // 1. DYNAMODB — Metrics Table
    // ─────────────────────────────────────────────────────────────────────
    const metricsTable = new dynamodb.Table(this, 'MetricsTable', {
      tableName: 'AgentCoreMetrics',
      partitionKey: { name: 'metric_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'timestamp', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
      pointInTimeRecovery: true,
    });

    metricsTable.addGlobalSecondaryIndex({
      indexName: 'agent_name-timestamp-index',
      partitionKey: { name: 'agent_name', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'timestamp', type: dynamodb.AttributeType.STRING },
      projectionType: dynamodb.ProjectionType.ALL,
    });

    metricsTable.addGlobalSecondaryIndex({
      indexName: 'metric_type-timestamp-index',
      partitionKey: { name: 'metric_type', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'timestamp', type: dynamodb.AttributeType.STRING },
      projectionType: dynamodb.ProjectionType.ALL,
    });

    // Audit Findings table
    const findingsTable = new dynamodb.Table(this, 'FindingsTable', {
      tableName: 'AuditFindings',
      partitionKey: { name: 'finding_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'audit_id', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    findingsTable.addGlobalSecondaryIndex({
      indexName: 'audit_id-index',
      partitionKey: { name: 'audit_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'finding_id', type: dynamodb.AttributeType.STRING },
      projectionType: dynamodb.ProjectionType.ALL,
    });

    // ─────────────────────────────────────────────────────────────────────
    // 2. IAM ROLE — Lambda execution role for agent Lambdas
    // ─────────────────────────────────────────────────────────────────────
    const agentLambdaRole = new iam.Role(this, 'AgentLambdaRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'),
      ],
      inlinePolicies: {
        BedrockInvoke: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              actions: [
                'bedrock:InvokeModel',
                'bedrock:InvokeModelWithResponseStream',
                'bedrock:Converse',
                'bedrock:ConverseStream',
                'bedrock:Retrieve',
                'bedrock:RetrieveAndGenerate',
              ],
              resources: ['*'],
            }),
          ],
        }),
        S3Access: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              actions: ['s3:GetObject', 's3:PutObject', 's3:ListBucket'],
              resources: [bucketArn, `${bucketArn}/*`],
            }),
          ],
        }),
        DynamoDBAccess: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              actions: [
                'dynamodb:PutItem',
                'dynamodb:GetItem',
                'dynamodb:Query',
                'dynamodb:Scan',
                'dynamodb:UpdateItem',
                'dynamodb:BatchWriteItem',
              ],
              resources: [
                metricsTable.tableArn,
                `${metricsTable.tableArn}/index/*`,
                findingsTable.tableArn,
                `${findingsTable.tableArn}/index/*`,
                props.auditsTable.tableArn,
              ],
            }),
          ],
        }),
        CloudWatchMetrics: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              actions: ['cloudwatch:PutMetricData'],
              resources: ['*'],
              conditions: {
                StringEquals: { 'cloudwatch:namespace': 'AgentCore/ISO27001Audit' },
              },
            }),
          ],
        }),
        AgentCoreMemory: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              actions: [
                'bedrock-agentcore:CreateEvent',
                'bedrock-agentcore:ListEvents',
                'bedrock-agentcore:GetEvent',
                'bedrock-agentcore:RetrieveMemoryRecords',
                'bedrock-agentcore:ListMemoryRecords',
              ],
              resources: ['*'],
            }),
          ],
        }),
        S3Vectors: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              actions: [
                's3vectors:QueryVectors',
                's3vectors:GetVectors',
                's3vectors:ListVectors',
              ],
              resources: ['*'],
            }),
          ],
        }),
      },
    });

    // ─────────────────────────────────────────────────────────────────────
    // 3. LAMBDA IMAGES — One container per service
    // Handlers import as backend.<service> and the framework dependency sets
    // exceed the zip limit, so the zip + shared layer packaging cannot run them.
    // ─────────────────────────────────────────────────────────────────────
    const serviceCode = (service: string) => lambda.DockerImageCode.fromImageAsset(
      path.join(__dirname, '../..'),
      {
        file: 'Dockerfile.lambda',
        buildArgs: { SERVICE: service },
        cmd: [`backend.${service}.handler.lambda_handler`],
        platform: ecrAssets.Platform.LINUX_ARM64,
        exclude: ['cdk', 'tests'],
      },
    );

    // ─────────────────────────────────────────────────────────────────────
    // 4. LAMBDA — Strands Agents Orchestrator
    // ─────────────────────────────────────────────────────────────────────
    const commonEnv = {
      BUCKET_NAME: bucketName,
      METRICS_TABLE: metricsTable.tableName,
      FINDINGS_TABLE: findingsTable.tableName,
      METRICS_PREFIX: 'metrics/',
      PRIMARY_MODEL_ID: 'us.anthropic.claude-sonnet-4-5-20250929-v1:0',
      FAST_MODEL_ID: 'us.anthropic.claude-sonnet-4-5-20250929-v1:0',
      KNOWLEDGE_BASE_ID: this.node.tryGetContext('knowledgeBaseId') || '',
      AUDITS_TABLE: props.auditsTable.tableName,
      AWS_ACCOUNT_ID: this.account,
      LOG_LEVEL: 'INFO',
    };

    const strandsLambda = new lambda.DockerImageFunction(this, 'StrandsOrchestratorLambda', {
      functionName: 'iso27001-strands-orchestrator',
      code: serviceCode('strandsagents'),
      architecture: lambda.Architecture.ARM_64,
      role: agentLambdaRole,
      timeout: cdk.Duration.minutes(15),
      memorySize: 2048,
      environment: {
        ...commonEnv,
        FRAMEWORK: 'strands',
      },
      logRetention: logs.RetentionDays.TWO_WEEKS,
    });

    // ─────────────────────────────────────────────────────────────────────
    // 5. LAMBDA — LangGraph Orchestrator
    // ─────────────────────────────────────────────────────────────────────
    const langgraphLambda = new lambda.DockerImageFunction(this, 'LangGraphOrchestratorLambda', {
      functionName: 'iso27001-langgraph-orchestrator',
      code: serviceCode('langgraph'),
      architecture: lambda.Architecture.ARM_64,
      role: agentLambdaRole,
      timeout: cdk.Duration.minutes(15),
      memorySize: 2048,
      environment: {
        ...commonEnv,
        FRAMEWORK: 'langgraph',
      },
      logRetention: logs.RetentionDays.TWO_WEEKS,
    });

    // ─────────────────────────────────────────────────────────────────────
    // 6. LAMBDA — CrewAI Orchestrator
    // ─────────────────────────────────────────────────────────────────────
    const crewaiLambda = new lambda.DockerImageFunction(this, 'CrewAIOrchestratorLambda', {
      functionName: 'iso27001-crewai-orchestrator',
      code: serviceCode('crewai'),
      architecture: lambda.Architecture.ARM_64,
      role: agentLambdaRole,
      timeout: cdk.Duration.minutes(15),
      memorySize: 2048,
      environment: {
        ...commonEnv,
        FRAMEWORK: 'crewai',
      },
      logRetention: logs.RetentionDays.TWO_WEEKS,
    });

    // ─────────────────────────────────────────────────────────────────────
    // 6b. LAMBDA — ISO 27001:2013 Comparative Orchestrator (comp2013)
    // ─────────────────────────────────────────────────────────────────────
    const comp2013Lambda = new lambda.DockerImageFunction(this, 'Comp2013OrchestratorLambda', {
      functionName: 'iso27001-comp2013-orchestrator',
      code: serviceCode('comp2013'),
      architecture: lambda.Architecture.ARM_64,
      role: agentLambdaRole,
      timeout: cdk.Duration.minutes(15),
      memorySize: 2048,
      environment: {
        ...commonEnv,
        FRAMEWORK: 'comp2013',
        JUDGE_MODEL_ID: 'us.anthropic.claude-sonnet-4-5-20250929-v1:0',
        VECTOR_STORE_BUCKET: 'iso27001-vectors-e16',
        VECTOR_STORE_INDEX: 'iso27001-compliance-index',
        EMBEDDING_MODEL: 'amazon.titan-embed-text-v2:0',
        TOP_K: '3',
      },
      logRetention: logs.RetentionDays.TWO_WEEKS,
    });

    // ─────────────────────────────────────────────────────────────────────
    // 7. API GATEWAY — Platform API behind the Cognito authorizer
    // Audits run asynchronously: API Gateway cuts responses at 29 seconds, so
    // the frontend starts them here and follows the status on the audit record.
    // ─────────────────────────────────────────────────────────────────────
    const siteOrigin = `https://${props.distribution.distributionDomainName}`;
    const frameworkLambdas: Record<string, lambda.IFunction> = {
      strands: strandsLambda,
      langgraph: langgraphLambda,
      crewai: crewaiLambda,
      comp2013: comp2013Lambda,
    };

    const platformLambda = new lambda.DockerImageFunction(this, 'PlatformApiLambda', {
      functionName: 'iso27001-platform-api',
      code: serviceCode('api'),
      architecture: lambda.Architecture.ARM_64,
      timeout: cdk.Duration.seconds(29),
      memorySize: 512,
      environment: {
        AUDITS_TABLE: props.auditsTable.tableName,
        FINDINGS_TABLE: findingsTable.tableName,
        DATA_BUCKET: props.dataBucket.bucketName,
        SAST_RESULTS_BUCKET: props.sastResultsBucketName || '',
        ALLOWED_ORIGIN: siteOrigin,
        ORCHESTRATOR_RUNTIME_ARN: props.orchestratorRuntimeArn || '',
        FRAMEWORK_FUNCTIONS: cdk.Stack.of(this).toJsonString(
          Object.fromEntries(Object.entries(frameworkLambdas).map(([name, fn]) => [name, fn.functionName])),
        ),
      },
      logRetention: logs.RetentionDays.TWO_WEEKS,
    });

    props.auditsTable.grantReadWriteData(platformLambda);
    findingsTable.grantReadData(platformLambda);
    props.dataBucket.grantRead(platformLambda);
    props.dataBucket.grantPut(platformLambda, 'uploads/*');
    Object.values(frameworkLambdas).forEach(fn => fn.grantInvoke(platformLambda));
    if (props.sastResultsBucketName) {
      s3.Bucket.fromBucketName(this, 'SastResultsBucket', props.sastResultsBucketName)
        .grantRead(platformLambda, 'agent-evaluations/*');
    }
    if (props.orchestratorRuntimeArn) {
      platformLambda.addToRolePolicy(new iam.PolicyStatement({
        actions: ['bedrock-agentcore:InvokeAgentRuntime'],
        resources: [props.orchestratorRuntimeArn, `${props.orchestratorRuntimeArn}/*`],
      }));
    }

    // Lambdas record their outcome and store reports where the API serves them from
    props.auditsTable.grant(agentLambdaRole, 'dynamodb:UpdateItem');
    props.dataBucket.grantReadWrite(agentLambdaRole);

    const api = new apigateway.RestApi(this, 'BackendApi', {
      restApiName: 'iso27001-backend-api',
      description: 'API for the ISO 27001 audit platform',
      defaultCorsPreflightOptions: {
        allowOrigins: [siteOrigin],
        allowMethods: ['GET', 'POST', 'DELETE', 'OPTIONS'],
        allowHeaders: ['Content-Type', 'Authorization'],
      },
      deployOptions: {
        stageName: 'v1',
        throttlingRateLimit: 10,
        throttlingBurstLimit: 20,
        metricsEnabled: true,
        loggingLevel: apigateway.MethodLoggingLevel.INFO,
      },
    });

    const authorizer = new apigateway.CognitoUserPoolsAuthorizer(this, 'PlatformAuthorizer', {
      cognitoUserPools: [props.userPool],
    });
    const secured: apigateway.MethodOptions = {
      authorizer,
      authorizationType: apigateway.AuthorizationType.COGNITO,
    };
    const platform = new apigateway.LambdaIntegration(platformLambda);

    const auditorias = api.root.addResource('auditorias');
    auditorias.addMethod('GET', platform, secured);
    auditorias.addMethod('POST', platform, secured);
    const auditoria = auditorias.addResource('{id}');
    auditoria.addMethod('GET', platform, secured);
    auditoria.addMethod('DELETE', platform, secured);

    const evaluaciones = api.root.addResource('evaluaciones');
    evaluaciones.addMethod('GET', platform, secured);
    evaluaciones.addMethod('POST', platform, secured);
    evaluaciones.addResource('{id}').addMethod('GET', platform, secured);

    // POST /audit/{framework}: strands, langgraph, crewai, comp2013
    api.root.addResource('audit').addResource('{framework}').addMethod('POST', platform, secured);

    // POST /sast/upload-url
    if (props.sastUploadFunctionArn) {
      const sastUpload = lambda.Function.fromFunctionAttributes(this, 'SastUploadFunction', {
        functionArn: props.sastUploadFunctionArn,
        sameEnvironment: true,
      });
      api.root.addResource('sast').addResource('upload-url')
        .addMethod('POST', new apigateway.LambdaIntegration(sastUpload), secured);
    }

    // Error responses generated by API Gateway need CORS too, or the browser
    // reports an expired token as a network failure instead of a 401
    for (const type of [apigateway.ResponseType.DEFAULT_4XX, apigateway.ResponseType.DEFAULT_5XX]) {
      api.addGatewayResponse(`Cors${type.responseType}`, {
        type,
        responseHeaders: { 'Access-Control-Allow-Origin': `'${siteOrigin}'` },
      });
    }

    // The site configuration depends on this API, so the assets deploy from this stack
    new s3deploy.BucketDeployment(this, 'DeployFrontend', {
      sources: [
        s3deploy.Source.asset(path.join(__dirname, '../../../frontend'), {
          exclude: ['assets/diagrams/*', 'assets/images/security_banner.jpg'],
        }),
        s3deploy.Source.data('config.js', cdk.Fn.join('', [
          'window.__API_BASE_URL__=', cdk.Stack.of(this).toJsonString(api.url), ';',
          'window.__APP_CONFIG__=', cdk.Stack.of(this).toJsonString({
            region: this.region,
            userPoolId: props.userPool.userPoolId,
            clientId: props.userPoolClient.userPoolClientId,
          }), ';',
        ])),
      ],
      destinationBucket: props.siteBucket,
      distribution: props.distribution,
      distributionPaths: ['/*'],
      memoryLimit: 512,
    });

    // ─────────────────────────────────────────────────────────────────────
    // 8. SNS TOPIC — Alerts
    // ─────────────────────────────────────────────────────────────────────
    // Customer-managed key: CloudWatch alarms cannot publish with the AWS-managed SNS key
    const alertsKey = new kms.Key(this, 'AlertsTopicKey', {
      description: 'Encrypts the ISO 27001 audit alerts topic',
      enableKeyRotation: true,
    });
    alertsKey.grant(new iam.ServicePrincipal('cloudwatch.amazonaws.com'), 'kms:Decrypt', 'kms:GenerateDataKey*');

    const alertsTopic = new sns.Topic(this, 'AlertsTopic', {
      topicName: 'iso27001-audit-alerts',
      displayName: 'ISO 27001 Audit System Alerts',
      masterKey: alertsKey,
    });

    // ─────────────────────────────────────────────────────────────────────
    // 9. CLOUDWATCH ALARMS
    // ─────────────────────────────────────────────────────────────────────
    const frameworks = [
      { name: 'strands', fn: strandsLambda },
      { name: 'langgraph', fn: langgraphLambda },
      { name: 'crewai', fn: crewaiLambda },
      { name: 'comp2013', fn: comp2013Lambda },
    ];

    for (const fw of frameworks) {
      // Error alarm
      new cloudwatch.Alarm(this, `${fw.name}ErrorAlarm`, {
        alarmName: `ISO27001-${fw.name}-Errors`,
        alarmDescription: `${fw.name} orchestrator Lambda errors > 2 in 5 min`,
        metric: fw.fn.metricErrors({ period: cdk.Duration.minutes(5) }),
        threshold: 2,
        evaluationPeriods: 1,
        comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
      }).addAlarmAction(new cdk.aws_cloudwatch_actions.SnsAction(alertsTopic));

      // Duration alarm (> 5 min)
      new cloudwatch.Alarm(this, `${fw.name}DurationAlarm`, {
        alarmName: `ISO27001-${fw.name}-Duration`,
        alarmDescription: `${fw.name} orchestrator avg duration > 5 min`,
        metric: fw.fn.metricDuration({ period: cdk.Duration.minutes(5), statistic: 'Average' }),
        threshold: 300000,
        evaluationPeriods: 2,
        comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
      }).addAlarmAction(new cdk.aws_cloudwatch_actions.SnsAction(alertsTopic));

      // Throttle alarm
      new cloudwatch.Alarm(this, `${fw.name}ThrottleAlarm`, {
        alarmName: `ISO27001-${fw.name}-Throttles`,
        alarmDescription: `${fw.name} orchestrator throttled`,
        metric: fw.fn.metricThrottles({ period: cdk.Duration.minutes(5) }),
        threshold: 1,
        evaluationPeriods: 1,
        comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
      }).addAlarmAction(new cdk.aws_cloudwatch_actions.SnsAction(alertsTopic));
    }

    // ─────────────────────────────────────────────────────────────────────
    // 10. CLOUDWATCH DASHBOARD
    // ─────────────────────────────────────────────────────────────────────
    const dashboard = new cloudwatch.Dashboard(this, 'BackendDashboard', {
      dashboardName: 'ISO27001-Backend-Overview',
    });

    // Lambda invocations comparison
    dashboard.addWidgets(
      new cloudwatch.GraphWidget({
        title: 'Orchestrator Invocations',
        left: frameworks.map(fw => fw.fn.metricInvocations()),
        width: 12,
      }),
      new cloudwatch.GraphWidget({
        title: 'Orchestrator Duration (ms)',
        left: frameworks.map(fw => fw.fn.metricDuration()),
        width: 12,
      }),
    );

    // Errors and throttles
    dashboard.addWidgets(
      new cloudwatch.GraphWidget({
        title: 'Orchestrator Errors',
        left: frameworks.map(fw => fw.fn.metricErrors()),
        width: 12,
      }),
      new cloudwatch.GraphWidget({
        title: 'Custom Metrics — Agent Execution Time',
        left: [
          new cloudwatch.Metric({
            namespace: 'AgentCore/ISO27001Audit',
            metricName: 'AgentExecutionTime',
            dimensionsMap: { AgentName: 'planning_agent' },
            statistic: 'Average',
          }),
          new cloudwatch.Metric({
            namespace: 'AgentCore/ISO27001Audit',
            metricName: 'AgentExecutionTime',
            dimensionsMap: { AgentName: 'consolidation_agent' },
            statistic: 'Average',
          }),
        ],
        width: 12,
      }),
    );

    // ─────────────────────────────────────────────────────────────────────
    // 11. OUTPUTS
    // ─────────────────────────────────────────────────────────────────────
    new cdk.CfnOutput(this, 'ApiEndpoint', {
      value: api.url,
      description: 'Backend API Gateway endpoint',
      exportName: 'Iso27001BackendApiEndpoint',
    });

    new cdk.CfnOutput(this, 'MetricsTableName', {
      value: metricsTable.tableName,
      description: 'DynamoDB table for agent metrics',
      exportName: 'Iso27001MetricsTable',
    });

    new cdk.CfnOutput(this, 'FindingsTableName', {
      value: findingsTable.tableName,
      description: 'DynamoDB table for audit findings',
      exportName: 'Iso27001FindingsTable',
    });

    new cdk.CfnOutput(this, 'AlertsTopicArn', {
      value: alertsTopic.topicArn,
      description: 'SNS topic for audit system alerts',
      exportName: 'Iso27001AlertsTopicArn',
    });
  }
}
