from django.urls import path

from . import users, views

urlpatterns = [
    path("csrf/", views.CsrfView.as_view(), name="auth-csrf"),
    path("login/", views.LoginView.as_view(), name="auth-login"),
    path("mfa/", views.MFAView.as_view(), name="auth-mfa"),
    path("mfa/enrol/", views.MFAEnrolView.as_view(), name="auth-mfa-enrol"),
    path("mfa/enrol/confirm/", views.MFAEnrolConfirmView.as_view(), name="auth-mfa-enrol-confirm"),
    path("mfa/recovery-codes/", views.RecoveryCodesView.as_view(), name="auth-mfa-recovery-codes"),
    path("logout/", views.LogoutView.as_view(), name="auth-logout"),
    path("me/", views.MeView.as_view(), name="auth-me"),
    path("password/", views.PasswordChangeView.as_view(), name="auth-password"),
    path("sessions/revoke-all/", views.RevokeAllSessionsView.as_view(), name="auth-revoke-all"),
    path("users/", users.UsersView.as_view(), name="auth-users"),
    path("users/<int:pk>/deactivate/", users.UserDeactivateView.as_view(), name="auth-user-deactivate"),
    path("users/<int:pk>/role/", users.UserRoleView.as_view(), name="auth-user-role"),
    path("users/<int:pk>/reset-password/", users.UserResetPasswordView.as_view(), name="auth-user-reset-password"),
    path("users/<int:pk>/reset-mfa/", users.UserResetMFAView.as_view(), name="auth-user-reset-mfa"),
]
