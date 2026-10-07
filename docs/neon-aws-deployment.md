# Move AgroBot to Neon and AWS

This guide moves AgroBot data into Neon PostgreSQL and deploys the app on AWS
ECS Fargate from the root `Dockerfile`, which builds the React frontend and
FastAPI backend into one container.

## 1. Create Neon database

1. Create a Neon project.
2. In the Neon connection modal, copy both connection strings:
   - Pooled URL for runtime traffic. Store this as `DATABASE_URL`.
   - Direct/unpooled URL for migrations and data import. Store this as
     `DATABASE_URL_UNPOOLED` or `DATABASE_MIGRATION_URL`.
3. Keep `sslmode=require&channel_binding=require` in the URL.

Use the direct/unpooled URL for Alembic and imports. Use the pooled URL for
normal app traffic.

## 2. Migrate local SQLite data to Neon

From the backend directory:

```bash
cd /Users/uday/Development/Agro-Bot/agrobot-assistant/backend
```

Run Alembic once against the direct Neon URL:

```bash
DATABASE_URL_UNPOOLED='<NEON_DIRECT_URL>' alembic upgrade head
```

Copy local SQLite data into Neon:

```bash
python scripts/migrate_sqlite_to_postgres.py \
  --source sqlite:///./agrobot.db \
  --dest '<NEON_DIRECT_URL>'
```

Verify:

```bash
psql '<NEON_DIRECT_URL>' \
  -c 'select count(*) as users from users;' \
  -c 'select count(*) as farms from farms;' \
  -c 'select count(*) as recommendations from recommendations;'
```

## 3. Configure AWS secrets

These commands assume:

- AWS profile: `agro-deploy`
- AWS region: `eu-north-1`
- App image repository: `agrobot-app`

Log in if SSO is expired:

```bash
aws sso login --profile agro-deploy
```

Store the Neon URLs and app secrets in AWS Secrets Manager:

```bash
AWS_PROFILE=agro-deploy aws secretsmanager create-secret \
  --region eu-north-1 \
  --name agrobot/DATABASE_URL \
  --secret-string '<NEON_POOLED_URL>'

AWS_PROFILE=agro-deploy aws secretsmanager create-secret \
  --region eu-north-1 \
  --name agrobot/DATABASE_URL_UNPOOLED \
  --secret-string '<NEON_DIRECT_URL>'

AWS_PROFILE=agro-deploy aws secretsmanager create-secret \
  --region eu-north-1 \
  --name agrobot/SECRET_KEY \
  --secret-string '<LONG_RANDOM_SECRET>'
```

Repeat for `GROQ_API_KEY`, `OPENWEATHER_API_KEY`, `TAVILY_API_KEY`, and
`AGMARKNET_API_KEY` if the production app needs those integrations.

## 4. Build and push image to ECR

App Runner is not available in `eu-north-1`, so production runs on ECS
Fargate (x86_64). Build for `linux/amd64` even on an Apple Silicon Mac, and
tag each image with the commit and a timestamp:

```bash
cd /Users/uday/Development/Agro-Bot

REPO=<AWS_ACCOUNT_ID>.dkr.ecr.eu-north-1.amazonaws.com/agrobot-app
TAG="$(git rev-parse --short HEAD)-$(date +%Y%m%d%H%M)"

AWS_PROFILE=agro-deploy aws ecr get-login-password --region eu-north-1 \
  | docker login --username AWS --password-stdin "${REPO%%/*}"

docker build --platform linux/amd64 -t "agrobot-app:${TAG}" .
docker tag "agrobot-app:${TAG}" "${REPO}:${TAG}"
docker push "${REPO}:${TAG}"
```

Always brace the variable (`"${REPO}:${TAG}"`). In zsh, an unbraced
`$REPO:latest` applies the `:l` modifier and pushes to a repository named
`agrobot-appatest` instead.

The image layers are large (CPU PyTorch). If a push fails with `broken pipe`
or a DNS error from Docker Desktop, run `docker push` again; finished layers
are skipped.

## 5. Deploy on ECS Fargate

Production resources (region `eu-north-1`):

| Resource | Name |
| --- | --- |
| ECS cluster | `Agrobot` |
| ECS service | `agrobot-app-service` (Fargate, 1 task) |
| Task definition family | `agrobot-app` (1 vCPU, 2 GB, `awsvpc`) |
| Execution role | `AgrobotTaskExecutionRole` |
| Load balancer | `agrobot-alb` → target group `agrobot-tg` (port 8000) |
| Logs | CloudWatch group `/ecs/agrobot-app` |
| DNS | `www.agrobot.in` via Cloudflare |

The container listens on port `8000` and has a container health check on
`/api/health`. Environment variables are `CORS_ORIGINS` and
`RUN_MIGRATIONS=false`. Secrets come from Secrets Manager (`agrobot/*`):
`SECRET_KEY`, `DATABASE_URL`, `DATABASE_URL_UNPOOLED`, `GROQ_API_KEY`,
`TAVILY_API_KEY`, `OPENWEATHER_API_KEY`, `AGMARKNET_API_KEY`. The execution
role must be allowed to read them.

Task definitions pin the image by digest, so pushing a tag alone deploys
nothing. Register a new revision that copies the current one with only the
image changed, then point the service at it:

```bash
export AWS_PROFILE=agro-deploy AWS_REGION=eu-north-1

DIGEST=$(aws ecr describe-images --repository-name agrobot-app \
  --image-ids imageTag="${TAG}" --query 'imageDetails[0].imageDigest' --output text)

CURRENT=$(aws ecs describe-services --cluster Agrobot --services agrobot-app-service \
  --query 'services[0].taskDefinition' --output text)

aws ecs describe-task-definition --task-definition "${CURRENT}" --query taskDefinition \
  | jq --arg img "${REPO}@${DIGEST}" '.containerDefinitions[0].image = $img
      | del(.taskDefinitionArn, .revision, .status, .requiresAttributes,
            .compatibilities, .registeredAt, .registeredBy, .deregisteredAt)' \
  > /tmp/agrobot-taskdef.json

NEW=$(aws ecs register-task-definition --cli-input-json file:///tmp/agrobot-taskdef.json \
  --query taskDefinition.taskDefinitionArn --output text)

aws ecs update-service --cluster Agrobot --service agrobot-app-service \
  --task-definition "${NEW}"

aws ecs wait services-stable --cluster Agrobot --services agrobot-app-service
```

To roll back, run `aws ecs update-service` with the previous revision
(`agrobot-app:<N>`).

## 6. Production checks

After deployment:

```bash
curl https://www.agrobot.in/api/health
curl https://www.agrobot.in/api/auth/me
curl https://www.agrobot.in/ads.txt
curl -s -o /dev/null -w '%{http_code}\n' https://www.agrobot.in/sitemap.xml
```

The second command should return an auth error. That is expected; it confirms
the API route is live. `ads.txt` should list the AdSense publisher ID.
