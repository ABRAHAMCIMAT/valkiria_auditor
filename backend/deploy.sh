#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# ISO 27001 Multi-Agent Audit System — Full Deployment Script
# ─────────────────────────────────────────────────────────────────────────────
#
# Usage:
#   chmod +x deploy.sh
#   ./deploy.sh
#
# Prerequisites:
#   - AWS CLI configured (aws configure)
#   - Node.js 18+ installed
#   - Python 3.12+ installed
#   - CDK CLI: npm install -g aws-cdk@2.200.0
#   - Docker running (agent and Lambda images are built locally for ARM64)
#
# ─────────────────────────────────────────────────────────────────────────────

set -e  # Exit on any error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
REGION="${AWS_REGION:-us-east-1}"

echo "═══════════════════════════════════════════════════════════════════"
echo "  ISO 27001 Multi-Agent Audit System — Deployment"
echo "  Region: $REGION"
echo "  Project: $PROJECT_ROOT"
echo "═══════════════════════════════════════════════════════════════════"

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 1: Prerequisites Verification
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "──── Phase 1: Verifying prerequisites ────"

echo "[1/5] Checking AWS credentials..."
aws sts get-caller-identity --region "$REGION" || {
    echo "ERROR: AWS credentials not configured. Run 'aws configure' first."
    exit 1
}
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "  Account: $ACCOUNT_ID"
echo "  Region:  $REGION"

echo "[2/5] Checking Node.js..."
node --version || { echo "ERROR: Node.js not installed."; exit 1; }

echo "[3/5] Checking Python..."
python --version || python3 --version || { echo "ERROR: Python not installed."; exit 1; }

echo "[4/5] Checking CDK..."
npx cdk --version || { echo "ERROR: CDK not available. Run: npm install -g aws-cdk@2.200.0"; exit 1; }

echo "[5/5] Checking Docker (builds the agent and Lambda images)..."
docker info > /dev/null || { echo "ERROR: Docker is not running."; exit 1; }

echo "✓ All prerequisites verified."

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 2: CDK Bootstrap (if not already done)
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "──── Phase 2: CDK Bootstrap ────"

npx cdk bootstrap "aws://$ACCOUNT_ID/$REGION" || {
    echo "WARNING: CDK bootstrap may have already been done. Continuing..."
}

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 3: Deploy Ingestion Stack
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "──── Phase 3: Deploying Ingestion Stack ────"

cd "$PROJECT_ROOT/actividad1.16/cdk"
npm install --silent
echo "  Synthesizing..."
npx cdk synth --quiet
echo "  Deploying..."
npx cdk deploy --require-approval never

# Capture outputs
BUCKET_NAME=$(aws cloudformation describe-stacks \
    --stack-name IngestionStack \
    --query "Stacks[0].Outputs[?OutputKey=='BucketName'].OutputValue" \
    --output text --region "$REGION" 2>/dev/null || echo "")

echo "  Bucket: $BUCKET_NAME"
echo "✓ Ingestion Stack deployed."

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 4: Upload Knowledge Base Documents (if raw/ is empty)
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "──── Phase 4: Uploading Knowledge Base Documents ────"

if [ -d "$PROJECT_ROOT/knowledge-base" ] && [ -n "$BUCKET_NAME" ]; then
    EXISTING=$(aws s3 ls "s3://$BUCKET_NAME/raw/" --region "$REGION" 2>/dev/null | wc -l)
    if [ "$EXISTING" -lt 5 ]; then
        echo "  Uploading documents to s3://$BUCKET_NAME/raw/..."
        aws s3 sync "$PROJECT_ROOT/knowledge-base/" "s3://$BUCKET_NAME/raw/" \
            --region "$REGION" --quiet
        echo "  ✓ Documents uploaded. Ingestion pipeline will trigger automatically."
        echo "  ⏳ Wait for Step Functions pipeline to complete before Phase 7."
    else
        echo "  Documents already uploaded ($EXISTING files in raw/). Skipping."
    fi
else
    echo "  WARNING: knowledge-base/ directory not found or bucket unknown. Skipping upload."
fi

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 5: Preflight (model access, tool calling, knowledge base)
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "──── Phase 5: Preflight ────"

KB_ID=$(aws bedrock-agent list-knowledge-bases --region "$REGION" \
    --query "knowledgeBaseSummaries[?name=='iso27001-compliance-kb'].knowledgeBaseId" \
    --output text 2>/dev/null || echo "")

if [ -z "$KB_ID" ] || [ "$KB_ID" = "None" ]; then
    echo "ERROR: Knowledge Base iso27001-compliance-kb not found. Wait for the ingestion pipeline and run this again."
    exit 1
fi
echo "  Knowledge Base ID: $KB_ID"

