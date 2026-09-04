#!/bin/bash
# ─── Runbook Demo Infrastructure Deployment ───
# This script deploys the full demo stack to AWS
#
# Prerequisites:
#   - AWS CLI configured with credentials
#   - An EC2 Key Pair created in your region
#   - A Discord Webhook URL (from channel settings → Integrations → Webhooks)
#
# Usage:
#   ./deploy.sh <key-pair-name> <discord-webhook-url>

set -e

STACK_NAME="runbook-demo"
REGION="${AWS_REGION:-us-east-1}"
TEMPLATE_FILE="$(dirname "$0")/cloudformation.yaml"

# Check arguments
if [ $# -lt 2 ]; then
    echo "Usage: ./deploy.sh <key-pair-name> <discord-webhook-url>"
    echo ""
    echo "  key-pair-name:      Name of an existing EC2 Key Pair in $REGION"
    echo "  discord-webhook-url: Discord channel webhook URL"
    echo ""
    echo "Example:"
    echo "  ./deploy.sh my-key-pair https://discord.com/api/webhooks/123/abc"
    exit 1
fi

KEY_PAIR="$1"
DISCORD_WEBHOOK="$2"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Runbook Demo - AWS Deployment"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Stack Name:    $STACK_NAME"
echo "Region:        $REGION"
echo "Key Pair:      $KEY_PAIR"
echo "Template:      $TEMPLATE_FILE"
echo ""

# Deploy CloudFormation stack
echo "→ Deploying CloudFormation stack..."
aws cloudformation deploy \
    --template-file "$TEMPLATE_FILE" \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --capabilities CAPABILITY_NAMED_IAM \
    --parameter-overrides \
        KeyPairName="$KEY_PAIR" \
        DiscordWebhookUrl="$DISCORD_WEBHOOK" \
    --no-fail-on-empty-changeset

echo ""
echo "→ Waiting for stack to complete..."
aws cloudformation wait stack-create-complete --stack-name "$STACK_NAME" --region "$REGION" 2>/dev/null || true

# Get outputs
echo ""
echo "→ Fetching stack outputs..."
OUTPUTS=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" --query "Stacks[0].Outputs" --output json)

INSTANCE_IP=$(echo "$OUTPUTS" | python3 -c "import sys,json; [print(o['OutputValue']) for o in json.load(sys.stdin) if o['OutputKey']=='InstancePublicIP']")
INSTANCE_ID=$(echo "$OUTPUTS" | python3 -c "import sys,json; [print(o['OutputValue']) for o in json.load(sys.stdin) if o['OutputKey']=='InstanceId']")
APP_URL=$(echo "$OUTPUTS" | python3 -c "import sys,json; [print(o['OutputValue']) for o in json.load(sys.stdin) if o['OutputKey']=='LoginAppURL']")

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✓ Deployment Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  Login App:   $APP_URL"
echo "  Instance:    $INSTANCE_ID ($INSTANCE_IP)"
echo ""
echo "  SSH:         ssh -i ~/.ssh/$KEY_PAIR.pem ec2-user@$INSTANCE_IP"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Demo Triggers (run via SSH):"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  1. Trigger 500 errors:"
echo "     for i in {1..5}; do curl -s -X POST http://localhost:3000/api/auth/login -H 'Content-Type: application/json' -d '{\"username\":\"test\",\"password\":\"test\"}'; done"
echo ""
echo "  2. Trigger high CPU:"
echo "     stress --cpu 2 --timeout 360"
echo ""
echo "  3. Trigger disk full:"
echo "     dd if=/dev/zero of=/tmp/fillfile bs=1M count=7000"
echo ""
echo "  4. Trigger instance down:"
echo "     sudo systemctl stop login-app"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
