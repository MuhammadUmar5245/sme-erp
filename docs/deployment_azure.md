# Deployment on Microsoft Azure (UAE North)

Report reference: §4.6 (secure hosting on AWS or Azure: encryption, firewalls, DDoS protection), §4.4.1 (cloud
backend), §4.4.4 (VPN), §5.2.2 (backup to the cloud), §2.3.3 (scalability).

**Region:** *UAE North* (Dubai) is the nearest Azure region to Oman (≈ 45 ms from Muscat); *UAE Central*
(Abu Dhabi) is the paired region for disaster recovery. Check whether an Azure region in Oman has become
available before deploying.

## Architecture

| Component | Azure service | Size for Al Wadi (≈ 45 staff) |
|---|---|---|
| Web application | **Azure App Service for Containers** (Linux), image `sme-erp-web` from Azure Container Registry | Premium v3 P1v3 (2 vCPU, 8 GB); autoscale 1–3 instances on CPU > 70 % |
| TLS / reverse proxy | App Service managed certificate + custom domain (replaces nginx); optional **Azure Front Door** with WAF and DDoS protection | Standard tier |
| Database | **Azure Database for PostgreSQL – Flexible Server** 16 | General Purpose D2ds_v5, 128 GB, zone-redundant HA (optional), backups 14–35 days, geo-redundant backup |
| Backups (extra) | Cron job (Azure Container Apps job or Logic App) running `scripts/backup.sh` → **Blob Storage** (`AZURE_BLOB_SAS_URL`) | Cool tier, immutable storage + lifecycle 365 days |
| Secrets | **Azure Key Vault** referenced from App Service settings | `DJANGO_SECRET_KEY`, `FIELD_ENCRYPTION_KEY`, DB and Power BI passwords |
| Network | Virtual Network with App Service VNet integration; PostgreSQL with **private access** (no public endpoint) | |
| Power BI | **VNet data gateway** (Power BI Premium/Fabric) or on-premises data gateway on a small VM in the VNet | B2s VM if on-premises gateway |
| VPN | **VPN Gateway** (site-to-site) from the Muscat head office / Sohar branch to the VNet | VpnGw1 |
| Monitoring | Application Insights + Azure Monitor alerts on `/health/`; in-app monitoring page | |

Encryption at rest: Flexible Server and Blob Storage encrypt data with AES-256 by default (optionally with
customer-managed keys in Key Vault). In transit: HTTPS only (App Service *HTTPS Only* on, TLS 1.2 minimum) and
`require_secure_transport=ON` on PostgreSQL.

## Steps

```bash
# 1. Resource group, registry, image
az group create -n rg-sme-erp -l uaenorth
az acr create -g rg-sme-erp -n alwadierpacr --sku Basic
az acr build -r alwadierpacr -t sme-erp-web:1.0 -f docker/web/Dockerfile .

# 2. Network and PostgreSQL (private access)
az network vnet create -g rg-sme-erp -n vnet-erp --address-prefixes 10.20.0.0/16 \
   --subnet-name snet-app --subnet-prefixes 10.20.1.0/24
az postgres flexible-server create -g rg-sme-erp -n alwadi-erp-db -l uaenorth --version 16 \
   --tier GeneralPurpose --sku-name Standard_D2ds_v5 --storage-size 128 \
   --vnet vnet-erp --subnet snet-db --subnet-prefixes 10.20.2.0/24 \
   --admin-user erpadmin --admin-password '<from Key Vault>' --backup-retention 35 --geo-redundant-backup Enabled
az postgres flexible-server db create -g rg-sme-erp -s alwadi-erp-db -d sme_erp

# 3. Key Vault with the secrets from .env.example
az keyvault create -g rg-sme-erp -n kv-alwadi-erp -l uaenorth
az keyvault secret set --vault-name kv-alwadi-erp -n django-secret-key --value '<random>'
#    ... FIELD-ENCRYPTION-KEY, POSTGRES-PASSWORD, POWERBI-READER-PASSWORD

# 4. App Service
az appservice plan create -g rg-sme-erp -n plan-erp --is-linux --sku P1v3
az webapp create -g rg-sme-erp -p plan-erp -n alwadi-erp \
   --deployment-container-image-name alwadierpacr.azurecr.io/sme-erp-web:1.0
az webapp vnet-integration add -g rg-sme-erp -n alwadi-erp --vnet vnet-erp --subnet snet-app
az webapp update -g rg-sme-erp -n alwadi-erp --https-only true
az webapp config appsettings set -g rg-sme-erp -n alwadi-erp --settings \
   DJANGO_SETTINGS_MODULE=config.settings.prod WEBSITES_PORT=8000 \
   POSTGRES_HOST=alwadi-erp-db.postgres.database.azure.com POSTGRES_DB=sme_erp POSTGRES_USER=erpadmin \
   DJANGO_ALLOWED_HOSTS=erp.alwadi.om DJANGO_CSRF_TRUSTED_ORIGINS=https://erp.alwadi.om \
   DJANGO_SECRET_KEY='@Microsoft.KeyVault(SecretUri=https://kv-alwadi-erp.vault.azure.net/secrets/django-secret-key)'
az webapp config set -g rg-sme-erp -n alwadi-erp --min-tls-version 1.2
```

5. Custom domain `erp.alwadi.om` with an App Service managed certificate.
6. The container start script runs `migrate` (creates the `reporting` schema and `powerbi_reader`) on start.
   Load data: run `python manage.py seed_demo --reset` (demo) **or** use the import wizard (live) from the App
   Service SSH console.
7. Backups: Flexible Server automated backups give point-in-time restore (RPO ≈ 5 min). Keep the daily
   `backup.sh` job to Blob Storage as an independent, portable copy (`AZURE_BLOB_SAS_URL`).
8. Power BI: install the gateway, add a PostgreSQL connection to `alwadi-erp-db.postgres.database.azure.com`
   with `powerbi_reader` (see `docs/powerbi/connection_guide.md`).
9. Alerts: Azure Monitor alert when `/health/` fails 3 times, CPU > 80 %, storage > 80 %, or no backup blob in 26 h.

## Indicative monthly cost (pay-as-you-go, USD, 2026 list prices – verify in the Azure calculator)

| Item | Approx. |
|---|---|
| App Service P1v3 | 140 |
| PostgreSQL Flexible D2ds_v5 + 128 GB + backup | 190 |
| Blob storage, Key Vault, Container Registry, monitoring | 25 |
| VPN Gateway VpnGw1 | 140 |
| **Total** | **≈ 495 USD (≈ 190 OMR)** – compare with the subscription assumption in the feasibility calculator |
