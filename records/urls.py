from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("register/", views.register_patient, name="register_patient"),
    path("register/staff/", views.register_clinic_staff, name="register_clinic_staff"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    path("password-change/", auth_views.PasswordChangeView.as_view(
        template_name="records/password_change.html",
        success_url="/password-change/done/",
    ), name="password_change"),
    path("password-change/done/", auth_views.PasswordChangeDoneView.as_view(
        template_name="records/password_change_done.html",
    ), name="password_change_done"),

    path("dashboard/", views.patient_dashboard, name="patient_dashboard"),
    path("dashboard/edit-profile/", views.edit_my_profile, name="edit_my_profile"),
    path("ask/", views.ask_assistant, name="ask_assistant"),
    path("edit-request/<int:request_id>/<str:decision>/", views.review_edit_request, name="review_edit_request"),

    path("clinic/", views.clinic_dashboard, name="clinic_dashboard"),
    path("clinic/my-patients/", views.my_patients, name="my_patients"),
    path("clinic/patient/<uuid:health_id>/add-visit/", views.add_visit, name="add_visit"),
    path("clinic/patient/<uuid:health_id>/edit/", views.edit_patient, name="edit_patient"),

    path("govt/", views.govt_dashboard, name="govt_dashboard"),
    path("govt/staff/<int:profile_id>/<str:decision>/", views.review_staff_request, name="review_staff_request"),
]