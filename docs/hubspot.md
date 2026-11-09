# HubSpot setup

Nexus sends every lead to HubSpot as a **Contact**, upserted by e-mail. Everything below works on the free HubSpot CRM.

## 1. Create the custom property

The promoter's id travels in one custom contact property.

1. HubSpot → **Settings → Data Management → Properties** → object **Contact** → **Create property**.
2. Label `Nexus promoter ID`, internal name **`nexus_promoter_id`**, field type **Single-line text**.

If you pick another internal name, set `HUBSPOT_PROMOTER_PROPERTY` to it.

> The free plan allows only a few custom properties per account, so Nexus uses just this one. The promoter's display name is not sent: it can change, and the id is enough to join back to Nexus.

## 2. Create the private app

1. **Settings → Integrations → Private apps → Create a private app**, name it `Nexus`.
2. Scopes: `crm.objects.contacts.read` and `crm.objects.contacts.write`.
3. Copy the access token (`pat-...`).

## 3. Configure Nexus

```env
CRM_PROVIDER=hubspot
HUBSPOT_TOKEN=pat-na1-...
```

In production the token goes into Secret Manager (see `docs/deploy-cloud-run.md`), never into the repository.

## How errors are handled

| HubSpot answer | Nexus does |
|---|---|
| `201` | Lead marked `synced`, contact id stored in `crm_id` |
| `409` (contact exists) | Reads the existing id from the error and `PATCH`es that contact — so a redelivered event is harmless |
| `429`, `5xx`, timeout, network error | Keeps the event `pending` and retries with exponential backoff (30 s, 1 min, 2 min… max 6 h) |
| `401` / `403` | Retried too: it is a configuration problem that a fixed token solves |
| Any other `4xx` | Marked `failed` at once (the same data will never be accepted); an admin can retry it from the Leads page after fixing the cause |

Free private apps are limited to 100 requests per 10 seconds; one lead costs one or two requests, so a normal form never gets close.
