from django.urls import path

from . import views

app_name = "purchasing"

urlpatterns = [
    path("suppliers/", views.SupplierListView.as_view(), name="supplier_list"),
    path("suppliers/new/", views.SupplierCreateView.as_view(), name="supplier_create"),
    path("suppliers/<int:pk>/", views.SupplierDetailView.as_view(), name="supplier_detail"),
    path("suppliers/<int:pk>/edit/", views.SupplierUpdateView.as_view(), name="supplier_update"),
    path("orders/", views.POListView.as_view(), name="po_list"),
    path("orders/new/", views.po_create, name="po_create"),
    path("orders/<int:pk>/", views.PODetailView.as_view(), name="po_detail"),
    path("orders/<int:pk>/edit/", views.po_update, name="po_update"),
    path("orders/<int:pk>/approve/", views.po_approve, name="po_approve"),
    path("orders/<int:pk>/cancel/", views.po_cancel, name="po_cancel"),
    path("orders/<int:pk>/receive/", views.po_receive, name="po_receive"),
    path("orders/<int:pk>/bill/", views.po_bill, name="po_bill"),
    path("receipts/", views.GRNListView.as_view(), name="grn_list"),
    path("receipts/<int:pk>/", views.GRNDetailView.as_view(), name="grn_detail"),
    path("bills/", views.BillListView.as_view(), name="bill_list"),
    path("bills/<int:pk>/", views.BillDetailView.as_view(), name="bill_detail"),
    path("bills/<int:pk>/pay/", views.bill_pay, name="bill_pay"),
]
