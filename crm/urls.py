from django.urls import path

from . import views

app_name = "crm"

urlpatterns = [
    path("customers/", views.CustomerListView.as_view(), name="customer_list"),
    path("customers/new/", views.CustomerCreateView.as_view(), name="customer_create"),
    path("customers/<int:pk>/", views.CustomerDetailView.as_view(), name="customer_detail"),
    path("customers/<int:pk>/edit/", views.CustomerUpdateView.as_view(), name="customer_update"),
    path("contacts/new/", views.ContactCreateView.as_view(), name="contact_create"),
    path("contacts/<int:pk>/edit/", views.ContactUpdateView.as_view(), name="contact_update"),
    path("interactions/", views.InteractionListView.as_view(), name="interaction_list"),
    path("interactions/new/", views.InteractionCreateView.as_view(), name="interaction_create"),
    path("interactions/<int:pk>/", views.InteractionDetailView.as_view(), name="interaction_detail"),
    path("interactions/<int:pk>/edit/", views.InteractionUpdateView.as_view(), name="interaction_update"),
    path("interactions/<int:pk>/close/", views.interaction_close, name="interaction_close"),
    path("feedback/", views.FeedbackListView.as_view(), name="feedback_list"),
    path("feedback/new/", views.FeedbackCreateView.as_view(), name="feedback_create"),
]
