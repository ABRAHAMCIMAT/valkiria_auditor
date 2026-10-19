import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as s3deploy from 'aws-cdk-lib/aws-s3-deployment';
import * as cloudfront from 'aws-cdk-lib/aws-cloudfront';
import * as origins from 'aws-cdk-lib/aws-cloudfront-origins';
import * as cognito from 'aws-cdk-lib/aws-cognito';
import * as path from 'path';

/**
 * FrontendStack — Deploys:
 * - S3 bucket for static frontend assets
 * - CloudFront CDN distribution
 * - Cognito User Pool with admin and user1
 */
export class FrontendStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // ─────────────────────────────────────────────────────────────────
    // 1. S3 BUCKET — Frontend hosting
    // ─────────────────────────────────────────────────────────────────
    const websiteBucket = new s3.Bucket(this, 'FrontendBucket', {
      bucketName: `iso27001-frontend-${this.account}`,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
    });

    // ─────────────────────────────────────────────────────────────────
    // 2. CLOUDFRONT — CDN Distribution
    // ─────────────────────────────────────────────────────────────────
    const oai = new cloudfront.OriginAccessIdentity(this, 'OAI', {
      comment: 'ISO 27001 Auditor Lead Frontend',
    });

    websiteBucket.grantRead(oai);

    const distribution = new cloudfront.Distribution(this, 'FrontendDistribution', {
      defaultBehavior: {
        origin: new origins.S3Origin(websiteBucket, {
          originAccessIdentity: oai,
        }),
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        cachePolicy: cloudfront.CachePolicy.CACHING_OPTIMIZED,
      },
      defaultRootObject: 'index.html',
      errorResponses: [
        {
          httpStatus: 403,
          responseHttpStatus: 200,
          responsePagePath: '/index.html',
          ttl: cdk.Duration.minutes(5),
        },
        {
          httpStatus: 404,
          responseHttpStatus: 200,
          responsePagePath: '/index.html',
          ttl: cdk.Duration.minutes(5),
        },
      ],
      comment: 'Auditor Lead - ISO 27001 Frontend',
    });

    // ─────────────────────────────────────────────────────────────────
    // 3. S3 DEPLOYMENT — Upload frontend files
    // ─────────────────────────────────────────────────────────────────
    new s3deploy.BucketDeployment(this, 'DeployFrontend', {
      sources: [s3deploy.Source.asset(path.join(__dirname, '../../../frontend'), {
        exclude: ['assets/diagrams/*', 'assets/images/security_banner.jpg'],
      })],
      destinationBucket: websiteBucket,
      distribution: distribution,
      distributionPaths: ['/*'],
      memoryLimit: 512,
    });

    // ─────────────────────────────────────────────────────────────────
    // 4. COGNITO — User Pool + Users
    // ─────────────────────────────────────────────────────────────────
    const userPool = new cognito.UserPool(this, 'AuditUserPool', {
      userPoolName: 'iso27001-auditor-lead-users',
      selfSignUpEnabled: false,
      signInAliases: { username: true, email: true },
      passwordPolicy: {
        minLength: 8,
        requireLowercase: false,
        requireUppercase: false,
        requireDigits: false,
        requireSymbols: false,
      },
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    const userPoolClient = new cognito.UserPoolClient(this, 'AuditUserPoolClient', {
      userPool: userPool,
      userPoolClientName: 'auditor-lead-web-client',
      authFlows: {
        userPassword: true,
        userSrp: true,
      },
      preventUserExistenceErrors: true,
    });

    // Create users via CfnUserPoolUser
    const adminUser = new cognito.CfnUserPoolUser(this, 'AdminUser', {
      userPoolId: userPool.userPoolId,
      username: 'admin',
      userAttributes: [
        { name: 'email', value: 'admin@auditorlead.local' },
        { name: 'email_verified', value: 'true' },
      ],
      messageAction: 'SUPPRESS',
    });

    const user1 = new cognito.CfnUserPoolUser(this, 'User1', {
      userPoolId: userPool.userPoolId,
      username: 'user1',
      userAttributes: [
        { name: 'email', value: 'user1@auditorlead.local' },
        { name: 'email_verified', value: 'true' },
      ],
      messageAction: 'SUPPRESS',
    });

    // ─────────────────────────────────────────────────────────────────
    // 5. OUTPUTS
    // ─────────────────────────────────────────────────────────────────
    new cdk.CfnOutput(this, 'SiteUrl', {
      value: `https://${distribution.distributionDomainName}`,
      description: 'Auditor Lead website URL (CloudFront)',
    });

    new cdk.CfnOutput(this, 'DistributionId', {
      value: distribution.distributionId,
      description: 'CloudFront distribution ID',
    });

    new cdk.CfnOutput(this, 'BucketName', {
      value: websiteBucket.bucketName,
      description: 'S3 bucket for frontend assets',
    });

    new cdk.CfnOutput(this, 'UserPoolId', {
      value: userPool.userPoolId,
      description: 'Cognito User Pool ID',
    });

    new cdk.CfnOutput(this, 'UserPoolClientId', {
      value: userPoolClient.userPoolClientId,
      description: 'Cognito User Pool Client ID',
    });
  }
}
