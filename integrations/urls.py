from django.urls import path

from . import views

app_name = "integrations"

urlpatterns = [
    path("imports/", views.ImportListView.as_view(), name="import_list"),
    path("imports/upload/", views.import_upload, name="import_upload"),
    path("imports/<int:pk>/", views.import_detail, name="import_detail"),
    path("imports/<int:pk>/map/", views.import_map, name="import_map"),
    path("imports/<int:pk>/dry-run/", views.import_dry_run, name="import_dry_run"),
    path("imports/<int:pk>/commit/", views.import_commit, name="import_commit"),
    path("imports/<int:pk>/report.csv", views.import_report, name="import_report"),
    path("exports/", views.export_index, name="export_index"),
    path("exports/<str:entity>.<str:fmt>", views.export_download, name="export_download"),
    path("api-keys/", views.apikey_list, name="apikey_list"),
    path("api-keys/<int:pk>/revoke/", views.apikey_revoke, name="apikey_revoke"),
]
