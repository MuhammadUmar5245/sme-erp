# Phase 7 — Operations: backup, DR, monitoring and feasibility

1. scripts/backup.sh: pg_dump compressed, timestamped, 14-day retention, optional
   upload to S3/Azure Blob if env vars are set. scripts/restore.sh with confirmation.
   A cron service in docker-compose runs a daily backup. Document RPO = 24h and
   RTO = 4h in docs/disaster_recovery.md, with a tested restore procedure.
2. Monitoring app: middleware recording request count, response time and errors per
   endpoint. Monitoring page (Admin only) showing uptime, average/p95 response time,
   error rate, active users, DB size, last backup time and status. Expose the same data
   at /api/v1/reports/system-metrics/ for Power BI.
3. Feasibility app: calculator page for ROI, NPV, IRR, payback period and 5-year TCO.
   Input fields cover licence/subscription, implementation, training, maintenance,
   expected savings and discount rate. Prefill defaults for Al Wadi Trading (OMR), show a
   cash-flow chart, and export the results to PDF.
Tests for the financial formulas against known values. Commit.
