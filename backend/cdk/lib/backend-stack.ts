import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as cloudwatch from 'aws-cdk-lib/aws-cloudwatch';
import * as sns from 'aws-cdk-lib/aws-sns';
import * as path from 'path';

/**
 * BackendStack — Deploys the multi-agent ISO 27001 audit backend:
 *
 * - Lambda functions for each orchestration framework (Strands, LangGraph, CrewAI)
 * - DynamoDB table for metrics persistence
 * - API Gateway for triggering audits
 * - CloudWatch dashboard and alarms
 * - IAM roles with least-privilege Bedrock access
 *
 * Imports from IngestionStack: bucket name, KB role ARN, OpenSearch endpoint
 */
export class BackendStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
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
                'bedrock-agentcore:InvokeMemory',
                'bedrock-agentcore:GetMemory',
                'bedrock-agentcore:ListMemories',
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
    // 3. LAMBDA LAYER — Shared Python dependencies
    // ─────────────────────────────────────────────────────────────────────
    const sharedLayer = new lambda.LayerVersion(this, 'SharedDepsLayer', {
      layerVersionName: 'iso27001-backend-shared-deps',
      description: 'Shared Python dependencies: boto3, pydantic, strands-agents',
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_12],
      code: lambda.Code.fromAsset(path.join(__dirname, '../../layers/shared')),
    });

    // ─────────────────────────────────────────────────────────────────────
    // 4. LAMBDA — Strands Agents Orchestrator
    // ─────────────────────────────────────────────────────────────────────
    const commonEnv = {
      BUCKET_NAME: bucketName,
      METRICS_TABLE: metricsTable.tableName,
      FINDINGS_TABLE: findingsTable.tableName,
      METRICS_PREFIX: 'metrics/',
      PRIMARY_MODEL_ID: 'openai.gpt-oss-120b-1:0',
      FAST_MODEL_ID: 'qwen.qwen3-32b-v1:0',
      KNOWLEDGE_BASE_ID: '', // Set post-deployment
      AGENTCORE_MEMORY_ID: '', // Set after: agentcore memory create iso27001_audit_memory --wait
      LOG_LEVEL: 'INFO',
    };

    const strandsLambda = new lambda.Function(this, 'StrandsOrchestratorLambda', {
      functionName: 'iso27001-strands-orchestrator',
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'handler.lambda_handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../../strandsagents')),
      layers: [sharedLayer],
      role: agentLambdaRole,
      timeout: cdk.Duration.minutes(10),
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
    const langgraphLambda = new lambda.Function(this, 'LangGraphOrchestratorLambda', {
      functionName: 'iso27001-langgraph-orchestrator',
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'handler.lambda_handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../../langgraph')),
      layers: [sharedLayer],
      role: agentLambdaRole,
      timeout: cdk.Duration.minutes(10),
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
    const crewaiLambda = new lambda.Function(this, 'CrewAIOrchestratorLambda', {
      functionName: 'iso27001-crewai-orchestrator',
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'handler.lambda_handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../../crewai')),
      layers: [sharedLayer],
      role: agentLambdaRole,
      timeout: cdk.Duration.minutes(10),
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
    const comp2013Lambda = new lambda.Function(this, 'Comp2013OrchestratorLambda', {
      functionName: 'iso27001-comp2013-orchestrator',
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'handler.lambda_handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../../comp2013')),
      layers: [sharedLayer],
      role: agentLambdaRole,
      timeout: cdk.Duration.minutes(10),
      memorySize: 2048,
      environment: {
        ...commonEnv,
        FRAMEWORK: 'comp2013',
        PRIMARY_MODEL_ID: 'us.anthropic.claude-sonnet-4-5-20250929-v1:0',
        JUDGE_MODEL_ID: 'us.anthropic.claude-sonnet-4-5-20250929-v1:0',
        VECTOR_STORE_BUCKET: 'iso27001-vectors-e16',
        VECTOR_STORE_INDEX: 'iso27001-compliance-index',
        EMBEDDING_MODEL: 'amazon.titan-embed-text-v2:0',
        TOP_K: '3',
      },
      logRetention: logs.RetentionDays.TWO_WEEKS,
    });

    // ─────────────────────────────────────────────────────────────────────
    // 7. API GATEWAY — Audit trigger API
    // ─────────────────────────────────────────────────────────────────────
    const api = new apigateway.RestApi(this, 'BackendApi', {
      restApiName: 'iso27001-backend-api',
      description: 'API for triggering ISO 27001 multi-agent audits',
      defaultCorsPreflightOptions: {
        allowOrigins: apigateway.Cors.ALL_ORIGINS,
        allowMethods: apigateway.Cors.ALL_METHODS,
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

    // POST /audit/strands
    const auditResource = api.root.addResource('audit');

    const strandsResource = auditResource.addResource('strands');
    strandsResource.addMethod('POST', new apigateway.LambdaIntegration(strandsLambda));

    // POST /audit/langgraph
    const langgraphResource = auditResource.addResource('langgraph');
    langgraphResource.addMethod('POST', new apigateway.LambdaIntegration(langgraphLambda));

    // POST /audit/crewai
    const crewaiResource = auditResource.addResource('crewai');
    crewaiResource.addMethod('POST', new apigateway.LambdaIntegration(crewaiLambda));

    // POST /audit/comp2013
    const comp2013Resource = auditResource.addResource('comp2013');
    comp2013Resource.addMethod('POST', new apigateway.LambdaIntegration(comp2013Lambda));

    // ─────────────────────────────────────────────────────────────────────
    // 8. SNS TOPIC — Alerts
    // ─────────────────────────────────────────────────────────────────────
    const alertsTopic = new sns.Topic(this, 'AlertsTopic', {
      topicName: 'iso27001-audit-alerts',
      displayName: 'ISO 27001 Audit System Alerts',
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

    new cdk.CfnOutput(this, 'StrandsEndpoint', {
      value: `${api.url}audit/strands`,
      description: 'Strands Agents audit endpoint',
    });

    new cdk.CfnOutput(this, 'LangGraphEndpoint', {
      value: `${api.url}audit/langgraph`,
      description: 'LangGraph audit endpoint',
    });

    new cdk.CfnOutput(this, 'CrewAIEndpoint', {
      value: `${api.url}audit/crewai`,
      description: 'CrewAI audit endpoint',
    });

    new cdk.CfnOutput(this, 'Comp2013Endpoint', {
      value: `${api.url}audit/comp2013`,
      description: 'ISO 27001:2013 comparative audit endpoint',
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