python3 "$SCRIPT_DIR/agentcore/preflight.py" --knowledge-base-id "$KB_ID" --region "$REGION"

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 6: Deploy Frontend and AgentCore (Memory, Runtimes, Gateway)
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "──── Phase 6: Deploying Frontend and AgentCore stacks ────"

cd "$SCRIPT_DIR/cdk"
npm install --silent
npx cdk deploy Iso27001FrontendStack Iso27001AgentCoreStack \
    -c knowledgeBaseId="$KB_ID" --require-approval never --exclusively

stack_output() {
    aws cloudformation describe-stacks --stack-name "$1" --region "$REGION" \
        --query "Stacks[0].Outputs[?OutputKey=='$2'].OutputValue" --output text
}

SITE_URL=$(stack_output Iso27001FrontendStack SiteUrl)
MEMORY_ID=$(stack_output Iso27001AgentCoreStack MemoryId)
echo "  Site:   $SITE_URL"
echo "  Memory: $MEMORY_ID"

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 7: Deploy SAST Pipeline
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "──── Phase 7: Deploying SAST Pipeline stack ────"

cd "$PROJECT_ROOT/deliverables/pipeline/cdk"
npm install --silent
npx cdk deploy -c knowledgeBaseId="$KB_ID" -c allowedOrigin="$SITE_URL" --require-approval never

SAST_UPLOAD_ARN=$(stack_output Iso27001SastPipelineStack UploadLambdaArn)
SAST_RESULTS_BUCKET=$(stack_output Iso27001SastPipelineStack ResultsBucketName)

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 8: Deploy Backend Stack (API, framework Lambdas, site assets)
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "──── Phase 8: Deploying Backend Stack ────"

cd "$SCRIPT_DIR/cdk"
npx cdk deploy Iso27001BackendStack --exclusively \
    -c knowledgeBaseId="$KB_ID" \
    -c sastUploadFunctionArn="$SAST_UPLOAD_ARN" \
    -c sastResultsBucketName="$SAST_RESULTS_BUCKET" \
    --require-approval never

API_ENDPOINT=$(stack_output Iso27001BackendStack ApiEndpoint)
echo "  ✓ API Endpoint: $API_ENDPOINT"

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 9: Deploy CloudWatch Alarms
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "──── Phase 9: Creating CloudWatch Alarms ────"

cd "$SCRIPT_DIR"
python -c "
from backend.observability.alerts import AlertManager
manager = AlertManager(region='$REGION')
manager.create_all_alarms()
print('  ✓ All CloudWatch alarms created.')
" 2>/dev/null || echo "  WARNING: Could not create alarms (import error). Deploy handles this via CDK."

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 10: Validation
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "──── Phase 10: Validation ────"

# Audits require a signed-in user: an anonymous call must be rejected
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "${API_ENDPOINT}auditorias" --max-time 30 || echo "timeout")
if [ "$RESPONSE" = "401" ]; then
    echo "  ✓ API rejects anonymous requests (HTTP 401)"
else
    echo "  ERROR: anonymous request returned HTTP $RESPONSE, expected 401"
    exit 1
fi

# Verify S3 metrics prefix exists
if [ -n "$BUCKET_NAME" ]; then
    echo "  Checking S3 metrics prefix..."
    aws s3api head-object --bucket "$BUCKET_NAME" --key "metrics/" --region "$REGION" 2>/dev/null || \
    aws s3api put-object --bucket "$BUCKET_NAME" --key "metrics/" --region "$REGION" --no-cli-pager > /dev/null 2>&1
    echo "  ✓ S3 metrics prefix ready."
fi

# ─────────────────────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "  DEPLOYMENT COMPLETE"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "  Resources:"
echo "    API Endpoint:     ${API_ENDPOINT:-'(check CloudFormation outputs)'}"
echo "    S3 Bucket:        ${BUCKET_NAME:-'(check CloudFormation outputs)'}"
echo "    Knowledge Base:   ${KB_ID}"
echo "    Memory ID:        ${MEMORY_ID:-'(check AgentCore stack outputs)'}"
echo "    Region:           $REGION"
echo ""
echo "  Site:             ${SITE_URL}"
echo ""
echo "  Metrics stored at:"
echo "    s3://$BUCKET_NAME/metrics/"
echo ""
echo "  CloudWatch Dashboard:"
echo "    ISO27001-Backend-Overview"
echo ""
echo "  Next steps:"
echo "    1. Subscribe to SNS topic for alerts:"
echo "       aws sns subscribe --topic-arn <AlertsTopicArn> --protocol email --notification-endpoint your@email.com"
echo "    2. Create a user in the Cognito pool, assign it a group (its tenant) and sign in"
echo "    3. Run the end-to-end test (real audit, real cost): backend/tests/e2e/test_deployed_audit.py"
echo ""
echo "═══════════════════════════════════════════════════════════════════"
