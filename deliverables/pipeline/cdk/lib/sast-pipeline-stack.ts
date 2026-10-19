import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as codepipeline from 'aws-cdk-lib/aws-codepipeline';
import * as codepipeline_actions from 'aws-cdk-lib/aws-codepipeline-actions';
import * as codebuild from 'aws-cdk-lib/aws-codebuild';
import * as s3n from 'aws-cdk-lib/aws-s3-notifications';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as path from 'path';

export class SastPipelineStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

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
          allowedMethods: [s3.HttpMethods.PUT, s3.HttpMethods.POST],
          allowedOrigins: ['*'],
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

    // ─────────────────────────────────────────────
    // 3. CODEBUILD — SAST Analysis Project
    // Unzips the uploaded code and runs Semgrep SAST
    // ─────────────────────────────────────────────
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
        phases: {
          install: {
            'runtime-versions': {
              python: '3.12',
            },
            commands: [
              'echo "[INFO] Installing SAST tools..."',
              'pip install semgrep',
            ],
          },
          pre_build: {
            commands: [
              'echo "[INFO] Preparing source code for analysis..."',
              'echo "[INFO] Source files from S3 .zip already extracted by CodePipeline"',
              'ls -la',
              'echo "[INFO] Source code ready for SAST analysis"',
            ],
          },
          build: {
            commands: [
              'echo "[INFO] Running Semgrep SAST analysis..."',
              'semgrep scan --config=auto --json --output=semgrep-results.json . || true',
              'echo "[INFO] Running Semgrep with OWASP rules..."',
              'semgrep scan --config=p/owasp-top-ten --json --output=semgrep-owasp.json . || true',
              'echo "[INFO] Running Semgrep with security-audit rules..."',
              'semgrep scan --config=p/security-audit --json --output=semgrep-security.json . || true',
              'echo "[INFO] SAST analysis complete"',
            ],
          },
          post_build: {
            commands: [
              'echo "[INFO] Consolidating SAST results..."',
              'python -c "' +
                'import json, os, datetime;' +
                'results = {};' +
                'for f in [\'semgrep-results.json\', \'semgrep-owasp.json\', \'semgrep-security.json\']:' +
                '    try:' +
                '        with open(f) as fh: results[f.replace(\'.json\',\'\')] = json.load(fh)' +
                '    except: results[f.replace(\'.json\',\'\')] = {\'error\': \'file not found\'};' +
                'consolidated = {' +
                '    \'timestamp\': datetime.datetime.utcnow().isoformat(),'+
                '    \'scan_type\': \'SAST\','+
                '    \'tool\': \'semgrep\','+
                '    \'results\': results'+
                '};' +
                'with open(\'sast-consolidated-report.json\', \'w\') as out: json.dump(consolidated, out, indent=2)' +
              '"',
              'echo "[INFO] Uploading results to S3..."',
              'TIMESTAMP=$(date +%Y%m%d-%H%M%S)',
              'aws s3 cp sast-consolidated-report.json s3://${RESULTS_BUCKET}/${RESULTS_PREFIX}${TIMESTAMP}/sast-consolidated-report.json',
              'aws s3 cp semgrep-results.json s3://${RESULTS_BUCKET}/${RESULTS_PREFIX}${TIMESTAMP}/semgrep-results.json || true',
              'aws s3 cp semgrep-owasp.json s3://${RESULTS_BUCKET}/${RESULTS_PREFIX}${TIMESTAMP}/semgrep-owasp.json || true',
              'aws s3 cp semgrep-security.json s3://${RESULTS_BUCKET}/${RESULTS_PREFIX}${TIMESTAMP}/semgrep-security.json || true',
            ],
          },
        },
        artifacts: {
          files: [
            'sast-consolidated-report.json',
            'semgrep-results.json',
            'semgrep-owasp.json',
            'semgrep-security.json',
          ],
          'discard-paths': 'yes',
        },
      }),
    });

    // Grant CodeBuild access to results bucket
    resultsBucket.grantReadWrite(sastBuildProject);

    // ─────────────────────────────────────────────
    // 4. CODEPIPELINE — Orchestrates the SAST flow
    // ─────────────────────────────────────────────
    const sourceOutput = new codepipeline.Artifact('SourceCode');
    const sastOutput = new codepipeline.Artifact('SastResults');

    const pipeline = new codepipeline.Pipeline(this, 'SastPipeline', {
      pipelineName: 'iso27001-sast-pipeline',
      pipelineType: codepipeline.PipelineType.V2,
      restartExecutionOnUpdate: false,
      stages: [
        {
          stageName: 'Source',
          actions: [
            new codepipeline_actions.S3SourceAction({
              actionName: 'S3Source',
              bucket: sourceBucket,
              bucketKey: 'uploads/application.zip',
              output: sourceOutput,
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
              outputs: [sastOutput],
            }),
          ],
        },
        {
          stageName: 'Agent_Evaluation',
          actions: [
            new codepipeline_actions.LambdaInvokeAction({
              actionName: 'EvaluateSastResults',
              lambda: this.createAgentEvaluationLambda(resultsBucket),
              userParameters: {
                resultsBucket: resultsBucket.bucketName,
                resultsPrefix: 'sast-reports/',
              },
            }),
          ],
        },
      ],
    });

    // Grant pipeline read access to source bucket
    sourceBucket.grantRead(pipeline.role);

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
        UPLOAD_KEY: 'uploads/application.zip',
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
  private createAgentEvaluationLambda(resultsBucket: s3.Bucket): lambda.Function {
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
        BedrockAccess: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              actions: [
                'bedrock:InvokeModel',
                'bedrock:RetrieveAndGenerate',
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
      timeout: cdk.Duration.minutes(10),
      memorySize: 1024,
      environment: {
        RESULTS_BUCKET: resultsBucket.bucketName,
        RESULTS_PREFIX: 'sast-reports/',
        EVALUATION_PREFIX: 'agent-evaluations/',
        GENERATION_MODEL_ID: 'amazon.nova-pro-v1:0',
        KB_ID: '', // Set after KB is created or via SSM parameter
      },
      logRetention: logs.RetentionDays.ONE_WEEK,
    });
  }
}
