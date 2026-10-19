import * as cdk from 'aws-cdk-lib';
import * as cognito from 'aws-cdk-lib/aws-cognito';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as cloudfront from 'aws-cdk-lib/aws-cloudfront';
import * as origins from 'aws-cdk-lib/aws-cloudfront-origins';
import { Construct } from 'constructs';

/**
 * Configuration properties for the PlatformStack.
 * Extends StackProps with environment-specific settings.
 */
export interface PlatformStackProps extends cdk.StackProps {
  /**
   * Deployment stage (e.g., 'dev', 'staging', 'prod').
   * Used for resource naming and configuration.
   */
  stage: string;

  /**
   * The name of the existing IngestionStack to import outputs from.
   * Defaults to 'IngestionStack' if not provided.
   */
  ingestionStackName?: string;
}

/**
 * PlatformStack — Fullstack audit platform infrastructure.
 *
 * This stack extends the existing IngestionStack by importing its outputs
 * (S3 bucket, Step Functions state machine, OpenSearch collection) and
 * building the fullstack platform on top: Cognito, API Gateway, DynamoDB,
 * CloudFront, Lambda functions, and EventBridge rules.
 */
export class PlatformStack extends cdk.Stack {
  /** Imported S3 data bucket name from IngestionStack */
  public readonly dataBucketName: string;

  /** Imported Step Functions state machine ARN from IngestionStack */
  public readonly stateMachineArn: string;

  /** Imported OpenSearch Serverless collection ARN from IngestionStack */
  public readonly ossCollectionArn: string;

  /** Imported OpenSearch Serverless collection endpoint from IngestionStack */
  public readonly ossCollectionEndpoint: string;

  /** Imported Bedrock KB role ARN from IngestionStack */
  public readonly kbRoleArn: string;

  /** Cognito User Pool for authentication */
  public readonly userPool: cognito.UserPool;

  /** Cognito User Pool App Client */
  public readonly userPoolClient: cognito.UserPoolClient;

  /** S3 bucket for frontend static assets */
  public readonly staticAssetsBucket: s3.Bucket;

  /** CloudFront distribution for serving the frontend */
  public readonly distribution: cloudfront.Distribution;

