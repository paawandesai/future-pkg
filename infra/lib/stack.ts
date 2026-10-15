// The demo deployment: invite-only Cognito, API on Lambda (streaming), SPA on S3 + CloudFront,
// DynamoDB plans with TTL and a daily purge, the API key in Secrets Manager. Nothing here holds a
// secret value: the secret is created empty-random and its value is put by the deploy job.
import {
  CfnOutput,
  Duration,
  Fn,
  RemovalPolicy,
  Stack,
  type StackProps,
  aws_cloudfront as cloudfront,
  aws_cloudfront_origins as origins,
  aws_cognito as cognito,
  aws_dynamodb as dynamodb,
  aws_iam as iam,
  aws_events as events,
  aws_events_targets as targets,
  aws_lambda as lambda,
  aws_logs as logs,
  aws_s3 as s3,
  aws_s3_deployment as s3deploy,
  aws_secretsmanager as secretsmanager,
  custom_resources as cr,
} from "aws-cdk-lib";
import type { Construct } from "constructs";

export const SECRET_NAME = "future-pkg/anthropic-api-key";
// AWS Lambda Web Adapter (Apache-2.0, awslabs): runs the FastAPI app unchanged and streams responses.
const WEB_ADAPTER_LAYER = "arn:aws:lambda:us-east-1:753240598075:layer:LambdaAdapterLayerX86:30";

export interface DemoStackProps extends StackProps {
  /** Directory with the packaged API (scripts/package_lambda.sh). */
  lambdaDir: string;
  /** The built SPA (web/dist). */
  webDir: string;
  modelFast: string;
  modelMain: string;
  /** Existing pool user (by email) to put in the admin group; only AWS can grant admin. */
  adminEmail?: string;
}

