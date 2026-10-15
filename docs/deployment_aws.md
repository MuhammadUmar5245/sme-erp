# Deployment on Amazon Web Services (Middle East)

Report reference: §4.6 (secure hosting on AWS or Azure), §4.4.1, §4.4.4, §5.2.2, §2.3.3.

**Region:** *me-central-1* (UAE) – nearest to Muscat; *me-south-1* (Bahrain) as the disaster-recovery region.

## Option A – ECS on Fargate (recommended)

| Component | AWS service | Size for Al Wadi |
|---|---|---|
| Container images | **ECR** repository `sme-erp-web` | – |
| Web application | **ECS Fargate** service, 2 tasks across 2 AZs, auto scaling on CPU | 1 vCPU / 2 GB per task |
| TLS, routing, WAF | **Application Load Balancer** with an ACM certificate (HTTPS 443, redirect 80→443), **AWS WAF**, Shield Standard (DDoS) | – |
| Database | **Amazon RDS for PostgreSQL 16**, Multi-AZ, storage encrypted with KMS, `rds.force_ssl = 1`, automated backups 14–35 days | db.m6g.large, 100 GB gp3 |
| Backups (extra) | **EventBridge Scheduler** → ECS task running `scripts/backup.sh` → **S3** (`S3_BUCKET`, SSE-KMS, Object Lock, lifecycle to Glacier) | – |
| Secrets | **Secrets Manager** / SSM Parameter Store injected into the task definition | – |
| Network | VPC with public subnets (ALB) and private subnets (tasks, RDS); security groups: ALB → tasks:8000, tasks → RDS:5432 | – |
| Power BI | On-premises data gateway on a small **EC2** Windows instance in a private subnet | t3.medium |
| VPN | **AWS Site-to-Site VPN** from the Muscat HQ and Sohar branch | – |
| Monitoring | CloudWatch logs and alarms (ALB 5xx, target health on `/health/`, RDS CPU/storage) + in-app monitoring | – |

### Steps

```bash
# 1. Image
aws ecr create-repository --repository-name sme-erp-web --region me-central-1
aws ecr get-login-password --region me-central-1 | docker login --username AWS --password-stdin <acct>.dkr.ecr.me-central-1.amazonaws.com
docker build -f docker/web/Dockerfile -t <acct>.dkr.ecr.me-central-1.amazonaws.com/sme-erp-web:1.0 .
docker push <acct>.dkr.ecr.me-central-1.amazonaws.com/sme-erp-web:1.0

# 2. Database
aws rds create-db-instance --db-instance-identifier alwadi-erp-db --engine postgres --engine-version 16 \
  --db-instance-class db.m6g.large --allocated-storage 100 --storage-type gp3 --storage-encrypted \
  --multi-az --backup-retention-period 14 --no-publicly-accessible \
  --master-username erpadmin --manage-master-user-password --db-name sme_erp \
  --vpc-security-group-ids <sg-rds> --db-subnet-group-name <private-subnets>

# 3. Secrets
aws secretsmanager create-secret --name sme-erp/django --secret-string \
  '{"DJANGO_SECRET_KEY":"...","FIELD_ENCRYPTION_KEY":"...","POWERBI_READER_PASSWORD":"..."}'

# 4. ECS cluster, task definition (port 8000, env DJANGO_SETTINGS_MODULE=config.settings.prod,
#    POSTGRES_HOST=<rds endpoint>, secrets from Secrets Manager), service behind the ALB, health check /health/
aws ecs create-cluster --cluster-name sme-erp
aws ecs register-task-definition --cli-input-json file://ecs-task.json
aws ecs create-service --cluster sme-erp --service-name web --task-definition sme-erp-web \
  --desired-count 2 --launch-type FARGATE --load-balancers targetGroupArn=<tg>,containerName=web,containerPort=8000 \
  --network-configuration "awsvpcConfiguration={subnets=[<private-a>,<private-b>],securityGroups=[<sg-app>]}"
```

5. Route 53 record `erp.alwadi.om` → ALB; ACM certificate for the domain.
6. Migrations run at container start (`docker/web/start.sh`). Load demo data with
   `aws ecs run-task ... --overrides '{"containerOverrides":[{"name":"web","command":["python","manage.py","seed_demo","--reset"]}]}'`.
7. Backups: RDS automated backups and snapshots (copy snapshots to me-south-1 for DR) plus the daily
   `backup.sh` export to S3 (`S3_BUCKET`, `AWS_REGION=me-central-1`).
8. Power BI gateway on EC2 → RDS endpoint, user `powerbi_reader` (SSL required).

## Option B – single EC2 instance with Docker Compose (lowest cost, pilot)

1. EC2 `t3.large` (Ubuntu 24.04) in me-central-1 with an encrypted EBS gp3 volume (KMS), Elastic IP, security group
   allowing 443 (and 22 from the office IP only).
2. Install Docker, `git clone` the repository, create `.env`, replace `certs/` with a Let's Encrypt certificate,
   `make up`.
3. Set `S3_BUCKET` and AWS credentials (or an instance role) so `backup.sh` copies every backup to S3.
4. Daily EBS snapshots via Amazon Data Lifecycle Manager.

## Indicative monthly cost (Option A, on-demand, USD – verify in the AWS calculator)

| Item | Approx. |
|---|---|
| ECS Fargate 2 × (1 vCPU, 2 GB) | 75 |
| ALB + WAF | 40 |
| RDS db.m6g.large Multi-AZ + 100 GB | 290 |
| S3, Secrets Manager, CloudWatch, ECR | 20 |
| Site-to-Site VPN (1 connection) | 40 |
| **Total** | **≈ 465 USD (≈ 180 OMR)**; Option B ≈ 90 USD |
