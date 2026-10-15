from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", auth_views.LoginView.as_view(redirect_authenticated_user=True), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("profile/", views.profile, name="profile"),
    path("2fa/setup/", views.two_factor_setup, name="2fa_setup"),
    path("2fa/verify/", views.two_factor_verify, name="2fa_verify"),
    path("2fa/disable/", views.two_factor_disable, name="2fa_disable"),
    path("users/", views.UserListView.as_view(), name="user_list"),
    path("users/new/", views.UserCreateView.as_view(), name="user_create"),
    path("users/<int:pk>/", views.UserDetailView.as_view(), name="user_detail"),
    path("users/<int:pk>/edit/", views.UserUpdateView.as_view(), name="user_update"),
    path("users/<int:pk>/reset-2fa/", views.user_reset_2fa, name="user_reset_2fa"),
    path("users/<int:pk>/unlock/", views.user_unlock, name="user_unlock"),
    path("audit/", views.AuditListView.as_view(), name="audit_list"),
    path("audit/<int:pk>/", views.AuditDetailView.as_view(), name="audit_detail"),
]
