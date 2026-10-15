from django.urls import path

from . import views

app_name = "sales"

urlpatterns = [
    path("orders/", views.OrderListView.as_view(), name="order_list"),
    path("orders/new/", views.order_create, name="order_create"),
    path("orders/<int:pk>/", views.OrderDetailView.as_view(), name="order_detail"),
    path("orders/<int:pk>/edit/", views.order_update, name="order_update"),
    path("orders/<int:pk>/confirm/", views.order_confirm, name="order_confirm"),
    path("orders/<int:pk>/cancel/", views.order_cancel, name="order_cancel"),
    path("orders/<int:pk>/invoice/", views.order_invoice, name="order_invoice"),
    path("invoices/", views.InvoiceListView.as_view(), name="invoice_list"),
    path("invoices/new/", views.invoice_create, name="invoice_create"),
    path("invoices/<int:pk>/", views.InvoiceDetailView.as_view(), name="invoice_detail"),
    path("invoices/<int:pk>/print/", views.invoice_print, name="invoice_print"),
    path("invoices/<int:pk>/pay/", views.invoice_pay, name="invoice_pay"),
    path("invoices/<int:pk>/credit/", views.invoice_credit, name="invoice_credit"),
    path("payments/", views.PaymentListView.as_view(), name="payment_list"),
    path("credit-notes/", views.CreditNoteListView.as_view(), name="creditnote_list"),
    path("credit-notes/<int:pk>/", views.CreditNoteDetailView.as_view(), name="creditnote_detail"),
]
