import * as cdk from 'aws-cdk-lib';
import * as cognito from 'aws-cdk-lib/aws-cognito';
import { Construct } from 'constructs';

/**
 * Properties for the CognitoAuth construct.
 */
export interface CognitoAuthProps {
  /**
   * Optional prefix for resource naming.
   * @default 'audit-platform'
   */
  readonly resourcePrefix?: string;
}

/**
 * CognitoAuth construct — defines the Cognito User Pool, custom attributes,
 * password policy, and App Client for the fullstack audit platform.
 *
 * Custom attributes:
 * - custom:role — "Administrator" or "Auditor"
 * - custom:tenant_id — UUID linking user to their organization
 *
 * Validates Requirements: 1.1, 1.4, 3.4, 12.1
 */
export class CognitoAuth extends Construct {
  /** The Cognito User Pool */
  public readonly userPool: cognito.UserPool;

  /** The App Client for frontend authentication */
  public readonly userPoolClient: cognito.UserPoolClient;

  constructor(scope: Construct, id: string, props?: CognitoAuthProps) {
    super(scope, id);

    const prefix = props?.resourcePrefix ?? 'audit-platform';

    // --- User Pool ---
    this.userPool = new cognito.UserPool(this, 'UserPool', {
      userPoolName: `${prefix}-user-pool`,

      // Sign-in configuration: email as the primary identifier
      signInAliases: {
        email: true,
      },

      // Self-sign-up disabled — administrators create users
      selfSignUpEnabled: false,

      // Password policy: min 12 chars, uppercase, lowercase, digit, special character
      // Validates Requirement 1.4
      passwordPolicy: {
        minLength: 12,
        requireUppercase: true,
        requireLowercase: true,
        requireDigits: true,
        requireSymbols: true,
      },

      // Account recovery via email
      accountRecovery: cognito.AccountRecovery.EMAIL_ONLY,

      // Standard attributes
      standardAttributes: {
        email: {
          required: true,
          mutable: true,
        },
      },

      // Custom attributes for role-based access and multi-tenancy
      // Validates Requirements 3.4, 12.1
      customAttributes: {
        'role': new cognito.StringAttribute({
          mutable: true,
          minLen: 1,
          maxLen: 50,
        }),
        'tenant_id': new cognito.StringAttribute({
          mutable: true,
          minLen: 1,
          maxLen: 36, // UUID length
        }),
      },

      // Removal policy for dev/staging — retain in production
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // --- App Client ---
    // Validates Requirement 1.1 (token issuance)
    this.userPoolClient = this.userPool.addClient('AppClient', {
      userPoolClientName: `${prefix}-app-client`,

      // Auth flows: USER_PASSWORD_AUTH for direct login, ALLOW_REFRESH_TOKEN_AUTH for token refresh
      authFlows: {
        userPassword: true,       // USER_PASSWORD_AUTH
        userSrp: false,           // Disable SRP (not needed for this use case)
      },

      // Token validity configuration
      accessTokenValidity: cdk.Duration.hours(1),    // Access token: 1 hour
      refreshTokenValidity: cdk.Duration.days(30),   // Refresh token: 30 days
      idTokenValidity: cdk.Duration.hours(1),        // ID token: 1 hour (matches access)

      // Prevent user existence errors from leaking information
      preventUserExistenceErrors: true,

      // No OAuth flows needed — using direct Cognito API auth
      oAuth: {
        flows: {
          implicitCodeGrant: false,
          authorizationCodeGrant: false,
        },
      },
    });

    // --- Outputs ---
    new cdk.CfnOutput(this, 'UserPoolId', {
      value: this.userPool.userPoolId,
      description: 'Cognito User Pool ID',
      exportName: `${prefix}-user-pool-id`,
    });

    new cdk.CfnOutput(this, 'UserPoolArn', {
      value: this.userPool.userPoolArn,
      description: 'Cognito User Pool ARN',
      exportName: `${prefix}-user-pool-arn`,
    });

    new cdk.CfnOutput(this, 'AppClientId', {
      value: this.userPoolClient.userPoolClientId,
      description: 'Cognito App Client ID',
      exportName: `${prefix}-app-client-id`,
    });
  }
}
