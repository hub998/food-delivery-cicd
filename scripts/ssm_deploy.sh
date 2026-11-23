#!/usr/bin/env bash
# Runs in GitHub Actions. Tells the EC2 server (through AWS Systems Manager, no SSH needed)
# to download the LATEST build from S3 and deploy it. Fails the pipeline if the deploy fails.
set -euo pipefail
: "${S3_BUCKET:?}" "${EC2_INSTANCE_ID:?}" "${AWS_REGION:?}"

cat > /tmp/ssm-params.json <<JSON
{"commands": [
  "set -euo pipefail",
  "KEY=\$(aws s3 cp s3://${S3_BUCKET}/latest.txt - --region ${AWS_REGION})",
  "echo Latest build in S3: \$KEY",
  "rm -rf /tmp/build /tmp/build.zip && mkdir /tmp/build",
  "aws s3 cp s3://${S3_BUCKET}/\$KEY /tmp/build.zip --region ${AWS_REGION}",
  "unzip -q /tmp/build.zip -d /tmp/build",
  "bash /tmp/build/deploy/deploy.sh"
]}
JSON

CMD_ID=$(aws ssm send-command \
  --region "$AWS_REGION" \
  --instance-ids "$EC2_INSTANCE_ID" \
  --document-name "AWS-RunShellScript" \
  --comment "Deploy latest build from S3" \
  --parameters file:///tmp/ssm-params.json \
  --query "Command.CommandId" --output text)
echo "SSM command: $CMD_ID"

# Wait for the command to finish (the wait command exits non-zero if it fails; we read the status ourselves)
aws ssm wait command-executed --region "$AWS_REGION" --command-id "$CMD_ID" --instance-id "$EC2_INSTANCE_ID" || true

STATUS=$(aws ssm get-command-invocation --region "$AWS_REGION" --command-id "$CMD_ID" --instance-id "$EC2_INSTANCE_ID" --query Status --output text)
echo "----- server output -----"
aws ssm get-command-invocation --region "$AWS_REGION" --command-id "$CMD_ID" --instance-id "$EC2_INSTANCE_ID" --query StandardOutputContent --output text
aws ssm get-command-invocation --region "$AWS_REGION" --command-id "$CMD_ID" --instance-id "$EC2_INSTANCE_ID" --query StandardErrorContent --output text
echo "-------------------------"
echo "Deployment status: $STATUS"
[ "$STATUS" = "Success" ]
