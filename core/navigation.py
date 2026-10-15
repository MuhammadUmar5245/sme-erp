"""Sidebar navigation. Each item is shown only if its URL exists and the user holds the permission,
so menus follow the user's role (RBAC)."""
from django.urls import NoReverseMatch, reverse

NAVIGATION = [
    {
        "label": "Dashboard",
        "icon": "speedometer2",
        "items": [
            ("Dashboard", "core:dashboard", None),
            ("Analytics", "reports:dashboard", "reports.view_dashboard"),
        ],
    },
    {
        "label": "Inventory",
        "icon": "box-seam",
        "items": [
            ("Products", "inventory:product_list", "inventory.view_product"),
            ("Categories", "inventory:category_list", "inventory.view_category"),
            ("Warehouses", "inventory:warehouse_list", "inventory.view_warehouse"),
            ("Stock levels", "inventory:stock_levels", "inventory.view_stockmovement"),
            ("Stock movements", "inventory:movement_list", "inventory.view_stockmovement"),
        ],
    },
    {
        "label": "Purchasing",
        "icon": "truck",
        "items": [
            ("Suppliers", "purchasing:supplier_list", "purchasing.view_supplier"),
            ("Purchase orders", "purchasing:po_list", "purchasing.view_purchaseorder"),
            ("Goods receipts", "purchasing:grn_list", "purchasing.view_goodsreceipt"),
            ("Supplier bills", "purchasing:bill_list", "purchasing.view_supplierbill"),
        ],
    },
    {
        "label": "Sales",
        "icon": "cart3",
        "items": [
            ("Sales orders", "sales:order_list", "sales.view_salesorder"),
            ("Invoices", "sales:invoice_list", "sales.view_invoice"),
            ("Payments", "sales:payment_list", "sales.view_payment"),
            ("Credit notes", "sales:creditnote_list", "sales.view_creditnote"),
        ],
    },
    {
        "label": "CRM",
        "icon": "people",
        "items": [
            ("Customers", "crm:customer_list", "crm.view_customer"),
            ("Interactions", "crm:interaction_list", "crm.view_interaction"),
            ("Feedback", "crm:feedback_list", "crm.view_feedback"),
        ],
    },
    {
        "label": "Finance",
        "icon": "bank",
        "items": [
            ("Chart of accounts", "finance:account_list", "finance.view_account"),
            ("Journal entries", "finance:journal_list", "finance.view_journalentry"),
            ("Expenses", "finance:expense_list", "finance.view_expense"),
            ("Financial reports", "finance:reports", "finance.view_journalentry"),
        ],
    },
    {
        "label": "HR",
        "icon": "person-badge",
        "items": [
            ("Employees", "hr:employee_list", "hr.view_employee"),
            ("Departments", "hr:department_list", "hr.view_department"),
            ("Leave requests", "hr:leave_list", "hr.view_leaverequest"),
        ],
    },
    {
        "label": "Reports",
        "icon": "graph-up",
        "items": [
            ("Report builder", "reports:builder", "reports.view_dashboard"),
            ("Feasibility (ROI/NPV)", "feasibility:calculator", "feasibility.view_feasibilitystudy"),
        ],
    },
    {
        "label": "Data & integration",
        "icon": "arrow-left-right",
        "items": [
            ("Import wizard", "integrations:import_list", "integrations.add_importjob"),
            ("Exports", "integrations:export_index", "integrations.view_importjob"),
            ("POS API keys", "integrations:apikey_list", "integrations.view_apikey"),
        ],
    },
    {
        "label": "Administration",
        "icon": "shield-lock",
        "items": [
            ("Users", "accounts:user_list", "accounts.view_user"),
            ("Audit log", "accounts:audit_list", "accounts.view_auditlog"),
            ("User evaluation", "core:feedback_overview", "core.view_systemfeedback"),
            ("System monitoring", "monitoring:dashboard", "monitoring.view_requestmetric"),
            ("API docs", "swagger-ui", None),
        ],
    },
    {
        "label": "Help",
        "icon": "question-circle",
        "items": [("Help & support", "core:support", None)],
    },
]


def build_navigation(user, current_path=""):
    sections = []
    for section in NAVIGATION:
        items = []
        for label, url_name, perm in section["items"]:
            if perm and not user.has_perm(perm):
                continue
            try:
                url = reverse(url_name)
            except NoReverseMatch:
                continue
            active = url == current_path or (url != "/" and current_path.startswith(url))
            items.append({"label": label, "url": url, "active": active})
        if items:
            sections.append(
                {
                    "label": section["label"],
                    "icon": section["icon"],
                    "items": items,
                    "open": any(i["active"] for i in items),
                }
            )
    return sections
