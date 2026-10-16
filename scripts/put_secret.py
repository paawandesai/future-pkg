"""Put ANTHROPIC_FUTURE_API_KEY from the environment into the stack's Secrets Manager secret.

The value is read from the environment and sent only to Secrets Manager; it is never printed,
logged, written to disk or passed on a command line. Prints a single confirmation line.
"""

import os
import sys

import boto3

SECRET_ID = "future-pkg/anthropic-api-key"

key = os.environ.get("ANTHROPIC_FUTURE_API_KEY", "")
if not key:
    sys.exit("ANTHROPIC_FUTURE_API_KEY is not set")
region = os.environ.get("AWS_DEFAULT_REGION") or os.environ.get("AWS_REGION") or "us-east-1"
boto3.client("secretsmanager", region_name=region).put_secret_value(SecretId=SECRET_ID, SecretString=key)
print(f"updated {SECRET_ID}")
