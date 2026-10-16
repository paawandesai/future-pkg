// cdk synth/diff/deploy entry. Paths default to the CI layout; the account comes from the caller's
// credentials and is never printed by our scripts (deploy output is masked, see scripts/cdk.sh).
import { App, Tags } from "aws-cdk-lib";
import { DemoStack } from "../lib/stack.ts";

const app = new App();
const stack = new DemoStack(app, "FuturePkgDemo", {
  env: { account: process.env.CDK_DEFAULT_ACCOUNT, region: "us-east-1" },
  lambdaDir: process.env.LAMBDA_DIR ?? "build/lambda",
  webDir: process.env.WEB_DIR ?? "../web/dist",
  modelFast: process.env.LLM_MODEL_FAST ?? "claude-haiku-5-5",
  modelMain: process.env.LLM_MODEL_MAIN ?? "claude-sonnet-5-5",
  adminEmail: process.env.DEMO_ADMIN_EMAIL || undefined,
  description: "future-pkg coach decision support demo (synthetic data only)",
});
Tags.of(stack).add("Project", "future-pkg");
