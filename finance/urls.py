from django.urls import path

from . import views

app_name = "finance"

urlpatterns = [
    path("accounts/", views.AccountListView.as_view(), name="account_list"),
    path("accounts/new/", views.AccountCreateView.as_view(), name="account_create"),
    path("accounts/<int:pk>/", views.AccountDetailView.as_view(), name="account_detail"),
    path("accounts/<int:pk>/edit/", views.AccountUpdateView.as_view(), name="account_update"),
    path("journals/", views.JournalListView.as_view(), name="journal_list"),
    path("journals/new/", views.journal_create, name="journal_create"),
    path("journals/<int:pk>/", views.JournalDetailView.as_view(), name="journal_detail"),
    path("expenses/", views.ExpenseListView.as_view(), name="expense_list"),
    path("expenses/new/", views.ExpenseCreateView.as_view(), name="expense_create"),
    path("expenses/<int:pk>/", views.ExpenseDetailView.as_view(), name="expense_detail"),
    path("reports/", views.reports, name="reports"),
]
