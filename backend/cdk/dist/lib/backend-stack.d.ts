import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
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
export declare class BackendStack extends cdk.Stack {
    constructor(scope: Construct, id: string, props?: cdk.StackProps);
}
