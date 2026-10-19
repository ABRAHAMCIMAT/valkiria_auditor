#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { SastPipelineStack } from '../lib/sast-pipeline-stack';

const app = new cdk.App();

new SastPipelineStack(app, 'Iso27001SastPipelineStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION || 'us-west-2',
  },
  description: 'ISO 27001 SAST Pipeline — CodePipeline triggered by S3 .zip upload',
});
