import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
/**
 * FrontendStack — Deploys:
 * - S3 bucket for static frontend assets
 * - CloudFront CDN distribution
 * - Cognito User Pool with admin and user1
 */
export declare class FrontendStack extends cdk.Stack {
    constructor(scope: Construct, id: string, props?: cdk.StackProps);
}
