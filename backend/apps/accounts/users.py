"""User administration for role admins: list, create, deactivate, set role, reset MFA.

Passwords are never chosen by the admin or sent anywhere but this one response:
a new user gets a random temporary password (shown once) and must change it.
"""
import logging
import secrets

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import transaction
from django.db.models import Q
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.errors import CMSError

from . import mfa, sessions
from .models import UserSecurity
from .roles import ADMIN, ORDER, IsAdminRole
from .signals import user_deactivated
from .views import me_payload, require_mfa_enabled

logger = logging.getLogger("crtdh.security")
User = get_user_model()


def user_payload(user):
    return dict(me_payload(user), is_active=user.is_active,
                last_login=user.last_login.isoformat() if user.last_login else None)


def set_role(user, role):
    user.groups.remove(*Group.objects.filter(name__in=ORDER))
    user.groups.add(Group.objects.get_or_create(name=role)[0])


def active_admin_count(exclude=None):
    qs = User.objects.filter(is_active=True).filter(Q(is_superuser=True) | Q(groups__name=ADMIN)).distinct()
    if exclude is not None:
        qs = qs.exclude(pk=exclude.pk)
    return qs.count()


class CreateUserSerializer(serializers.Serializer):
    username = serializers.RegexField(r"^[A-Za-z0-9._-]{3,64}$")
    email = serializers.EmailField(max_length=254)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    role = serializers.ChoiceField(choices=ORDER)

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("That username is taken.")
        return value


class RoleSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=ORDER)


class _AdminView(APIView):
    permission_classes = [IsAdminRole]

    def get_target(self, pk):
        user = User.objects.filter(pk=pk).first()
        if not user:
            raise CMSError("CMS_NOT_FOUND", "No such user.", fix="Reload the user list.")
        return user


class UsersView(_AdminView):
    def get(self, request):
        users = User.objects.order_by("username").prefetch_related("groups")
        return Response({"results": [user_payload(u) for u in users]})

    def post(self, request):
        ser = CreateUserSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        temp = secrets.token_urlsafe(18)
        with transaction.atomic():
            user = User.objects.create_user(d["username"], d["email"], temp,
                                            first_name=d.get("first_name", ""), last_name=d.get("last_name", ""))
            set_role(user, d["role"])
            UserSecurity.objects.create(user=user, must_change_password=True)
        logger.info("user created username=%s role=%s by=%s", user.username, d["role"], request.user.username)
        return Response(dict(user_payload(user), temporary_password=temp), status=status.HTTP_201_CREATED)


class UserDeactivateView(_AdminView):
    def post(self, request, pk):
        user = self.get_target(pk)
        if user.pk == request.user.pk:
            raise CMSError("CMS_VALIDATION", "You cannot deactivate yourself.", fix="Ask another admin.")
        if active_admin_count(exclude=user) == 0:
            raise CMSError("CMS_VALIDATION", "This is the last admin.", fix="Make someone else admin first.")
        user.is_active = False
        user.save(update_fields=["is_active"])
        sessions.revoke_all(user)
        user_deactivated.send(sender=User, user=user)
        logger.info("user deactivated username=%s by=%s", user.username, request.user.username)
        return Response(user_payload(user))


class UserRoleView(_AdminView):
    def post(self, request, pk):
        user = self.get_target(pk)
        ser = RoleSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        role = ser.validated_data["role"]
        if user.is_superuser:
            raise CMSError("CMS_VALIDATION", "Superuser roles are managed on the server.", fix="Pick another user.")
        if role != ADMIN and active_admin_count(exclude=user) == 0:
            raise CMSError("CMS_VALIDATION", "This is the last admin.", fix="Make someone else admin first.")
        set_role(user, role)
        logger.info("role set username=%s role=%s by=%s", user.username, role, request.user.username)
        return Response(user_payload(user))


class UserResetMFAView(_AdminView):
    """For a lost phone: clears MFA, signs the user out and replaces the password with a one-time
    temporary password (shown once). Keeping the old password would let anyone who knows it (a leak,
    or the person who took the phone) enrol their own authenticator at the next sign-in."""

    def post(self, request, pk):
        require_mfa_enabled()
        user = self.get_target(pk)
        if user.pk == request.user.pk:
            raise CMSError("CMS_VALIDATION", "Another admin must reset your MFA.", fix="Ask another admin.")
        temp = secrets.token_urlsafe(18)
        with transaction.atomic():
            mfa.reset(user)
            user.set_password(temp)
            user.save(update_fields=["password"])
            UserSecurity.objects.update_or_create(user=user, defaults={"must_change_password": True})
        sessions.revoke_all(user)
        logger.info("mfa reset username=%s by=%s", user.username, request.user.username)
        return Response(dict(user_payload(user), temporary_password=temp))


class UserResetPasswordView(_AdminView):
    """For a forgotten password: new one-time temporary password (shown once), signs the user out.
    The user must change it before doing anything else."""

    def post(self, request, pk):
        user = self.get_target(pk)
        if user.pk == request.user.pk:
            raise CMSError("CMS_VALIDATION", "Use the change-password screen for your own account.",
                           fix="Go to your account settings.")
        temp = secrets.token_urlsafe(18)
        user.set_password(temp)
        user.save(update_fields=["password"])
        UserSecurity.objects.update_or_create(user=user, defaults={"must_change_password": True})
        sessions.revoke_all(user)
        # nosemgrep: python.lang.security.audit.logging.logger-credential-leak.python-logger-credential-disclosure -- logs usernames only; the temporary password is never logged
        logger.info("password reset username=%s by=%s", user.username, request.user.username)
        return Response(dict(user_payload(user), temporary_password=temp))
