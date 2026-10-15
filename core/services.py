"""Home dashboard data. Each module contributes widgets only if installed and permitted."""
from django.apps import apps


def dashboard_context(user):
    context = {}
    if apps.is_installed("inventory") and user.has_perm("inventory.view_product"):
        from inventory.services import low_stock_products

        context["low_stock"] = low_stock_products()[:10]
    if apps.is_installed("reports") and user.has_perm("reports.view_dashboard"):
        from reports.services import kpis

        context["kpis"] = kpis()
    return context
