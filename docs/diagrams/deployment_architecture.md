# Deployment / Architecture Diagram

Report reference: §4.4.1 (cloud-based system architecture: web UI, cloud backend with RDBMS, service layer,
Power BI), §4.4.4 (network: encrypted connections, VPN), §4.6 (secure hosting, encryption, RBAC),
§5.2.2 (backup).

```mermaid
flowchart LR
    subgraph Users["Users (desktop, tablet, mobile)"]
        B1[Browser - Muscat HQ]
        B2[Tablet - warehouse]
        B3[Phone - sales rep]
        POS[POS terminal]
    end
    PBID[Power BI Desktop / Service]
    GW[On-premises data gateway<br/>or VNet gateway]

    subgraph Cloud["Cloud host (Azure UAE North / AWS me-central-1) or Docker host"]
        direction LR
        NG[nginx<br/>TLS 1.2/1.3, HTTP→HTTPS, HSTS]
        subgraph App["web container"]
            DJ[Django + gunicorn<br/>UI · REST API /api/v1 · RBAC · 2FA · audit]
        end
        subgraph Data["db container / managed PostgreSQL"]
            PG[(PostgreSQL 16<br/>schema public: modules)]
            RP[(schema reporting<br/>dim_* / fact_* views)]
        end
        CR[cron container<br/>daily pg_dump 02:00]
        BK[(backups/<br/>14 days, checksummed)]
    end
    OFF[(Off-site copy<br/>S3 / Azure Blob, encrypted)]

    B1 & B2 & B3 -- HTTPS 443 --> NG
    POS -- HTTPS + X-API-Key + Idempotency-Key --> NG
    NG -- HTTP 8000 internal network --> DJ
    DJ -- SQL --> PG
    PG --- RP
    PBID -- "Web/API: HTTPS + token" --> NG
    PBID -. "PostgreSQL: TLS, powerbi_reader (SELECT reporting only)" .-> GW
    GW -. "VPN / private network, port 5432" .-> RP
    CR -- pg_dump --> PG
    CR --> BK
    CR -- "HTTPS upload (optional)" --> OFF
```

| Component | Technology | Security / reliability |
|---|---|---|
| Reverse proxy | nginx 1.27 | TLS termination, HTTP→HTTPS redirect, HSTS, security headers, re-resolves the app container |
| Application | Django 5.2, DRF, gunicorn (3 workers) | RBAC on every page and endpoint, TOTP 2FA, axes lockout, CSRF, audit log, health check |
| Database | PostgreSQL 16 | SSL on, field encryption for personal data, read-only `powerbi_reader`, encrypted disks in the cloud |
| Analytics | Power BI (Import + DirectQuery) | Gateway inside the private network, TLS to the database, token-based API alternative |
| Backup | cron + pg_dump | Daily, checksummed, optional AES-256 and off-site copy; RPO 24 h, RTO 4 h |
| Monitoring | Monitoring middleware + `/health/` | Response time, errors, availability, last backup – in-app and in Power BI |
