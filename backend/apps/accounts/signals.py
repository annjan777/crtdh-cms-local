"""Signals other lanes listen to (e.g. mcp revokes OAuth tokens).

user_deactivated(sender=User, user=<User>)       - account switched off by an admin
user_sessions_revoked(sender=User, user=<User>)  - "sign out everywhere", MFA reset or deactivation
"""
from django.dispatch import Signal

user_deactivated = Signal()
user_sessions_revoked = Signal()
