# TravelOS — Deployment Guide (Phase 5)

How to run TravelOS in production. The app is two services + datastores:

```
            ┌──────────── CloudFront (assets) ◀── S3 (posters/brochures/reels)
Internet ─▶ ALB ─▶ ECS "web" (Gunicorn/Uvicorn, RUN_SCHEDULER=false)
                     │
                     ├─▶ RDS Postgres 16 (+pgvector, RLS)
                     └─▶ ElastiCache Redis
            ECS "worker" (python -m app.workers.run, RUN_SCHEDULER=true)  ◀── single scheduler
Frontend:  nginx static SPA (S3+CloudFront or its own ECS/Amplify), VITE_API_BASE_URL → ALB
```

**Why a separate worker:** the follow-up + publishing schedulers must run exactly
once. The web service runs N Gunicorn workers, so it sets `RUN_SCHEDULER=false`;
the dedicated `worker` service runs the scheduler.

---

## 1. Try the production shape locally

```bash
cp .env.example .env
# set these in .env:
#   ENVIRONMENT=production
#   SECRET_KEY=<long random>
#   CREDENTIALS_ENCRYPTION_KEY=<python -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())">
docker compose -f docker-compose.prod.yml up --build
# web → http://localhost:8000 (Gunicorn) ; frontend → http://localhost:8080 (nginx)
```

This runs Gunicorn + a separate scheduler worker + nginx-served frontend.

---

## 2. Deploy to AWS

Prereqs: an AWS account, Terraform ≥ 1.6, Docker, AWS CLI configured.

### 2a. Provision infrastructure
```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars   # fill in secrets
terraform init
terraform apply
```
Creates: VPC, ECR repos, RDS Postgres, ElastiCache Redis, S3 + CloudFront,
ALB, ECS cluster + web/worker/migrate task defs + services, IAM, Secrets Manager.
Note the outputs (`alb_dns_name`, `ecr_backend_url`, `assets_cdn_domain`, …).

### 2b. One-time DB bootstrap (RDS)
RDS has no init hook, so create the non-superuser app role + pgvector once, as
the master user (adapt `infra/db/init.sql` — the master role is `travelos`, not
`postgres`):
```bash
psql "postgresql://travelos:<db_password>@<rds_endpoint>:5432/travelos" \
  -c "CREATE ROLE travelos_app LOGIN PASSWORD 'travelos_app';" \
  -c "GRANT ALL ON SCHEMA public TO travelos_app;" \
  -c "ALTER SCHEMA public OWNER TO travelos_app;" \
  -c "CREATE EXTENSION IF NOT EXISTS vector;"
```
(Use a strong password and put it in the `DATABASE_URL` secret.)

### 2c. Build, push, migrate, deploy
The `Deploy` GitHub Action does this on push to `main`. Configure repo
Variables/Secrets (see `.github/workflows/deploy.yml`) — `AWS_ROLE_ARN` (OIDC),
`AWS_REGION`, `ECR_BACKEND`, `ECR_FRONTEND`, `ECS_CLUSTER`, `ECS_WEB_SERVICE`,
`ECS_WORKER_SERVICE`, `PUBLIC_API_URL`. Or manually:
```bash
aws ecr get-login-password | docker login --username AWS --password-stdin <ecr>
docker build -f backend/Dockerfile.prod -t <ecr>/travelos-backend:latest ./backend && docker push <ecr>/travelos-backend:latest
aws ecs run-task --cluster travelos --task-definition travelos-migrate --launch-type FARGATE --network-configuration ...
aws ecs update-service --cluster travelos --service travelos-web --force-new-deployment
aws ecs update-service --cluster travelos --service travelos-worker --force-new-deployment
```

### 2d. Domain + HTTPS
Point your domain at `alb_dns_name`, add an ACM cert + a 443 listener (redirect
80→443), and set `CORS_ORIGINS` to your frontend origin.

---

## 3. Going live with real integrations

All of these work in **dev/mock** mode out of the box; flip to real by setting keys:

| Integration | What to set | Notes |
|---|---|---|
| LLM text/images | `GEMINI_API_KEY` (+ `LLM_TEXT_PROVIDER=gemini`, `LLM_IMAGE_PROVIDER=gemini`) | Free tier OK; falls back to mock if unset |
| Assets | `STORAGE_BACKEND=s3`, `S3_BUCKET`, `ASSET_PUBLIC_BASE_URL=https://<cloudfront>` | **Public URLs are required** — IG Graph API fetches the image by URL |
| Instagram | `META_APP_ID/SECRET`; connect via OAuth; App Review for `instagram_content_publish` | Business/Creator IG + linked FB Page; start in Dev mode w/ test users |
| Meta Lead Ads | Subscribe app to `leadgen`; webhook → `/api/v1/public/webhooks/meta` | Map Page id → tenant (replace dev `?tenant=` routing) |
| WhatsApp | `WHATSAPP_PROVIDER=cloud`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_TOKEN` | Pre-approve templates for sends outside the 24h window |
| Email / SMS | `EMAIL_PROVIDER=resend\|brevo` (+key); `SMS_PROVIDER=fast2sms` (+key) | Default `console` just logs |

Webhook callback URLs to register with Meta:
`https://<your-api>/api/v1/public/webhooks/meta` and `.../webhooks/whatsapp`
(verify tokens: `META_WEBHOOK_VERIFY_TOKEN`, `WHATSAPP_VERIFY_TOKEN`).

---

## 4. Operations
- **Migrations:** the `travelos-migrate` task runs `alembic upgrade head`.
- **Logs:** CloudWatch `/ecs/travelos`.
- **Scale:** raise `desired_web_count`; keep the worker at 1.
- **Secrets:** rotate in Secrets Manager; tasks read `SECRET_KEY`,
  `CREDENTIALS_ENCRYPTION_KEY`, `DATABASE_URL`, `REDIS_URL` from there.
- The app **fails fast** in production if `SECRET_KEY` / `CREDENTIALS_ENCRYPTION_KEY`
  are unset (see `Settings.require_production_secrets`).
