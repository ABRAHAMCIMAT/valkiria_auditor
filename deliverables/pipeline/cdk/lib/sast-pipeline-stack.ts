import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as codepipeline from 'aws-cdk-lib/aws-codepipeline';
import * as codepipeline_actions from 'aws-cdk-lib/aws-codepipeline-actions';
import * as codebuild from 'aws-cdk-lib/aws-codebuild';
import * as cloudtrail from 'aws-cdk-lib/aws-cloudtrail';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as events_targets from 'aws-cdk-lib/aws-events-targets';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as fs from 'fs';
import * as path from 'path';

const UPLOAD_KEY = 'uploads/application.zip';
const SEMGREP_VERSION = '1.183.0';

export class SastPipelineStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const allowedOrigin: string = this.node.tryGetContext('allowedOrigin') || '*';
    const knowledgeBaseId: string = this.node.tryGetContext('knowledgeBaseId') || '';
    const auditsTableName: string = this.node.tryGetContext('auditsTableName') || 'ValkiriaAudits';
    const auditsTable = dynamodb.Table.fromTableName(this, 'AuditsTable', auditsTableName);

    // ─────────────────────────────────────────────
    // 1. S3 BUCKET — Source for .zip uploads from frontend
    // ─────────────────────────────────────────────
    const sourceBucket = new s3.Bucket(this, 'SastSourceBucket', {
      bucketName: `iso27001-sast-source-${this.account}`,
      versioned: true, // Required for CodePipeline S3 source
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
      lifecycleRules: [
        {
          id: 'expire-old-uploads',
          expiration: cdk.Duration.days(30),
          noncurrentVersionExpiration: cdk.Duration.days(7),
        },
      ],
      cors: [
        {
          allowedMethods: [s3.HttpMethods.PUT],
          allowedOrigins: [allowedOrigin],
          allowedHeaders: ['*'],
          maxAge: 3600,
        },
      ],
    });

    // ─────────────────────────────────────────────
    // 2. S3 BUCKET — SAST results and reports
    // ─────────────────────────────────────────────
    const resultsBucket = new s3.Bucket(this, 'SastResultsBucket', {
      bucketName: `iso27001-sast-results-${this.account}`,
      versioned: true,
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    // S3 event triggers for CodePipeline are delivered through CloudTrail data
    // events: without a trail the pipeline never starts on upload.
    const sourceTrail = new cloudtrail.Trail(this, 'SastSourceTrail', {
      trailName: 'iso27001-sast-source-events',
      isMultiRegionTrail: false,
      includeGlobalServiceEvents: false,
    });
    sourceTrail.addS3EventSelector(
      [{ bucket: sourceBucket, objectPrefix: UPLOAD_KEY }],
      { readWriteType: cloudtrail.ReadWriteType.WRITE_ONLY, includeManagementEvents: false },
    );

    // ─────────────────────────────────────────────
    // 3. CODEBUILD — SAST Analysis Project
    // Unzips the uploaded code and runs Semgrep SAST
    // ─────────────────────────────────────────────
    const consolidateScript = fs
      .readFileSync(path.join(__dirname, '../../scripts/consolidate_sast.py'))
      .toString('base64');

    const sastBuildProject = new codebuild.PipelineProject(this, 'SastBuildProject', {
      projectName: 'iso27001-sast-analysis',
      description: 'Unzips uploaded application code and runs SAST (Semgrep)',
      environment: {
        buildImage: codebuild.LinuxBuildImage.STANDARD_7_0,
        computeType: codebuild.ComputeType.MEDIUM,
        privileged: false,
      },
      timeout: cdk.Duration.minutes(30),
      logging: {
        cloudWatch: {
          logGroup: new logs.LogGroup(this, 'SastBuildLogGroup', {
            logGroupName: '/aws/codebuild/iso27001-sast-analysis',
            retention: logs.RetentionDays.TWO_WEEKS,
            removalPolicy: cdk.RemovalPolicy.DESTROY,
          }),
        },
      },
      environmentVariables: {
        RESULTS_BUCKET: { value: resultsBucket.bucketName },
        RESULTS_PREFIX: { value: 'sast-reports/' },
      },
      buildSpec: codebuild.BuildSpec.fromObject({
        version: '0.2',
        env: {
          'exported-variables': ['REPORT_KEY'],
        },
        phases: {
          install: {
            'runtime-versions': {
              python: '3.12',
            },
            commands: [
              'echo "[INFO] Installing SAST tools..."',
              `pip install semgrep==${SEMGREP_VERSION}`,
            ],
          },
          pre_build: {
            commands: [
              'echo "[INFO] Source files from S3 .zip already extracted by CodePipeline"',
              'ls -la',
              // The source artifact is the audited code, so the script travels in the buildspec
              `echo ${consolidateScript} | base64 -d > /tmp/consolidate_sast.py`,
            ],
          },
          build: {
            commands: [
              // One run with both rulesets avoids counting overlapping rules twice.
              // Semgrep exits non-zero only on real errors, which must fail this stage.
              'echo "[INFO] Running Semgrep SAST analysis..."',
              'semgrep scan --metrics=off --config=p/owasp-top-ten --config=p/security-audit --json --output=/tmp/semgrep-results.json .',
              'echo "[INFO] SAST analysis complete"',
            ],
          },
          post_build: {
            commands: [
              // post_build runs even after a failed build: stop before publishing anything
              'if [ "$CODEBUILD_BUILD_SUCCEEDING" != "1" ]; then echo "[ERROR] SAST scan failed"; exit 1; fi',
              'echo "[INFO] Consolidating SAST results..."',
              'python /tmp/consolidate_sast.py /tmp/semgrep-results.json /tmp/sast-consolidated-report.json',
              'echo "[INFO] Uploading results to S3..."',
              'REPORT_DIR=${RESULTS_PREFIX}build-${CODEBUILD_BUILD_NUMBER}',
              'REPORT_KEY=${REPORT_DIR}/sast-consolidated-report.json',
              'aws s3 cp /tmp/sast-consolidated-report.json s3://${RESULTS_BUCKET}/${REPORT_KEY}',
              'aws s3 cp /tmp/semgrep-results.json s3://${RESULTS_BUCKET}/${REPORT_DIR}/semgrep-results.json',
            ],
          },
        },
      }),
    });

    // Grant CodeBuild access to results bucket
    resultsBucket.grantReadWrite(sastBuildProject);

    // ─────────────────────────────────────────────
    // 4. CODEPIPELINE — Orchestrates the SAST flow
    // ─────────────────────────────────────────────
    const sourceOutput = new codepipeline.Artifact('SourceCode');
    const agentEvaluationLambda = this.createAgentEvaluationLambda(
      resultsBucket, sourceBucket, auditsTable, knowledgeBaseId,
    );

    const pipeline = new codepipeline.Pipeline(this, 'SastPipeline', {
      pipelineName: 'iso27001-sast-pipeline',
      pipelineType: codepipeline.PipelineType.V2,
      // Each upload pins its own object version, so queueing keeps concurrent uploads apart
      executionMode: codepipeline.ExecutionMode.QUEUED,
      restartExecutionOnUpdate: false,
      stages: [
        {
          stageName: 'Source',
          actions: [
            new codepipeline_actions.S3SourceAction({
              actionName: 'S3Source',
              bucket: sourceBucket,
              bucketKey: UPLOAD_KEY,
              output: sourceOutput,
              variablesNamespace: 'SourceVars',
              trigger: codepipeline_actions.S3Trigger.EVENTS,
            }),
          ],
        },
        {
          stageName: 'SAST_Analysis',
          actions: [
            new codepipeline_actions.CodeBuildAction({
              actionName: 'RunSemgrepSAST',
              project: sastBuildProject,
              input: sourceOutput,
              variablesNamespace: 'SastVars',
            }),
          ],
        },
        {
          stageName: 'Agent_Evaluation',
          actions: [
            new codepipeline_actions.LambdaInvokeAction({
              actionName: 'EvaluateSastResults',
              lambda: agentEvaluationLambda,
              userParameters: {
                reportKey: '#{SastVars.REPORT_KEY}',
                sourceVersionId: '#{SourceVars.VersionId}',
              },
            }),
          ],
        },
      ],
    });

    // Grant pipeline read access to source bucket
    sourceBucket.grantRead(pipeline.role);

    // Failures before the evaluation stage must still reach the frontend
    pipeline.onStateChange('SastPipelineFailed', {
      eventPattern: { detail: { state: ['FAILED'] } },
      target: new events_targets.LambdaFunction(agentEvaluationLambda),
    });

    // ─────────────────────────────────────────────
    // 5. LAMBDA — Presigned URL for .zip upload
    // ─────────────────────────────────────────────
    const uploadLambdaRole = new iam.Role(this, 'UploadLambdaRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'),
      ],
      inlinePolicies: {
        S3Upload: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              actions: ['s3:PutObject'],
              resources: [`${sourceBucket.bucketArn}/uploads/*`],
            }),
          ],
        }),
        AuditRecords: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              actions: ['dynamodb:GetItem', 'dynamodb:UpdateItem'],
              resources: [auditsTable.tableArn],
            }),
          ],
        }),
      },
    });

    const uploadLambda = new lambda.Function(this, 'SastUploadLambda', {
      functionName: 'iso27001-sast-upload-url',
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'handler.lambda_handler',
      code: lambda.Code.fromAsset(
        path.join(__dirname, '../../lambdas/sast_upload')
      ),
      role: uploadLambdaRole,
      timeout: cdk.Duration.seconds(30),
      memorySize: 256,
      environment: {
        BUCKET_NAME: sourceBucket.bucketName,
        UPLOAD_KEY,
        AUDITS_TABLE: auditsTableName,
        ALLOWED_ORIGIN: allowedOrigin,
        URL_EXPIRATION_SECONDS: '3600',
      },
      logRetention: logs.RetentionDays.ONE_WEEK,
    });

    // ─────────────────────────────────────────────
    // 6. OUTPUTS
    // ─────────────────────────────────────────────
    new cdk.CfnOutput(this, 'SourceBucketName', {
      value: sourceBucket.bucketName,
      description: 'S3 bucket for .zip code uploads (triggers pipeline)',
    });

    new cdk.CfnOutput(this, 'ResultsBucketName', {
      value: resultsBucket.bucketName,
      description: 'S3 bucket for SAST results and agent evaluation reports',
    });

    new cdk.CfnOutput(this, 'PipelineName', {
      value: pipeline.pipelineName,
      description: 'CodePipeline name for SAST analysis',
    });

    new cdk.CfnOutput(this, 'UploadLambdaArn', {
      value: uploadLambda.functionArn,
      description: 'Lambda ARN for generating presigned upload URLs',
    });
  }

  // ─────────────────────────────────────────────
  // HELPER: Agent Evaluation Lambda
  // Invokes Bedrock agent to evaluate SAST findings
  // against ISO 27001 controls using the Knowledge Base
  // ─────────────────────────────────────────────
  private createAgentEvaluationLambda(
    resultsBucket: s3.Bucket,
    sourceBucket: s3.Bucket,
    auditsTable: dynamodb.ITable,
    knowledgeBaseId: string,
  ): lambda.Function {
    const agentRole = new iam.Role(this, 'AgentEvaluationRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'),
      ],
      inlinePolicies: {
        S3Access: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              actions: ['s3:GetObject', 's3:PutObject', 's3:ListBucket'],
              resources: [resultsBucket.bucketArn, `${resultsBucket.bucketArn}/*`],
            }),
          ],
        }),
        SourceMetadata: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              actions: ['s3:GetObject', 's3:GetObjectVersion'],
              resources: [`${sourceBucket.bucketArn}/${UPLOAD_KEY}`],
            }),
          ],
        }),
        AuditRecords: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              actions: ['dynamodb:UpdateItem'],
              resources: [auditsTable.tableArn],
            }),
          ],
        }),
        BedrockAccess: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              actions: [
                'bedrock:InvokeModel',
                'bedrock:Retrieve',
              ],
              resources: ['*'],
            }),
          ],
        }),
        CodePipelineAccess: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              actions: [
                'codepipeline:PutJobSuccessResult',
                'codepipeline:PutJobFailureResult',
                'codepipeline:GetPipelineExecution',
              ],
              resources: ['*'],
            }),
          ],
        }),
      },
    });

    return new lambda.Function(this, 'AgentEvaluationLambda', {
      functionName: 'iso27001-sast-agent-evaluation',
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'handler.lambda_handler',
      code: lambda.Code.fromAsset(
        path.join(__dirname, '../../lambdas/agent_evaluation')
      ),
      role: agentRole,
      timeout: cdk.Duration.minutes(15),
      memorySize: 1024,
      environment: {
        RESULTS_BUCKET: resultsBucket.bucketName,
        EVALUATION_PREFIX: 'agent-evaluations/',
        GENERATION_MODEL_ID: 'us.amazon.nova-pro-v1:0',
        KB_ID: knowledgeBaseId,
        SOURCE_BUCKET: sourceBucket.bucketName,
        SOURCE_KEY: UPLOAD_KEY,
        AUDITS_TABLE: auditsTable.tableName,
      },
      logRetention: logs.RetentionDays.ONE_WEEK,
    });
  }
}
