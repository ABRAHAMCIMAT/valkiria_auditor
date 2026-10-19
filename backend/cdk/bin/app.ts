#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { FrontendStack } from '../lib/frontend-stack';
import { BackendStack } from '../lib/backend-stack';

const app = new cdk.App();

new FrontendStack(app, 'Iso27001FrontendStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION || 'us-east-1',
  },
  tags: {
    project: 'iso27001-audit',
    environment: 'production',
    team: 'team-16',
  },
});

new BackendStack(app, 'Iso27001BackendStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION || 'us-east-1',
  },
  tags: {
    project: 'iso27001-audit',
    environment: 'production',
    team: 'team-16',
  },
});
