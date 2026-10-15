"""Load test: 50 concurrent users against the HTTPS stack (report 2.3.2 performance, 3.5.5 capacity).

Run (from the project folder, with the stack up and demo data seeded):
    docker run --rm --network sme-erp_default -v "%cd%/loadtest:/loadtest" -w /loadtest python:3.12-slim \
        sh -c "pip install -q locust==2.32.4 && locust -f locustfile.py --headless -u 50 -r 5 -t 3m \
               --host https://nginx --csv results/run"
Environment: LOADTEST_USER / LOADTEST_PASSWORD (default viewer@alwadi.om), POWERBI_TOKEN for API users.
"""
import os
import random
import re

import urllib3
from locust import HttpUser, between, task

urllib3.disable_warnings()  # self-signed certificate in the local stack

EMAIL = os.environ.get("LOADTEST_USER", "viewer@alwadi.om")
PASSWORD = os.environ.get("LOADTEST_PASSWORD", "AlWadi-Demo-2026!")
TOKEN = os.environ.get("POWERBI_TOKEN", "")
HEADERS = {"Host": "localhost", "Referer": "https://localhost/"}


class OfficeUser(HttpUser):
    """A staff member browsing the ERP (dashboard, lists, detail pages, search)."""

    weight = 4
    wait_time = between(1, 4)

    def on_start(self):
        self.client.verify = False
        self.client.headers.update(HEADERS)
        page = self.client.get("/accounts/login/", name="login page")
        token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', page.text)
        self.client.post("/accounts/login/", name="login",
                         data={"username": EMAIL, "password": PASSWORD,
                               "csrfmiddlewaretoken": token.group(1) if token else ""},
                         headers={"Referer": "https://localhost/accounts/login/"})

    @task(3)
    def dashboard(self):
        self.client.get("/", name="home dashboard")

    @task(2)
    def analytics(self):
        self.client.get("/reports/dashboard/", name="analytics dashboard")
        self.client.get("/reports/dashboard/data/", name="analytics chart data")

    @task(4)
    def invoices(self):
        page = random.randint(1, 50)
        self.client.get(f"/sales/invoices/?page={page}", name="invoice list")

    @task(3)
    def products(self):
        self.client.get(f"/inventory/products/?q={random.choice(['rice', 'tea', 'oil', 'dates', ''])}",
                        name="product search")

    @task(2)
    def stock_levels(self):
        self.client.get("/inventory/stock/", name="stock levels")

    @task(2)
    def customer_360(self):
        self.client.get(f"/crm/customers/{random.randint(1, 300)}/", name="customer 360")

    @task(1)
    def reports(self):
        self.client.get("/finance/reports/?report=ar", name="AR aging report")


class PowerBIUser(HttpUser):
    """Power BI refresh / Web connector paging through the reporting API with a token."""

    weight = 1
    wait_time = between(2, 6)

    def on_start(self):
        self.client.verify = False
        self.client.headers.update(HEADERS)
        if TOKEN:
            self.client.headers["Authorization"] = f"Token {TOKEN}"

    @task(3)
    def fact_sales_page(self):
        self.client.get(f"/api/v1/reports/fact-sales/?page_size=1000&page={random.randint(1, 15)}",
                        name="API fact-sales page")

    @task(1)
    def kpis(self):
        self.client.get("/api/v1/reports/kpis/", name="API kpis")

    @task(1)
    def inventory(self):
        self.client.get("/api/v1/reports/fact-inventory-daily/?page_size=1000&date_from=2026-10-01",
                        name="API inventory daily")
