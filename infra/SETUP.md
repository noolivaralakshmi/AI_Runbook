# Runbook Demo - AWS Infrastructure Setup

## Prerequisites

1. **AWS CLI** configured with credentials (`aws configure`)
2. **EC2 Key Pair** created in your region
3. **Discord Webhook URL** — from your Discord channel:
   - Channel Settings → Integrations → Webhooks → New Webhook → Copy URL

## One-Command Deploy

```bash
cd infra
./deploy.sh <your-key-pair-name> <your-discord-webhook-url>
```

Example:
```bash
./deploy.sh runbook-demo-key https://discord.com/api/webhooks/1234567890/abcdef
```

## What Gets Created

| Resource | Purpose |
|----------|---------|
| EC2 (t2.micro) | Runs the login app on port 3000 |
| CloudWatch Agent | Collects CPU, disk, memory metrics + app logs |
| SNS Topic | Receives CloudWatch alarm notifications |
| Lambda Function | Forwards SNS alarms to Discord as `!incident` messages |
| CloudWatch Alarms | Monitors 4 conditions (see below) |

## CloudWatch Alarms

| Alarm | Trigger | What Happens |
|-------|---------|--------------|
| `runbook-demo-500-errors` | 3+ app errors in 1 minute | Posts 500 error incident to Discord |
| `runbook-demo-high-cpu` | CPU > 80% for 5 minutes | Posts CPU alarm to Discord |
| `runbook-demo-disk-full` | Disk > 85% used | Posts disk alarm to Discord |
| `runbook-demo-instance-down` | EC2 status check fails | Posts server down incident to Discord |

## Demo Flow

```
CloudWatch detects problem
    → Alarm triggers
        → SNS notification
            → Lambda posts "!incident ..." to Discord
                → Runbook bot picks it up
                    → AI Pipeline runs (diagnosis + remediation)
                        → GitHub Issue + PR created
```

## Trigger Demo Scenarios

SSH into the instance:
```bash
ssh -i ~/.ssh/your-key.pem ec2-user@<instance-ip>
```

### Scenario 1: 500 Errors (triggers app error alarm)
```bash
for i in {1..5}; do
  curl -s -X POST http://localhost:3000/api/auth/login \
    -H 'Content-Type: application/json' \
    -d '{"username":"test","password":"test"}'
done
```

### Scenario 2: High CPU (triggers CPU alarm)
```bash
sudo yum install -y stress
stress --cpu 2 --timeout 360
```

### Scenario 3: Disk Full (triggers disk alarm)
```bash
dd if=/dev/zero of=/tmp/fillfile bs=1M count=7000
# Clean up after demo: rm /tmp/fillfile
```

### Scenario 4: App Down (triggers status check)
```bash
sudo systemctl stop login-app
# Restart after demo: sudo systemctl start login-app
```

## Cleanup

Delete everything when done:
```bash
aws cloudformation delete-stack --stack-name runbook-demo --region us-east-1
```

## Cost

- EC2 t2.micro: **Free tier** (750 hours/month for 12 months)
- CloudWatch: Free tier includes 10 alarms, 5GB logs
- Lambda: Free tier includes 1M requests/month
- SNS: Free tier includes 1M publishes/month

**Estimated cost: $0** (within free tier limits)
