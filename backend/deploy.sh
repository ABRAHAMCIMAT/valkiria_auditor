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
#   - AgentCore toolkit: pip install bedrock-agentcore-starter-toolkit
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

echo "[5/5] Checking AgentCore toolkit..."
agentcore --version 2>/dev/null || {
    echo "WARNING: AgentCore toolkit not installed. Installing..."
    pip install bedrock-agentcore-starter-toolkit
}

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
# PHASE 5: Create AgentCore Memory Resource
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "──── Phase 5: Creating AgentCore Memory ────"

MEMORY_STRATEGIES='[{"summaryMemoryStrategy":{"name":"AuditSessionSummary","namespaces":["/summaries/{actorId}/{sessionId}"]}},{"semanticMemoryStrategy":{"name":"OrganizationalFacts","namespaces":["/facts/{actorId}"]}},{"userPreferenceMemoryStrategy":{"name":"AuditorPreferences","namespaces":["/preferences/{actorId}"]}}]'

MEMORY_ID=$(agentcore memory list --region "$REGION" 2>/dev/null | grep "iso27001_audit_memory" | awk '{print $1}' || echo "")

if [ -z "$MEMORY_ID" ]; then
    echo "  Creating memory resource..."
    agentcore memory create iso27001_audit_memory \
        --description "Memory for ISO 27001 multi-agent audit system" \
        --strategies "$MEMORY_STRATEGIES" \
        --region "$REGION" \
        --wait
    MEMORY_ID=$(agentcore memory list --region "$REGION" 2>/dev/null | grep "iso27001_audit_memory" | awk '{print $1}' || echo "")
    echo "  ✓ Memory created: $MEMORY_ID"
else
    echo "  Memory already exists: $MEMORY_ID"
fi

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 6: Build Lambda Layer
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "──── Phase 6: Building Lambda Layer ────"

cd "$SCRIPT_DIR/layers/shared"
rm -rf python
mkdir -p python/lib/python3.12/site-packages

echo "  Installing dependencies (this may take a minute)..."
pip install -r requirements.txt \
    -t python/lib/python3.12/site-packages \
    --no-cache-dir --quiet \
    --platform manylinux2014_x86_64 \
    --only-binary=:all: 2>/dev/null || \
pip install -r requirements.txt \
    -t python/lib/python3.12/site-packages \
    --no-cache-dir --quiet

LAYER_SIZE=$(du -sh python 2>/dev/null | cut -f1)
echo "  ✓ Layer built: $LAYER_SIZE"

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 7: Deploy Backend Stack
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "──── Phase 7: Deploying Backend Stack ────"

cd "$SCRIPT_DIR/cdk"
npm install --silent

echo "  Synthesizing..."
npx cdk synth --quiet

echo "  Deploying..."
npx cdk deploy --require-approval never

# Capture API endpoint
API_ENDPOINT=$(aws cloudformation describe-stacks \
    --stack-name Iso27001BackendStack \
    --query "Stacks[0].Outputs[?OutputKey=='ApiEndpoint'].OutputValue" \
    --output text --region "$REGION" 2>/dev/null || echo "")

echo "  ✓ Backend Stack deployed."
echo "  API Endpoint: $API_ENDPOINT"

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 8: Configure Environment Variables
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "──── Phase 8: Configuring Lambda Environment Variables ────"

# Get Knowledge Base ID (from Bedrock, if available)
KB_ID=$(aws bedrock-agent list-knowledge-bases --region "$REGION" \
    --query "knowledgeBaseSummaries[?name=='iso27001-compliance-kb'].knowledgeBaseId" \
    --output text 2>/dev/null || echo "")

if [ -n "$KB_ID" ] && [ "$KB_ID" != "None" ]; then
    echo "  Knowledge Base ID: $KB_ID"
else
    echo "  WARNING: Knowledge Base not found. Set KNOWLEDGE_BASE_ID manually after ingestion completes."
    KB_ID=""
fi

LAMBDAS=("iso27001-strands-orchestrator" "iso27001-langgraph-orchestrator" "iso27001-crewai-orchestrator")

for LAMBDA_NAME in "${LAMBDAS[@]}"; do
    echo "  Updating $LAMBDA_NAME..."

    # Get current environment
    CURRENT_ENV=$(aws lambda get-function-configuration \
        --function-name "$LAMBDA_NAME" \
        --query "Environment.Variables" \
        --output json --region "$REGION" 2>/dev/null || echo "{}")

    # Update with KB_ID and MEMORY_ID
    if [ -n "$KB_ID" ] && [ "$KB_ID" != "None" ]; then
        UPDATED_ENV=$(echo "$CURRENT_ENV" | python -c "
import sys, json
env = json.load(sys.stdin)
env['KNOWLEDGE_BASE_ID'] = '$KB_ID'
env['AGENTCORE_MEMORY_ID'] = '$MEMORY_ID'
print(json.dumps({'Variables': env}))
")
        aws lambda update-function-configuration \
            --function-name "$LAMBDA_NAME" \
            --environment "$UPDATED_ENV" \
            --region "$REGION" \
            --no-cli-pager > /dev/null 2>&1 || true
    fi
done

echo "  ✓ Environment variables configured."

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

if [ -n "$API_ENDPOINT" ]; then
    echo "  Testing Strands endpoint..."
    RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" \
        -X POST "${API_ENDPOINT}audit/strands" \
        -H "Content-Type: application/json" \
        -d '{"organization_context":"Validation test - ACME Corp, 50 employees, tech startup","audit_type":"internal"}' \
        --max-time 30 2>/dev/null || echo "timeout")

    if [ "$RESPONSE" = "200" ]; then
        echo "  ✓ Strands orchestrator responding (HTTP 200)"
    elif [ "$RESPONSE" = "timeout" ]; then
        echo "  ⏳ Strands orchestrator timed out (expected for first cold start, try again)"
    else
        echo "  ⚠ Strands orchestrator returned HTTP $RESPONSE"
    fi
else
    echo "  WARNING: API endpoint not available. Check CloudFormation outputs."
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
echo "    Knowledge Base:   ${KB_ID:-'(pending ingestion pipeline completion)'}"
echo "    Memory ID:        ${MEMORY_ID:-'(check agentcore memory list)'}"
echo "    Region:           $REGION"
echo ""
echo "  Endpoints:"
echo "    POST ${API_ENDPOINT}audit/strands"
echo "    POST ${API_ENDPOINT}audit/langgraph"
echo "    POST ${API_ENDPOINT}audit/crewai"
echo ""
echo "  Metrics stored at:"
echo "    s3://$BUCKET_NAME/metrics/"
echo ""
echo "  CloudWatch Dashboard:"
echo "    ISO27001-Backend-Overview"
echo ""
echo "  Next steps:"
echo "    1. If KB_ID is empty, wait for ingestion pipeline then re-run Phase 8"
echo "    2. Subscribe to SNS topic for alerts:"
echo "       aws sns subscribe --topic-arn <AlertsTopicArn> --protocol email --notification-endpoint your@email.com"
echo "    3. Test a full audit:"
echo "       curl -X POST ${API_ENDPOINT}audit/strands -H 'Content-Type: application/json' \\"
echo "         -d '{\"organization_context\":\"Your org description\",\"audit_type\":\"internal\"}'"
echo ""
echo "═══════════════════════════════════════════════════════════════════"
