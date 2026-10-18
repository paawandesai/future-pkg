// cdk synth/diff/deploy entry. Paths default to the CI layout; the account comes from the caller's
// credentials and is never printed by our scripts (deploy output is masked, see scripts/cdk.sh).
import { App, Tags } from "aws-cdk-lib";
import { DemoStack } from "../lib/stack.ts";

function required(name: string): string {
  const v = process.env[name];
  if (!v) throw new Error(`${name} is not set; model ids are configuration (see .env.example)`);
  return v;
}

const app = new App();
const stack = new DemoStack(app, "FuturePkgDemo", {
  env: { account: process.env.CDK_DEFAULT_ACCOUNT, region: "us-east-1" },
  lambdaDir: process.env.LAMBDA_DIR ?? "build/lambda",
  webDir: process.env.WEB_DIR ?? "../web/dist",
  // Model ids are configuration (CI variables or the environment), never defaults in code.
  modelFast: required("LLM_MODEL_FAST"),
  modelMain: required("LLM_MODEL_MAIN"),
  // Context (-c key=value or cdk.json) or environment. The budget is skipped without an address.
  apiConcurrency: Number(app.node.tryGetContext("apiConcurrency") ?? 5),
  budgetEmail: app.node.tryGetContext("budgetEmail") ?? (process.env.BUDGET_ALERT_EMAIL || undefined),
  monthlyBudgetUsd: Number(app.node.tryGetContext("monthlyBudgetUsd") ?? 20),
  description: "future-pkg coach decision support demo (synthetic data only)",
});
Tags.of(stack).add("Project", "future-pkg");
