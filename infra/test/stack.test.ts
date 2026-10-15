// Guardrails the deployed stack must keep. Run: pnpm --filter infra test
import assert from "node:assert/strict";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import { App } from "aws-cdk-lib";
import { Match, Template } from "aws-cdk-lib/assertions";
import { DemoStack } from "../lib/stack.ts";

const dir = (name: string) => {
  const d = mkdtempSync(join(tmpdir(), name));
  writeFileSync(join(d, "placeholder.txt"), "x");
  return d;
};
const stack = new DemoStack(new App(), "Test", {
  env: { account: "111111111111", region: "us-east-1" },
  lambdaDir: dir("lambda"),
  webDir: dir("web"),
  modelFast: "fast",
  modelMain: "main",
});
const t = Template.fromStack(stack);
const json = JSON.stringify(t.toJSON());

test("the API runs with Cognito auth, never mock", () => {
  const fns = t.findResources("AWS::Lambda::Function", {
    Properties: { Environment: { Variables: { PLAN_TABLE: Match.anyValue() } } },
  });
  const envs = Object.values(fns).map((f) => f.Properties.Environment.Variables);
  const api = envs.find((e) => "AUTH_MODE" in e);
  assert.ok(api, "API function not found");
  assert.equal(api.AUTH_MODE, "cognito");
  assert.ok(!json.includes('"AUTH_MODE":"mock"'));
});

test("sign-up is closed and coaches can't write their coach id", () => {
  t.hasResourceProperties("AWS::Cognito::UserPool", {
    AdminCreateUserConfig: { AllowAdminCreateUserOnly: true },
  });
  const clients = Object.values(t.findResources("AWS::Cognito::UserPoolClient"));
  assert.equal(clients.length, 1);
  const write: string[] = clients[0].Properties.WriteAttributes;
  assert.ok(!write.some((a) => a.includes("coach_id")), "coach_id must not be client-writable");
  assert.ok(clients[0].Properties.ReadAttributes.includes("custom:coach_id"));
});

test("no secret value or API key in the template; the function gets only the secret's name", () => {
  assert.ok(!/ANTHROPIC_FUTURE_API_KEY/.test(json));
  assert.ok(!/sk-ant-/.test(json));
  t.hasResourceProperties("AWS::SecretsManager::Secret", { Name: "future-pkg/anthropic-api-key" });
  const outputs = JSON.stringify(t.toJSON().Outputs);
  assert.ok(!/111111111111/.test(outputs), "outputs must not carry the account id");
});

test("every response from CloudFront carries noindex", () => {
  t.hasResourceProperties("AWS::CloudFront::ResponseHeadersPolicy", {
    ResponseHeadersPolicyConfig: {
      CustomHeadersConfig: {
        Items: [Match.objectLike({ Header: "X-Robots-Tag", Value: Match.stringLikeRegexp("noindex") })],
      },
    },
  });
  const dist = Object.values(t.findResources("AWS::CloudFront::Distribution"))[0].Properties.DistributionConfig;
  for (const b of [dist.DefaultCacheBehavior, ...dist.CacheBehaviors]) assert.ok(b.ResponseHeadersPolicyId);
});

test("plans expire and are purged on a schedule", () => {
  t.hasResourceProperties("AWS::DynamoDB::Table", {
    TimeToLiveSpecification: { AttributeName: "expires_at", Enabled: true },
  });
  t.hasResourceProperties("AWS::Events::Rule", { ScheduleExpression: "rate(1 day)" });
});

test("the site bucket is private", () => {
  t.hasResourceProperties("AWS::S3::Bucket", {
    PublicAccessBlockConfiguration: {
      BlockPublicAcls: true,
      BlockPublicPolicy: true,
      IgnorePublicAcls: true,
      RestrictPublicBuckets: true,
    },
  });
});
