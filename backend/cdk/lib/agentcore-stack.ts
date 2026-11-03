import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as agentcore from 'aws-cdk-lib/aws-bedrockagentcore';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as ecrAssets from 'aws-cdk-lib/aws-ecr-assets';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as path from 'path';

const MODEL_ID = 'us.anthropic.claude-sonnet-4-5-20250929-v1:0';

/** key: prefix of the <KEY>_AGENT_ARN variable read by shared/invocation.py */
const SUB_AGENTS = [
  { key: 'PLANNING', dir: 'planning_agent', name: 'iso27001_planning' },
  { key: 'EVIDENCE', dir: 'evidence_agent', name: 'iso27001_evidence' },
  { key: 'ORG_CONTROLS', dir: 'organizational_controls_agent', name: 'iso27001_org_controls' },
  { key: 'PEOPLE_CONTROLS', dir: 'people_controls_agent', name: 'iso27001_people_controls' },
  { key: 'PHYSICAL_CONTROLS', dir: 'physical_controls_agent', name: 'iso27001_physical_controls' },
  { key: 'TECH_CONTROLS', dir: 'technological_controls_agent', name: 'iso27001_tech_controls' },
];

export interface AgentCoreStackProps extends cdk.StackProps {
  /** Site origin allowed to upload evidence directly to the data bucket */
  allowedOrigin: string;
}

/**
 * AgentCoreStack — Deploys the multi-agent audit system on Bedrock AgentCore:
 *
 * - The data resources shared with the platform API: audit records and evidence bucket
 * - One Runtime per agent, built from backend/agentcore/Dockerfile
 * - Memory (STM + LTM), attached only to the orchestrator
 * - An MCP Gateway exposing read-only knowledge base access to external clients
 */
export class AgentCoreStack extends cdk.Stack {
  public readonly orchestratorRuntimeArn: string;
  public readonly auditsTable: dynamodb.ITable;
  public readonly dataBucket: s3.IBucket;

