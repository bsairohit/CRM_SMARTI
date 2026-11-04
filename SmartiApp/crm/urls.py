from django.urls import path

from . import views

urlpatterns = [
    path("", views.upcoming_jobs, name="upcoming_jobs"),
    path("customers/", views.customer_list, name="customer_list"),
    path("customers/new/", views.customer_create, name="customer_create"),
    path("customers/<int:pk>/", views.customer_detail, name="customer_detail"),
    path("customers/<int:pk>/edit/", views.customer_edit, name="customer_edit"),
    path("customers/<int:pk>/status/", views.customer_update_status, name="customer_update_status"),
    path("staff/", views.staff_list, name="staff_list"),
    path("staff/new/", views.staff_create, name="staff_create"),
    path("staff/<int:pk>/", views.staff_detail, name="staff_detail"),
    path("staff/<int:pk>/edit/", views.staff_edit, name="staff_edit"),
    path("jobs/", views.job_list, name="job_list"),
    path("jobs/new/", views.job_create, name="job_create"),
    path("jobs/<int:pk>/edit/", views.job_edit, name="job_edit"),
    path("jobs/<int:pk>/status/", views.job_update_status, name="job_update_status"),
]