  constructor(scope: Construct, id: string, props: PlatformStackProps) {
    super(scope, id, props);

    const stage = props.stage;

    // ─────────────────────────────────────────────
    // IMPORT OUTPUTS FROM EXISTING INGESTION STACK
    // ─────────────────────────────────────────────

    // S3 Data Bucket (raw/, processed/adp/, eda_results/, validation/)
    this.dataBucketName = cdk.Fn.importValue('Iso27001BucketName');

    // Step Functions state machine (EDA → Chunking → RAG Validation)
    this.stateMachineArn = cdk.Fn.importValue('Iso27001StateMachineArn');

    // OpenSearch Serverless collection (vector store)
    this.ossCollectionArn = cdk.Fn.importValue('Iso27001OssCollectionArn');
    this.ossCollectionEndpoint = cdk.Fn.importValue('Iso27001OssEndpoint');

    // Bedrock Knowledge Base IAM role
    this.kbRoleArn = cdk.Fn.importValue('Iso27001KbRoleArn');

    // Reference the imported S3 bucket for use in other constructs
    const dataBucket = cdk.aws_s3.Bucket.fromBucketName(
      this,
      'ImportedDataBucket',
      this.dataBucketName
    );

    // ─────────────────────────────────────────────
    // ENVIRONMENT VARIABLES (shared across Lambdas)
    // ─────────────────────────────────────────────

    /**
     * Common environment variables passed to all platform Lambda functions.
     * Individual Lambdas may receive additional variables specific to their role.
     */
    const commonEnvironment: Record<string, string> = {
      STAGE: stage,
      DATA_BUCKET: this.dataBucketName,
      STATE_MACHINE_ARN: this.stateMachineArn,
      OSS_COLLECTION_ARN: this.ossCollectionArn,
      OSS_ENDPOINT: this.ossCollectionEndpoint,
      KB_ROLE_ARN: this.kbRoleArn,
      RAW_PREFIX: 'raw/',
      ADP_OUTPUT_PREFIX: 'processed/adp/',
    };

    // ─────────────────────────────────────────────
    // DYNAMODB TABLES
    // ─────────────────────────────────────────────

    /**
     * Documents Table
     * Stores metadata for uploaded documents.
     * PK: document_id, SK: upload_timestamp (ISO 8601)
     * GSI1: tenant_id (PK) + upload_timestamp (SK) — per-tenant document listing
     * GSI2: status (PK) + upload_timestamp (SK) — filter by processing status
     */
    const documentsTable = new dynamodb.Table(this, 'DocumentsTable', {
      tableName: `${stage}-documents`,
      partitionKey: {
        name: 'document_id',
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: {
        name: 'upload_timestamp',
        type: dynamodb.AttributeType.STRING,
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      pointInTimeRecovery: true,
    });

    documentsTable.addGlobalSecondaryIndex({
      indexName: 'tenant-upload-index',
      partitionKey: {
        name: 'tenant_id',
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: {
        name: 'upload_timestamp',
        type: dynamodb.AttributeType.STRING,
      },
      projectionType: dynamodb.ProjectionType.ALL,
    });

    documentsTable.addGlobalSecondaryIndex({
      indexName: 'status-upload-index',
      partitionKey: {
        name: 'status',
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: {
        name: 'upload_timestamp',
        type: dynamodb.AttributeType.STRING,
      },
      projectionType: dynamodb.ProjectionType.ALL,
    });

    /**
     * Tenants Table
     * Stores tenant (organization) information.
     * PK: tenant_id
     */
    const tenantsTable = new dynamodb.Table(this, 'TenantsTable', {
      tableName: `${stage}-tenants`,
      partitionKey: {
        name: 'tenant_id',
        type: dynamodb.AttributeType.STRING,
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      pointInTimeRecovery: true,
    });

    /**
     * Audits Table
     * Stores audit records (gap analysis, full audits, control reviews).
     * PK: audit_id, SK: created_at (ISO 8601)
     * GSI1: tenant_id (PK) + created_at (SK) — per-tenant audit listing
     */
    const auditsTable = new dynamodb.Table(this, 'AuditsTable', {
      tableName: `${stage}-audits`,
      partitionKey: {
        name: 'audit_id',
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: {
        name: 'created_at',
        type: dynamodb.AttributeType.STRING,
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      pointInTimeRecovery: true,
    });

    auditsTable.addGlobalSecondaryIndex({
      indexName: 'tenant-created-index',
      partitionKey: {
        name: 'tenant_id',
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: {
        name: 'created_at',
        type: dynamodb.AttributeType.STRING,
      },
      projectionType: dynamodb.ProjectionType.ALL,
    });

    /**
     * BDA Output Records Table
     * Stores individual artifacts produced by Bedrock Data Automation,
     * linked to their parent source document for traceability.
     * PK: output_id, SK: created_at (ISO 8601)
     * GSI1: parent_document_id (PK) + created_at (SK) — query outputs by source document
     * GSI2: tenant_id (PK) + created_at (SK) — tenant-scoped listing
     */
    const bdaOutputsTable = new dynamodb.Table(this, 'BdaOutputsTable', {
      tableName: `${stage}-bda-outputs`,
      partitionKey: {
        name: 'output_id',
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: {
        name: 'created_at',
        type: dynamodb.AttributeType.STRING,
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      pointInTimeRecovery: true,
    });

    bdaOutputsTable.addGlobalSecondaryIndex({
      indexName: 'parent-document-index',
      partitionKey: {
        name: 'parent_document_id',
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: {
        name: 'created_at',
        type: dynamodb.AttributeType.STRING,
      },
      projectionType: dynamodb.ProjectionType.ALL,
    });

    bdaOutputsTable.addGlobalSecondaryIndex({
      indexName: 'tenant-created-index',
      partitionKey: {
        name: 'tenant_id',
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: {
        name: 'created_at',
        type: dynamodb.AttributeType.STRING,
      },
      projectionType: dynamodb.ProjectionType.ALL,
    });

    // Add table names to common environment variables
    commonEnvironment['DOCUMENTS_TABLE'] = documentsTable.tableName;
    commonEnvironment['TENANTS_TABLE'] = tenantsTable.tableName;
    commonEnvironment['AUDITS_TABLE'] = auditsTable.tableName;
    commonEnvironment['BDA_OUTPUTS_TABLE'] = bdaOutputsTable.tableName;

    // ─────────────────────────────────────────────
    // COGNITO USER POOL (Authentication)
    // ─────────────────────────────────────────────

    /**
     * Cognito User Pool for platform authentication.
     * Custom attributes:
     *   - custom:role — "Administrator" or "Auditor"
     *   - custom:tenant_id — UUID linking user to their organization
     * Password policy: min 12 chars, uppercase, lowercase, digit, special character.
     * Token validity: access 1 hour, refresh 30 days.
     */
    this.userPool = new cognito.UserPool(this, 'PlatformUserPool', {
      userPoolName: `${stage}-iso27001-platform-users`,
      selfSignUpEnabled: false,
      signInAliases: {
        email: true,
      },
      standardAttributes: {
        email: {
          required: true,
          mutable: true,
        },
      },
      customAttributes: {
        role: new cognito.StringAttribute({
          mutable: true,
        }),
        tenant_id: new cognito.StringAttribute({
          mutable: true,
        }),
      },
      passwordPolicy: {
        minLength: 12,
        requireUppercase: true,
        requireLowercase: true,
        requireDigits: true,
        requireSymbols: true,
      },
      accountRecovery: cognito.AccountRecovery.EMAIL_ONLY,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    /**
     * App Client for the platform frontend.
     * Enables USER_PASSWORD_AUTH (direct login) and ALLOW_REFRESH_TOKEN_AUTH (token refresh).
     * Access token validity: 1 hour.
     * Refresh token validity: 30 days.
     */
    this.userPoolClient = new cognito.UserPoolClient(this, 'PlatformAppClient', {
      userPool: this.userPool,
      userPoolClientName: `${stage}-iso27001-platform-client`,
      authFlows: {
        userPassword: true,
      },
      accessTokenValidity: cdk.Duration.hours(1),
      refreshTokenValidity: cdk.Duration.days(30),
      idTokenValidity: cdk.Duration.hours(1),
      preventUserExistenceErrors: true,
    });

    // Add Cognito identifiers to common environment variables
    commonEnvironment['USER_POOL_ID'] = this.userPool.userPoolId;
    commonEnvironment['USER_POOL_CLIENT_ID'] = this.userPoolClient.userPoolClientId;

    // ─────────────────────────────────────────────
    // CLOUDFRONT CDN + S3 STATIC ASSETS
    // ─────────────────────────────────────────────

    // S3 bucket for frontend static assets (React Native web build)
    this.staticAssetsBucket = new s3.Bucket(this, 'StaticAssetsBucket', {
      bucketName: `iso27001-platform-static-${stage}-${this.account}`,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
    });

    // CloudFront Origin Access Control for secure S3 access
    const oac = new cloudfront.CfnOriginAccessControl(this, 'StaticAssetsOAC', {
      originAccessControlConfig: {
        name: `iso27001-platform-oac-${stage}`,
        originAccessControlOriginType: 's3',
        signingBehavior: 'always',
        signingProtocol: 'sigv4',
        description: 'OAC for platform static assets S3 bucket',
      },
    });

    // CloudFront distribution with HTTPS redirect, 24h cache, and SPA error handling
    this.distribution = new cloudfront.Distribution(this, 'StaticAssetsDistribution', {
      comment: `ISO 27001 Platform Frontend (${stage})`,
      defaultBehavior: {
        origin: origins.S3BucketOrigin.withOriginAccessControl(this.staticAssetsBucket),
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        cachePolicy: new cloudfront.CachePolicy(this, 'StaticAssetsCachePolicy', {
          cachePolicyName: `iso27001-platform-cache-${stage}`,
          comment: '24-hour cache TTL for static frontend assets',
          defaultTtl: cdk.Duration.hours(24),
          minTtl: cdk.Duration.seconds(0),
          maxTtl: cdk.Duration.days(365),
          enableAcceptEncodingGzip: true,
          enableAcceptEncodingBrotli: true,
        }),
        allowedMethods: cloudfront.AllowedMethods.ALLOW_GET_HEAD,
        cachedMethods: cloudfront.CachedMethods.CACHE_GET_HEAD,
      },
      defaultRootObject: 'index.html',
      // Custom error response: 404 → /index.html for SPA client-side routing
      errorResponses: [
        {
          httpStatus: 404,
          responseHttpStatus: 200,
          responsePagePath: '/index.html',
          ttl: cdk.Duration.seconds(0),
        },
        {
          httpStatus: 403,
          responseHttpStatus: 200,
          responsePagePath: '/index.html',
          ttl: cdk.Duration.seconds(0),
        },
      ],
      httpVersion: cloudfront.HttpVersion.HTTP2_AND_3,
      priceClass: cloudfront.PriceClass.PRICE_CLASS_100,
    });

    // ─────────────────────────────────────────────
    // STACK OUTPUTS
    // ─────────────────────────────────────────────

    new cdk.CfnOutput(this, 'PlatformStage', {
      value: stage,
      description: 'Deployment stage for the platform stack',
    });

    new cdk.CfnOutput(this, 'ImportedBucketName', {
      value: this.dataBucketName,
      description: 'Imported S3 data bucket from IngestionStack',
    });

    new cdk.CfnOutput(this, 'ImportedStateMachineArn', {
      value: this.stateMachineArn,
      description: 'Imported Step Functions state machine ARN from IngestionStack',
    });

    new cdk.CfnOutput(this, 'ImportedOssCollectionArn', {
      value: this.ossCollectionArn,
      description: 'Imported OpenSearch Serverless collection ARN from IngestionStack',
    });

    new cdk.CfnOutput(this, 'StaticAssetsBucketName', {
      value: this.staticAssetsBucket.bucketName,
      description: 'S3 bucket for frontend static assets',
      exportName: `Iso27001StaticAssetsBucket-${stage}`,
    });

    new cdk.CfnOutput(this, 'DistributionId', {
      value: this.distribution.distributionId,
      description: 'CloudFront distribution ID (use for cache invalidation)',
      exportName: `Iso27001DistributionId-${stage}`,
    });

    new cdk.CfnOutput(this, 'DistributionDomainName', {
      value: this.distribution.distributionDomainName,
      description: 'CloudFront distribution domain name',
      exportName: `Iso27001DistributionDomain-${stage}`,
    });

    new cdk.CfnOutput(this, 'DocumentsTableName', {
      value: documentsTable.tableName,
      description: 'DynamoDB Documents table name',
      exportName: `${stage}-DocumentsTableName`,
    });

    new cdk.CfnOutput(this, 'TenantsTableName', {
      value: tenantsTable.tableName,
      description: 'DynamoDB Tenants table name',
      exportName: `${stage}-TenantsTableName`,
    });

    new cdk.CfnOutput(this, 'AuditsTableName', {
      value: auditsTable.tableName,
      description: 'DynamoDB Audits table name',
      exportName: `${stage}-AuditsTableName`,
    });

    new cdk.CfnOutput(this, 'BdaOutputsTableName', {
      value: bdaOutputsTable.tableName,
      description: 'DynamoDB BDA Output Records table name',
      exportName: `${stage}-BdaOutputsTableName`,
    });

    new cdk.CfnOutput(this, 'UserPoolId', {
      value: this.userPool.userPoolId,
      description: 'Cognito User Pool ID',
      exportName: `${stage}-UserPoolId`,
    });

    new cdk.CfnOutput(this, 'UserPoolArn', {
      value: this.userPool.userPoolArn,
      description: 'Cognito User Pool ARN',
      exportName: `${stage}-UserPoolArn`,
    });

    new cdk.CfnOutput(this, 'UserPoolClientId', {
      value: this.userPoolClient.userPoolClientId,
      description: 'Cognito User Pool App Client ID',
      exportName: `${stage}-UserPoolClientId`,
    });
  }
}
