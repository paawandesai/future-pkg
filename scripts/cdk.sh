#!/usr/bin/env bash
# Run the CDK CLI for infra/ with every 12-digit number (AWS account ids) masked in its output.
# Usage: scripts/cdk.sh synth|diff|deploy [args...]
set -euo pipefail
cd "$(dirname "$0")/../infra"
export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-${AWS_REGION:-us-east-1}}"
export CDK_DISABLE_VERSION_CHECK=1
pnpm exec cdk "$@" --no-notices --ci 2>&1 | sed -E 's/[0-9]{12}/************/g'
