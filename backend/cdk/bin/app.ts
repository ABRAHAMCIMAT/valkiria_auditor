#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { FrontendStack } from '../lib/frontend-stack';
import { BackendStack } from '../lib/backend-stack';
import { AgentCoreStack } from '../lib/agentcore-stack';

const app = new cdk.App();

const env = {
  account: process.env.CDK_DEFAULT_ACCOUNT,
  region: process.env.CDK_DEFAULT_REGION || 'us-east-1',
};
const tags = {
  project: 'iso27001-audit',
  environment: 'production',
  team: 'team-16',
};

const frontend = new FrontendStack(app, 'Iso27001FrontendStack', { env, tags });

const agentCore = new AgentCoreStack(app, 'Iso27001AgentCoreStack', {
  env,
  tags,
  allowedOrigin: `https://${frontend.distribution.distributionDomainName}`,
});

// The SAST stack is a separate CDK app: pass its outputs to expose it in this API
new BackendStack(app, 'Iso27001BackendStack', {
  env,
  tags,
  userPool: frontend.userPool,
  userPoolClient: frontend.userPoolClient,
  siteBucket: frontend.siteBucket,
  distribution: frontend.distribution,
  auditsTable: agentCore.auditsTable,
  dataBucket: agentCore.dataBucket,
  orchestratorRuntimeArn: agentCore.orchestratorRuntimeArn,
  sastUploadFunctionArn: app.node.tryGetContext('sastUploadFunctionArn'),
  sastResultsBucketName: app.node.tryGetContext('sastResultsBucketName'),
});
