"""Accounts business logic: role/permission sync, user management, TOTP two-factor authentication."""
import io

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.auth.password_validation import validate_password
from django.db import transaction

from .roles import ROLE_PERMISSIONS, ROLES


def _permissions_for(spec):
    """Resolve a role spec ({"app": actions, "app.model": actions, "extra": [...]}) to Permission objects."""
    if spec == "__all__":
        return list(Permission.objects.all())
    perms = []
    for key, actions in spec.items():
        if key == "extra":
            for full in actions:
                app_label, codename = full.split(".", 1)
                perms.extend(Permission.objects.filter(content_type__app_label=app_label, codename=codename))
            continue
        if "." in key:
            app_label, model = key.split(".", 1)
            qs = Permission.objects.filter(content_type__app_label=app_label, content_type__model=model)
        else:
            app_label, model = key, None
            qs = Permission.objects.filter(content_type__app_label=app_label)
        wanted = {f"{action}_" for action in actions}
        for perm in qs.select_related("content_type"):
            model_name = perm.content_type.model
            if any(perm.codename == f"{prefix}{model_name}" for prefix in wanted):
                perms.append(perm)
    return perms


def sync_role_permissions(using="default"):
    """Create the 7 role groups and grant each the permissions defined in roles.py.

    Idempotent and additive: permissions an administrator added manually are kept.
    """
    groups = {}
    for role in ROLES:
        group, _ = Group.objects.using(using).get_or_create(name=role)
        perms = _permissions_for(ROLE_PERMISSIONS[role])
        if perms:
            group.permissions.add(*perms)
        groups[role] = group
    return groups


@transaction.atomic
def create_user(email, password, roles=(), **fields):
    """Create a user with the password policy enforced and assign role groups."""
    User = get_user_model()
    user = User(email=User.objects.normalize_email(email).lower(), **fields)
    validate_password(password, user)
    user.set_password(password)
    user.save()
    set_roles(user, roles)
    return user


def set_roles(user, roles):
    groups = list(Group.objects.filter(name__in=roles))
    user.groups.set(groups)
    # Admins get Django admin-site access.
    is_admin = "Admin" in roles or user.is_superuser
    if user.is_staff != is_admin:
        user.is_staff = is_admin
        user.save(update_fields=["is_staff"])
    return user


def unlock_user(user):
    """Clear django-axes lockout records for this account."""
    from axes.utils import reset

    return reset(username=user.email)


def is_locked_out(user):
    from axes.models import AccessAttempt
    from django.conf import settings

    return AccessAttempt.objects.filter(
        username__iexact=user.email, failures_since_start__gte=settings.AXES_FAILURE_LIMIT
    ).exists()


# ---- TOTP two-factor authentication ---------------------------------------------------------


def get_or_create_pending_device(user):
    """Return the user's unconfirmed TOTP device (created on first visit to the enrolment page)."""
    from django_otp.plugins.otp_totp.models import TOTPDevice

    device = TOTPDevice.objects.filter(user=user, confirmed=False).first()
    if device is None:
        device = TOTPDevice.objects.create(user=user, name="Authenticator app", confirmed=False)
    return device


def qr_code_svg(device):
    """QR code (SVG markup) of the otpauth:// URI for scanning with an authenticator app."""
    import qrcode
    import qrcode.image.svg

    image = qrcode.make(device.config_url, image_factory=qrcode.image.svg.SvgPathImage, box_size=8)
    buffer = io.BytesIO()
    image.save(buffer)
    return buffer.getvalue().decode()


def confirm_device(device, token):
    """Verify the first token from the app; on success the device becomes the user's 2FA device."""
    from django_otp.plugins.otp_totp.models import TOTPDevice

    if not device.verify_token(str(token).strip()):
        return False
    with transaction.atomic():
        TOTPDevice.objects.filter(user=device.user, confirmed=True).exclude(pk=device.pk).delete()
        device.confirmed = True
        device.save()
    return True


def verify_user_token(user, token):
    """Return the confirmed device matching the token, or None."""
    from django_otp import match_token

    return match_token(user, str(token).strip())


def reset_two_factor(user):
    """Remove all OTP devices (admin action, e.g. lost phone). Mandatory roles must re-enrol."""
    from django_otp.plugins.otp_totp.models import TOTPDevice

    deleted, _ = TOTPDevice.objects.filter(user=user).delete()
    return deleted


def has_two_factor(user):
    from django_otp import user_has_device

    return user_has_device(user)

