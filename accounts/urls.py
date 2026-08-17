from django.urls import path

from . import views

urlpatterns = [
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("", views.post_login_redirect, name="post_login_redirect"),
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("profile/", views.profile, name="profile"),
    path("password-change/", views.PasswordChangeView.as_view(), name="password_change"),
]