export class DemoStack extends Stack {
  constructor(scope: Construct, id: string, props: DemoStackProps) {
    super(scope, id, props);

    // ---------- storage ----------
    const plans = new dynamodb.Table(this, "Plans", {
      partitionKey: { name: "id", type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      timeToLiveAttribute: "expires_at",
      removalPolicy: RemovalPolicy.DESTROY,
    });

    // Access requests (email, optional name, reason) expire after 7 days; rate counters after 2 hours.
    const access = new dynamodb.Table(this, "AccessRequests", {
      partitionKey: { name: "id", type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      timeToLiveAttribute: "expires_at",
      removalPolicy: RemovalPolicy.DESTROY,
    });

    const apiKey = new secretsmanager.Secret(this, "AnthropicKey", {
      secretName: SECRET_NAME,
      description: "Anthropic API key for the coach demo; value is put by the deploy job",
      removalPolicy: RemovalPolicy.DESTROY,
    });

    // ---------- auth: invite-only coaches ----------
    const pool = new cognito.UserPool(this, "Coaches", {
      userPoolName: "future-pkg-coaches",
      selfSignUpEnabled: false,
      signInAliases: { email: true },
      autoVerify: { email: true },
      featurePlan: cognito.FeaturePlan.LITE,
      passwordPolicy: {
        minLength: 12,
        requireLowercase: true,
        requireUppercase: true,
        requireDigits: true,
        requireSymbols: false,
        tempPasswordValidity: Duration.days(7),
      },
      accountRecovery: cognito.AccountRecovery.NONE,
      customAttributes: { coach_id: new cognito.StringAttribute({ minLen: 1, maxLen: 64, mutable: true }) },
      userInvitation: {
        emailSubject: "Your coach workspace demo invite",
        emailBody:
          "You're invited to the coach decision support demo (synthetic data only). " +
          "Sign in with {username} and the temporary password {####}, then choose your own.",
      },
      removalPolicy: RemovalPolicy.DESTROY,
    });
    const client = pool.addClient("Web", {
      authFlows: { userPassword: true },
      generateSecret: false,
      preventUserExistenceErrors: true,
      idTokenValidity: Duration.hours(1),
      accessTokenValidity: Duration.hours(1),
      refreshTokenValidity: Duration.hours(8),
      readAttributes: new cognito.ClientAttributes()
        .withStandardAttributes({ email: true })
        .withCustomAttributes("coach_id"),
      // Coaches can't write their own coach_id: only an admin sets it, so a token can't be re-scoped.
      writeAttributes: new cognito.ClientAttributes().withStandardAttributes({ email: true }),
    });

    // Admins approve access requests and manage reviewer accounts. Membership is granted only by
    // AWS (this stack, or the console), never by the app.
    const admins = new cognito.CfnUserPoolGroup(this, "Admins", {
      userPoolId: pool.userPoolId,
      groupName: "admin",
      description: "Demo admins: approve access requests, invite and disable reviewers",
    });
    if (props.adminEmail) {
      const grant = new cr.AwsCustomResource(this, "FirstAdmin", {
        onUpdate: {
          service: "CognitoIdentityServiceProvider",
          action: "adminAddUserToGroup",
          parameters: { UserPoolId: pool.userPoolId, GroupName: "admin", Username: props.adminEmail },
          physicalResourceId: cr.PhysicalResourceId.of("first-admin"),
        },
        policy: cr.AwsCustomResourcePolicy.fromSdkCalls({ resources: [pool.userPoolArn] }),
        installLatestAwsSdk: false,
      });
      grant.node.addDependency(admins);
    }

    // ---------- API ----------
    const apiLogs = new logs.LogGroup(this, "ApiLogs", {
      retention: logs.RetentionDays.TWO_WEEKS,
      removalPolicy: RemovalPolicy.DESTROY,
    });
    const api = new lambda.Function(this, "Api", {
      runtime: lambda.Runtime.PYTHON_3_12,
      architecture: lambda.Architecture.X86_64,
      code: lambda.Code.fromAsset(props.lambdaDir),
      handler: "run.sh",
      memorySize: 1769,
      timeout: Duration.seconds(60),
      layers: [lambda.LayerVersion.fromLayerVersionArn(this, "WebAdapter", WEB_ADAPTER_LAYER)],
      logGroup: apiLogs,
      environment: {
        AWS_LAMBDA_EXEC_WRAPPER: "/opt/bootstrap",
        AWS_LWA_INVOKE_MODE: "response_stream",
        AWS_LWA_READINESS_CHECK_PATH: "/healthz",
        PORT: "8080",
        AUTH_MODE: "cognito",
        COGNITO_USER_POOL_ID: pool.userPoolId,
        COGNITO_CLIENT_ID: client.userPoolClientId,
        PLAN_TABLE: plans.tableName,
        ACCESS_TABLE: access.tableName,
        // Salt for hashing client addresses in rate counters: the stack's own GUID, not a secret.
        RATE_SALT: Fn.select(2, Fn.split("/", this.stackId)),
        ANTHROPIC_SECRET_ID: apiKey.secretName,
        LLM_MODEL_FAST: props.modelFast,
        LLM_MODEL_MAIN: props.modelMain,
        AS_OF_DATE: "2026-06-04",
        DATA_DIR: "/var/task/data",
        KG_DIR: "/var/task/kg",
        FIXTURES_DIR: "/var/task/fixtures",
      },
    });
    plans.grantReadWriteData(api);
    access.grantReadWriteData(api);
    apiKey.grantRead(api);
    api.addToRolePolicy(
      new iam.PolicyStatement({
        actions: [
          "cognito-idp:AdminCreateUser",
          "cognito-idp:AdminDisableUser",
          "cognito-idp:AdminEnableUser",
          "cognito-idp:ListUsers",
          "cognito-idp:ListUsersInGroup",
        ],
        resources: [pool.userPoolArn],
      }),
    );
    // Public URL; every /api route verifies a Cognito ID token, /healthz returns only {"status":"ok"}.
    const apiUrl = api.addFunctionUrl({
      authType: lambda.FunctionUrlAuthType.NONE,
      invokeMode: lambda.InvokeMode.RESPONSE_STREAM,
    });

    // ---------- purge: daily, deletes every plan drafted more than 12 hours ago (TTL is the backstop) ----------
    const purge = new lambda.Function(this, "Purge", {
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: "index.handler",
      timeout: Duration.minutes(5),
      code: lambda.Code.fromInline(PURGE_CODE),
      environment: { PLAN_TABLE: plans.tableName },
      logGroup: new logs.LogGroup(this, "PurgeLogs", {
        retention: logs.RetentionDays.TWO_WEEKS,
        removalPolicy: RemovalPolicy.DESTROY,
      }),
    });
    plans.grantReadWriteData(purge);
    new events.Rule(this, "DailyPurge", {
      schedule: events.Schedule.rate(Duration.days(1)),
      targets: [new targets.LambdaFunction(purge)],
    });

    // ---------- web ----------
    const site = new s3.Bucket(this, "Site", {
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
      enforceSSL: true,
      removalPolicy: RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
    });
    const headers = new cloudfront.ResponseHeadersPolicy(this, "Headers", {
      customHeadersBehavior: {
        customHeaders: [{ header: "X-Robots-Tag", value: "noindex, nofollow, noarchive", override: true }],
      },
      securityHeadersBehavior: {
        contentSecurityPolicy: {
          contentSecurityPolicy: [
            "default-src 'self'",
            "script-src 'self'",
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
            "font-src https://fonts.gstatic.com",
            `connect-src 'self' https://cognito-idp.${this.region}.amazonaws.com`,
            "img-src 'self' data:",
            "frame-ancestors 'none'",
            "base-uri 'none'",
            "form-action 'self'",
          ].join("; "),
          override: true,
        },
        contentTypeOptions: { override: true },
        frameOptions: { frameOption: cloudfront.HeadersFrameOption.DENY, override: true },
        referrerPolicy: { referrerPolicy: cloudfront.HeadersReferrerPolicy.NO_REFERRER, override: true },
        strictTransportSecurity: { accessControlMaxAge: Duration.days(365), includeSubdomains: true, override: true },
      },
    });
    const distribution = new cloudfront.Distribution(this, "Cdn", {
      comment: "future-pkg coach demo (synthetic data only)",
      defaultRootObject: "index.html",
      priceClass: cloudfront.PriceClass.PRICE_CLASS_100,
      defaultBehavior: {
        origin: origins.S3BucketOrigin.withOriginAccessControl(site),
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        responseHeadersPolicy: headers,
      },
      additionalBehaviors: {
        "/api/*": {
          origin: new origins.FunctionUrlOrigin(apiUrl, { readTimeout: Duration.seconds(60) }),
          viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.HTTPS_ONLY,
          allowedMethods: cloudfront.AllowedMethods.ALLOW_ALL,
          cachePolicy: cloudfront.CachePolicy.CACHING_DISABLED,
          originRequestPolicy: cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
          responseHeadersPolicy: headers,
        },
      },
    });
    new s3deploy.BucketDeployment(this, "SiteFiles", {
      destinationBucket: site,
      distribution,
      distributionPaths: ["/*"],
      sources: [
        s3deploy.Source.asset(props.webDir),
        s3deploy.Source.jsonData("config.json", {
          authMode: "cognito",
          region: this.region,
          userPoolClientId: client.userPoolClientId,
        }),
      ],
      memoryLimit: 256,
    });

    // Outputs carry no secrets and no account id.
    new CfnOutput(this, "SiteUrl", { value: `https://${distribution.distributionDomainName}` });
    new CfnOutput(this, "UserPoolId", { value: pool.userPoolId });
  }
}

const PURGE_CODE = `
import os, time, boto3
table = boto3.resource("dynamodb").Table(os.environ["PLAN_TABLE"])
DAY = 86400

def handler(event, context):
    # expires_at = drafted + 1 day, so expires_at <= now + 12 h means drafted over 12 hours ago.
    cutoff = int(time.time()) + DAY // 2
    deleted, kwargs = 0, {"ProjectionExpression": "id, expires_at"}
    while True:
        page = table.scan(**kwargs)
        with table.batch_writer() as batch:
            for item in page.get("Items", []):
                if int(item.get("expires_at", 0)) <= cutoff:
                    batch.delete_item(Key={"id": item["id"]})
                    deleted += 1
        if "LastEvaluatedKey" not in page:
            break
        kwargs["ExclusiveStartKey"] = page["LastEvaluatedKey"]
    print(f"purged {deleted}")
    return {"purged": deleted}
`;
