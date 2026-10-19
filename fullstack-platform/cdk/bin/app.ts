#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { PlatformStack } from '../lib/platform-stack';

const app = new cdk.App();

const stage = app.node.tryGetContext('stage') || 'dev';

new PlatformStack(app, `Iso27001PlatformStack-${stage}`, {
  stage,
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION || 'us-east-1',
  },
  description: `ISO 27001 Fullstack Audit Platform (${stage})`,
});
