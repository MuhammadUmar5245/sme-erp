"""Role-based access control: the 7 role groups and the model permissions each one holds.

Permissions are expressed per app (applies to every model of the app) or per model, with the
actions view/add/change/delete, plus custom permissions (e.g. purchasing.approve_purchaseorder).
The mapping is applied by a data migration and re-applied after every `migrate`, so modules added
later automatically get their permissions assigned.
"""

ADMIN = "Admin"
MANAGER = "Manager"
ACCOUNTANT = "Accountant"
SALES_OFFICER = "SalesOfficer"
STOREKEEPER = "Storekeeper"
HR_OFFICER = "HROfficer"
VIEWER = "Viewer"

ROLES = [ADMIN, MANAGER, ACCOUNTANT, SALES_OFFICER, STOREKEEPER, HR_OFFICER, VIEWER]

# TOTP two-factor authentication is mandatory for these roles (optional for everyone else).
MFA_REQUIRED_ROLES = [ADMIN, ACCOUNTANT]

ALL = ("view", "add", "change", "delete")
EDIT = ("view", "add", "change")
VIEW = ("view",)

BUSINESS_APPS = [
    "inventory",
    "purchasing",
    "sales",
    "crm",
    "finance",
    "hr",
    "reports",
    "integrations",
    "feasibility",
]

ROLE_DESCRIPTIONS = {
    ADMIN: "Full access including users, roles, audit log and system monitoring.",
    MANAGER: "Runs operations: approves purchase orders and leave, sees all business data.",
    ACCOUNTANT: "Finance, invoicing, payments, supplier bills, VAT and financial reports.",
    SALES_OFFICER: "Customers, CRM, sales orders, invoices and customer payments.",
    STOREKEEPER: "Products, warehouses, stock movements and goods receipts.",
    HR_OFFICER: "Employees, departments and leave requests.",
    VIEWER: "Read-only access to business data and dashboards.",
}

# role -> {"app" or "app.model": actions} ; "extra" -> list of "app.codename"
ROLE_PERMISSIONS = {
    ADMIN: "__all__",
    MANAGER: {
        "inventory": ALL,
        "purchasing": EDIT,
        "sales": EDIT,
        "crm": ALL,
        "finance": VIEW,
        "hr": EDIT,
        "reports": VIEW,
        "integrations": EDIT,
        "feasibility": ALL,
        "accounts.user": VIEW,
        "extra": [
            "purchasing.approve_purchaseorder",
            "hr.approve_leaverequest",
            "reports.view_dashboard",
            "reports.view_powerbi_api",
        ],
    },
    ACCOUNTANT: {
        "finance": ALL,
        "sales.invoice": EDIT,
        "sales.invoiceline": EDIT,
        "sales.payment": EDIT,
        "sales.creditnote": EDIT,
        "sales.creditnoteline": EDIT,
        "sales.salesorder": VIEW,
        "sales.salesorderline": VIEW,
        "purchasing.supplier": EDIT,
        "purchasing.purchaseorder": VIEW,
        "purchasing.purchaseorderline": VIEW,
        "purchasing.goodsreceipt": VIEW,
        "purchasing.supplierbill": EDIT,
        "purchasing.supplierpayment": EDIT,
        "crm.customer": VIEW,
        "inventory": VIEW,
        "reports": VIEW,
        "integrations": EDIT,
        "feasibility": ALL,
        "extra": ["reports.view_dashboard", "reports.view_powerbi_api"],
    },
    SALES_OFFICER: {
        "crm": EDIT,
        "sales.salesorder": EDIT,
        "sales.salesorderline": EDIT,
        "sales.invoice": EDIT,
        "sales.invoiceline": EDIT,
        "sales.payment": ("view", "add"),
        "sales.creditnote": VIEW,
        "inventory.product": VIEW,
        "inventory.category": VIEW,
        "inventory.warehouse": VIEW,
        "inventory.stockmovement": VIEW,
        "extra": ["reports.view_dashboard"],
    },
    STOREKEEPER: {
        "inventory": ALL,
        "purchasing.supplier": VIEW,
        "purchasing.purchaseorder": VIEW,
        "purchasing.purchaseorderline": VIEW,
        "purchasing.goodsreceipt": EDIT,
        "purchasing.goodsreceiptline": EDIT,
        "sales.salesorder": VIEW,
        "extra": ["purchasing.receive_purchaseorder"],
    },
    HR_OFFICER: {
        "hr": ALL,
        "extra": ["hr.approve_leaverequest"],
    },
    VIEWER: {
        "inventory": VIEW,
        "purchasing": VIEW,
        "sales": VIEW,
        "crm": VIEW,
        "finance": VIEW,
        "hr.department": VIEW,
        "extra": ["reports.view_dashboard", "reports.view_powerbi_api"],
    },
}