  constructor(scope: Construct, id: string, props: AgentCoreStackProps) {
    super(scope, id, props);

    const knowledgeBaseId: string = this.node.tryGetContext('knowledgeBaseId') || '';
    const modelId: string = this.node.tryGetContext('modelId') || MODEL_ID;
    const agentCoreDir = path.join(__dirname, '../../agentcore');

    // ─────────────────────────────────────────────────────────────────────
    // 1. SHARED DATA — Audit records and evidence/report storage
    // ─────────────────────────────────────────────────────────────────────
    this.auditsTable = new dynamodb.Table(this, 'AuditsTable', {
      tableName: 'ValkiriaAudits',
      partitionKey: { name: 'tenant_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'id', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
      pointInTimeRecoverySpecification: { pointInTimeRecoveryEnabled: true },
    });

    this.dataBucket = new s3.Bucket(this, 'AuditDataBucket', {
      bucketName: `valkiria-audit-data-${this.account}`,
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      enforceSSL: true,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
      cors: [{
        allowedMethods: [s3.HttpMethods.PUT],
        allowedOrigins: [props.allowedOrigin],
        allowedHeaders: ['*'],
        maxAge: 3600,
      }],
    });

    // Created with fixed names by the backend stack and the agents' tools
    const findingsTableArn = this.formatArn({ service: 'dynamodb', resource: 'table', resourceName: 'AuditFindings' });

    // ─────────────────────────────────────────────────────────────────────
    // 2. MEMORY — Session summaries and long-term facts, scoped per tenant
    // ─────────────────────────────────────────────────────────────────────
    const memory = new agentcore.CfnMemory(this, 'AuditMemory', {
      name: 'iso27001_audit_memory',
      description: 'Memory for the ISO 27001 multi-agent audit orchestrator',
      eventExpiryDuration: 90,
      memoryStrategies: [
        {
          summaryMemoryStrategy: {
            name: 'AuditSessionSummary',
            namespaces: ['/summaries/{actorId}/{sessionId}'],
          },
        },
        {
          semanticMemoryStrategy: {
            name: 'OrganizationalFacts',
            namespaces: ['/facts/{actorId}'],
          },
        },
      ],
    });

    // ─────────────────────────────────────────────────────────────────────
    // 3. IAM — Execution role shared by the agent runtimes
    // ─────────────────────────────────────────────────────────────────────
    const runtimeRole = new iam.Role(this, 'RuntimeRole', {
      assumedBy: new iam.ServicePrincipal('bedrock-agentcore.amazonaws.com', {
        conditions: {
          StringEquals: { 'aws:SourceAccount': this.account },
          ArnLike: { 'aws:SourceArn': this.formatArn({ service: 'bedrock-agentcore', resource: '*' }) },
        },
      }),
    });

    runtimeRole.addToPolicy(new iam.PolicyStatement({
      actions: [
        'bedrock:InvokeModel',
        'bedrock:InvokeModelWithResponseStream',
        'bedrock:Retrieve',
        'bedrock:RetrieveAndGenerate',
        'bedrock:GetInferenceProfile',
      ],
      resources: ['*'],
    }));
    runtimeRole.addToPolicy(new iam.PolicyStatement({
      actions: ['dynamodb:PutItem', 'dynamodb:GetItem', 'dynamodb:Query'],
      resources: [findingsTableArn, `${findingsTableArn}/index/*`],
    }));
    runtimeRole.addToPolicy(new iam.PolicyStatement({
      actions: ['dynamodb:UpdateItem'],
      resources: [this.auditsTable.tableArn],
    }));
    this.dataBucket.grantReadWrite(runtimeRole);
    runtimeRole.addToPolicy(new iam.PolicyStatement({
      actions: [
        'bedrock-agentcore:CreateEvent',
        'bedrock-agentcore:ListEvents',
        'bedrock-agentcore:GetEvent',
        'bedrock-agentcore:RetrieveMemoryRecords',
        'bedrock-agentcore:ListMemoryRecords',
      ],
      resources: [memory.attrMemoryArn],
    }));
    runtimeRole.addToPolicy(new iam.PolicyStatement({
      actions: ['logs:CreateLogGroup', 'logs:CreateLogStream', 'logs:PutLogEvents', 'logs:DescribeLogStreams', 'logs:DescribeLogGroups'],
      resources: [this.formatArn({
        service: 'logs',
        resource: 'log-group',
        resourceName: '/aws/bedrock-agentcore/runtimes/*',
        arnFormat: cdk.ArnFormat.COLON_RESOURCE_NAME,
      }) + '*'],
    }));
    runtimeRole.addToPolicy(new iam.PolicyStatement({
      actions: ['ecr:GetAuthorizationToken'],
      resources: ['*'],
    }));

    // ─────────────────────────────────────────────────────────────────────
    // 4. RUNTIMES — One per agent. Sub-agents first: the orchestrator needs their ARNs
    // ─────────────────────────────────────────────────────────────────────
    const commonEnv: Record<string, string> = {
      AWS_REGION: this.region,
      KNOWLEDGE_BASE_ID: knowledgeBaseId,
      BUCKET_NAME: this.dataBucket.bucketName,
      FINDINGS_TABLE: 'AuditFindings',
      AUDITS_TABLE: this.auditsTable.tableName,
      MODEL_ID: modelId,
      GENERATION_MODEL_ID: modelId,
    };

    const createRuntime = (dir: string, name: string, environmentVariables: Record<string, string>) => {
      const image = new ecrAssets.DockerImageAsset(this, `${name}Image`, {
        directory: agentCoreDir,
        buildArgs: { AGENT_DIR: dir },
        platform: ecrAssets.Platform.LINUX_ARM64,
      });
      image.repository.grantPull(runtimeRole);

      const runtime = new agentcore.CfnRuntime(this, `${name}Runtime`, {
        agentRuntimeName: name,
        roleArn: runtimeRole.roleArn,
        agentRuntimeArtifact: { containerConfiguration: { containerUri: image.imageUri } },
        networkConfiguration: { networkMode: 'PUBLIC' },
        protocolConfiguration: 'HTTP',
        environmentVariables,
      });
      // The service validates its permissions when the runtime is created
      runtime.node.addDependency(runtimeRole);
      return runtime;
    };

    const subAgentArns: Record<string, string> = {};
    for (const agent of SUB_AGENTS) {
      const runtime = createRuntime(agent.dir, agent.name, commonEnv);
      subAgentArns[`${agent.key}_AGENT_ARN`] = runtime.attrAgentRuntimeArn;
      new cdk.CfnOutput(this, `${agent.key}RuntimeArn`, { value: runtime.attrAgentRuntimeArn });
    }

    // Memory goes on the orchestrator only, the one component that receives the
    // tenant as actor: sub-agent calls carry an actor chosen by the model.
    const orchestrator = createRuntime('consolidation_agent', 'iso27001_consolidation', {
      ...commonEnv,
      ...subAgentArns,
      AGENTCORE_MEMORY_ID: memory.attrMemoryId,
    });
    this.orchestratorRuntimeArn = orchestrator.attrAgentRuntimeArn;

    runtimeRole.addToPolicy(new iam.PolicyStatement({
      actions: ['bedrock-agentcore:InvokeAgentRuntime'],
      resources: [this.formatArn({ service: 'bedrock-agentcore', resource: 'runtime', resourceName: 'iso27001_*' })],
    }));

    // ─────────────────────────────────────────────────────────────────────
    // 5. MCP GATEWAY — Read-only knowledge base tool, authorized with IAM
    // ─────────────────────────────────────────────────────────────────────
    const gatewayToolsLambda = new lambda.Function(this, 'GatewayToolsLambda', {
      functionName: 'iso27001-agentcore-gateway-tools',
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'handler.lambda_handler',
      code: lambda.Code.fromAsset(path.join(agentCoreDir, 'gateway_tools')),
      timeout: cdk.Duration.seconds(60),
      memorySize: 256,
      environment: { KNOWLEDGE_BASE_ID: knowledgeBaseId },
      logRetention: logs.RetentionDays.TWO_WEEKS,
    });
    gatewayToolsLambda.addToRolePolicy(new iam.PolicyStatement({
      actions: ['bedrock:Retrieve'],
      resources: [this.formatArn({ service: 'bedrock', resource: 'knowledge-base', resourceName: knowledgeBaseId || '*' })],
    }));

    const gatewayRole = new iam.Role(this, 'GatewayRole', {
      assumedBy: new iam.ServicePrincipal('bedrock-agentcore.amazonaws.com'),
    });
    gatewayToolsLambda.grantInvoke(gatewayRole);

    const gateway = new agentcore.CfnGateway(this, 'AuditGateway', {
      name: 'iso27001-audit-gateway',
      description: 'MCP access to the ISO 27001 knowledge base',
      roleArn: gatewayRole.roleArn,
      protocolType: 'MCP',
      authorizerType: 'AWS_IAM',
    });

    new agentcore.CfnGatewayTarget(this, 'KnowledgeBaseTarget', {
      gatewayIdentifier: gateway.attrGatewayIdentifier,
      name: 'knowledge-base',
      description: 'Knowledge base retrieval',
      credentialProviderConfigurations: [{ credentialProviderType: 'GATEWAY_IAM_ROLE' }],
      targetConfiguration: {
        mcp: {
          lambda: {
            lambdaArn: gatewayToolsLambda.functionArn,
            toolSchema: {
              inlinePayload: [{
                name: 'query_knowledge_base',
                description: 'Busca pasajes relevantes en la base de conocimiento ISO 27001',
                inputSchema: {
                  type: 'object',
                  required: ['query'],
                  properties: {
                    query: { type: 'string', description: 'Consulta en lenguaje natural' },
                    number_of_results: { type: 'integer', description: 'Pasajes a devolver (máximo 20)' },
                  },
                },
              }],
            },
          },
        },
      },
    });

    // ─────────────────────────────────────────────────────────────────────
    // 6. OUTPUTS
    // ─────────────────────────────────────────────────────────────────────
    new cdk.CfnOutput(this, 'OrchestratorRuntimeArn', { value: orchestrator.attrAgentRuntimeArn });
    new cdk.CfnOutput(this, 'MemoryId', { value: memory.attrMemoryId });
    new cdk.CfnOutput(this, 'GatewayUrl', { value: gateway.attrGatewayUrl });
    new cdk.CfnOutput(this, 'AuditDataBucketName', { value: this.dataBucket.bucketName });
    new cdk.CfnOutput(this, 'AuditsTableName', { value: this.auditsTable.tableName });
  }
}
