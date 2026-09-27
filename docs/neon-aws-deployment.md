# Move AgroBot to Neon and AWS

This guide moves AgroBot data into Neon PostgreSQL and deploys the app on AWS
from the root `Dockerfile`, which builds the React frontend and FastAPI backend
into one container.

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

Authenticate Docker to ECR:

```bash
AWS_PROFILE=agro-deploy aws ecr get-login-password --region eu-north-1 \
  | docker login --username AWS --password-stdin <AWS_ACCOUNT_ID>.dkr.ecr.eu-north-1.amazonaws.com
```

Build and push the app image from the repo root:

```bash
cd /Users/uday/Development/Agro-Bot

docker build -t agrobot-app:latest .

docker tag agrobot-app:latest \
  <AWS_ACCOUNT_ID>.dkr.ecr.eu-north-1.amazonaws.com/agrobot-app:latest

docker push <AWS_ACCOUNT_ID>.dkr.ecr.eu-north-1.amazonaws.com/agrobot-app:latest
```

## 5. Deploy on AWS App Runner

Create an App Runner service from the private ECR image:

- Repository type: Container registry
- Provider: Amazon ECR
- Image: `<AWS_ACCOUNT_ID>.dkr.ecr.eu-north-1.amazonaws.com/agrobot-app:latest`
- Port: `8000`
- Health check path: `/api/health`
- Environment variables:
  - `CORS_ORIGINS=https://<your-app-runner-or-custom-domain>`
  - `RUN_MIGRATIONS=false`
- Environment secrets:
  - `DATABASE_URL` -> `agrobot/DATABASE_URL`
  - `DATABASE_URL_UNPOOLED` -> `agrobot/DATABASE_URL_UNPOOLED`
  - `SECRET_KEY` -> `agrobot/SECRET_KEY`
  - API keys as needed

The App Runner instance role must be allowed to read the Secrets Manager
secrets referenced as environment secrets.

## 6. Production checks

After deployment:

```bash
curl https://<app-runner-domain>/api/health
curl https://<app-runner-domain>/api/auth/me
```

The second command should return an auth error. That is expected; it confirms
the API route is live.
