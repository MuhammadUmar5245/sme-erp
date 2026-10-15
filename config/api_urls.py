"""REST API v1 routes (/api/v1/). Every viewset enforces Django model permissions (RBAC)."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from accounts import api as accounts_api
from crm import api as crm_api
from finance import api as finance_api
from hr import api as hr_api
from inventory import api as inventory_api
from purchasing import api as purchasing_api
from reports import api as reports_api
from sales import api as sales_api

router = DefaultRouter()
router.register("accounts/users", accounts_api.UserViewSet, basename="user")
router.register("accounts/audit-logs", accounts_api.AuditLogViewSet, basename="auditlog")
router.register("inventory/categories", inventory_api.CategoryViewSet, basename="category")
router.register("inventory/warehouses", inventory_api.WarehouseViewSet, basename="warehouse")
router.register("inventory/products", inventory_api.ProductViewSet, basename="product")
router.register("inventory/stock-movements", inventory_api.StockMovementViewSet, basename="stockmovement")
router.register("purchasing/suppliers", purchasing_api.SupplierViewSet, basename="supplier")
router.register("purchasing/purchase-orders", purchasing_api.PurchaseOrderViewSet, basename="purchaseorder")
router.register("purchasing/goods-receipts", purchasing_api.GoodsReceiptViewSet, basename="goodsreceipt")
router.register("purchasing/bills", purchasing_api.SupplierBillViewSet, basename="supplierbill")
router.register("purchasing/supplier-payments", purchasing_api.SupplierPaymentViewSet, basename="supplierpayment")
router.register("sales/orders", sales_api.SalesOrderViewSet, basename="salesorder")
router.register("sales/invoices", sales_api.InvoiceViewSet, basename="invoice")
router.register("sales/payments", sales_api.PaymentViewSet, basename="payment")
router.register("sales/credit-notes", sales_api.CreditNoteViewSet, basename="creditnote")
router.register("crm/customers", crm_api.CustomerViewSet, basename="customer")
router.register("crm/contacts", crm_api.ContactViewSet, basename="contact")
router.register("crm/interactions", crm_api.InteractionViewSet, basename="interaction")
router.register("crm/feedback", crm_api.FeedbackViewSet, basename="feedback")
router.register("finance/accounts", finance_api.AccountViewSet, basename="account")
router.register("finance/journal-entries", finance_api.JournalEntryViewSet, basename="journalentry")
router.register("finance/expenses", finance_api.ExpenseViewSet, basename="expense")
router.register("hr/departments", hr_api.DepartmentViewSet, basename="department")
router.register("hr/employees", hr_api.EmployeeViewSet, basename="employee")
router.register("hr/leave-requests", hr_api.LeaveRequestViewSet, basename="leaverequest")
# Power BI reporting datasets (read-only views of schema "reporting").
for slug, viewset in reports_api.REPORTING_VIEWSETS.items():
    router.register(f"reports/{slug}", viewset, basename=f"report-{slug}")

urlpatterns = [
    path("auth/token/", accounts_api.ObtainTokenView.as_view(), name="api-token"),
    path("reports/", reports_api.DatasetIndexView.as_view(), name="report-index"),
    path("reports/kpis/", reports_api.KPIView.as_view(), name="report-kpis"),
    path("finance/reports/<slug:name>/", finance_api.FinancialReportView.as_view(), name="finance-report"),
    path("", include(router.urls)),
]
