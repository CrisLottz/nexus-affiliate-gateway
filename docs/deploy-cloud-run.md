# Deploying to Google Cloud Run

This is roadmap steps 0 and 9: the accounts and the one-time cloud setup. After it, every merge to `main` deploys automatically through `.github/workflows/deploy.yml`.

Everything here fits in free tiers for a small deployment (Cloud Run, Artifact Registry under 0.5 GB, Secret Manager under 6 active secrets, Cloud Scheduler under 3 jobs, Neon free plan). The budget alert and `--max-instances 2` are the guard rails.

## 0. Accounts

| Service | What you need | Cost |
|---|---|---|
| Google Cloud | A project with billing enabled and a **budget alert of US$1** (Billing → Budgets & alerts) | Free tier |
| Neon | A project → copy the **pooled** connection string (`postgresql://…-pooler…/neondb?sslmode=require`) | Free plan |
| HubSpot (optional) | Free CRM + private app token — see [hubspot.md](hubspot.md) | Free |

## 1. Variables used below

```bash
PROJECT_ID=your-project-id
REGION=us-central1
SERVICE=nexus
GITHUB_REPO=CrisLottz/nexus-affiliate-gateway
gcloud config set project "$PROJECT_ID"
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format 'value(projectNumber)')
```

## 2. APIs, image registry and service accounts

```bash
gcloud services enable run.googleapis.com artifactregistry.googleapis.com \
  secretmanager.googleapis.com cloudscheduler.googleapis.com iamcredentials.googleapis.com

gcloud artifacts repositories create nexus --repository-format docker --location "$REGION"

# Runtime identity of the container: may only read its secrets.
gcloud iam service-accounts create nexus-runtime
# Identity GitHub Actions uses to deploy.
gcloud iam service-accounts create nexus-deployer

RUNTIME_SA=nexus-runtime@$PROJECT_ID.iam.gserviceaccount.com
DEPLOY_SA=nexus-deployer@$PROJECT_ID.iam.gserviceaccount.com

for role in roles/run.admin roles/artifactregistry.writer; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" --member "serviceAccount:$DEPLOY_SA" --role "$role"
done
# The deployer may deploy services that run as the runtime account.
gcloud iam service-accounts add-iam-policy-binding "$RUNTIME_SA" \
  --member "serviceAccount:$DEPLOY_SA" --role roles/iam.serviceAccountUser
```

## 3. Secrets

```bash
python -c "import secrets; print(secrets.token_urlsafe(48), end='')" | gcloud secrets create nexus-secret-key --data-file=-
python -c "import secrets; print(secrets.token_urlsafe(32), end='')" | gcloud secrets create nexus-internal-token --data-file=-
printf '%s' 'postgresql://USER:PASSWORD@HOST-pooler.REGION.aws.neon.tech/neondb?sslmode=require' \
  | gcloud secrets create nexus-database-url --data-file=-
# Only with HubSpot:
# printf '%s' 'pat-na1-…' | gcloud secrets create nexus-hubspot-token --data-file=-

for s in nexus-secret-key nexus-internal-token nexus-database-url; do
  gcloud secrets add-iam-policy-binding "$s" --member "serviceAccount:$RUNTIME_SA" \
    --role roles/secretmanager.secretAccessor
done
```

## 4. Workload Identity Federation (GitHub → Google without a JSON key)

GitHub Actions presents a short-lived OIDC token; Google trusts it only for this repository.

```bash
gcloud iam workload-identity-pools create github --location global
gcloud iam workload-identity-pools providers create-oidc github \
  --location global --workload-identity-pool github \
  --issuer-uri https://token.actions.githubusercontent.com \
  --attribute-mapping "google.subject=assertion.sub,attribute.repository=assertion.repository" \
  --attribute-condition "assertion.repository == '$GITHUB_REPO'"

gcloud iam service-accounts add-iam-policy-binding "$DEPLOY_SA" \
  --role roles/iam.workloadIdentityUser \
  --member "principalSet://iam.googleapis.com/projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/github/attribute.repository/$GITHUB_REPO"

echo "projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/github/providers/github"
```

## 5. GitHub repository variables

Settings → Secrets and variables → Actions → **Variables** (none of these are secret):

| Variable | Value |
|---|---|
| `GCP_PROJECT_ID` | `$PROJECT_ID` |
| `GCP_REGION` | `$REGION` |
| `CLOUD_RUN_SERVICE` | `nexus` |
| `GCP_WIF_PROVIDER` | the `projects/…/providers/github` line printed above |
| `GCP_DEPLOY_SA` | `$DEPLOY_SA` |
| `GCP_RUNTIME_SA` | `$RUNTIME_SA` |
| `CRM_PROVIDER` | `mock` or `hubspot` |
| `DEMO_MODE` | `true` for the public demo |
| `BRAND_NAME` | optional |
| `DEPLOY_ENABLED` | `true` — turns the workflow on |

Then run **Actions → Deploy to Cloud Run → Run workflow** (or merge to `main`). The container runs the Alembic migrations on start.

## 6. Cloud Scheduler for the outbox

Cloud Run scales to zero, so the retries are driven from outside, every 5 minutes:

```bash
URL=$(gcloud run services describe "$SERVICE" --region "$REGION" --format 'value(status.url)')
TOKEN=$(gcloud secrets versions access latest --secret nexus-internal-token)
gcloud scheduler jobs create http nexus-outbox-flush --location "$REGION" \
  --schedule "*/5 * * * *" --http-method POST \
  --uri "$URL/internal/outbox/flush" \
  --headers "Authorization=Bearer $TOKEN"
```

## 7. First admin

In demo mode the demo admin already exists. Otherwise, create the first real admin once from your machine against the production database:

```bash
DATABASE_URL='postgresql://…neon…' SECRET_KEY=x-unused-locally-0000 \
  flask --app nexus create-user --email you@example.com --name "Your Name" --role admin
```

## Notes

- **Cold starts:** the first request after idle takes a few seconds. `--min-instances 1` removes it but is no longer free.
- **Rate limits are per instance** (in-memory). With `--max-instances 2` that is acceptable; for more, point Flask-Limiter at Redis.
- **Rolling back:** Cloud Run keeps every revision — `gcloud run services update-traffic nexus --to-revisions REVISION=100`.
