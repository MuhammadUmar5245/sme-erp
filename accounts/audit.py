"""Automatic audit logging of create/update/delete on business models (via model signals).

The acting user and client IP come from the current request (CurrentRequestMiddleware). Bulk data
loads (seed, imports) can switch logging off with `with audit.disabled(): ...`.
"""
import contextlib
import contextvars
import datetime
import decimal
import uuid

from django.conf import settings
from django.db.models.signals import post_delete, post_save, pre_save

_request_ctx = contextvars.ContextVar("audit_request", default=None)
_disabled = contextvars.ContextVar("audit_disabled", default=False)

IGNORED_FIELDS = {"password", "last_login", "updated_at", "created_at"}
EXCLUDED_MODELS = {"accounts.auditlog", "auth.permission", "monitoring.requestmetric", "monitoring.healthprobe",
                   "core.sequence"}


def set_request_context(request):
    return _request_ctx.set(request)


def reset_request_context(token):
    _request_ctx.reset(token)


@contextlib.contextmanager
def disabled():
    token = _disabled.set(True)
    try:
        yield
    finally:
        _disabled.reset(token)


def _current_actor():
    request = _request_ctx.get()
    if request is None:
        return None, None
    from .middleware import get_client_ip

    user = getattr(request, "user", None)
    if user is not None and not user.is_authenticated:
        user = None
    return user, get_client_ip(request)


def _jsonable(value):
    if isinstance(value, (datetime.date, datetime.datetime, datetime.time)):
        return value.isoformat()
    if isinstance(value, (decimal.Decimal, uuid.UUID)):
        return str(value)
    if isinstance(value, (bytes, memoryview)):
        return "<binary>"
    if isinstance(value, (dict, list, str, int, float, bool)) or value is None:
        return value
    return str(value)


def _snapshot(instance):
    data = {}
    for field in instance._meta.concrete_fields:
        if field.name in IGNORED_FIELDS:
            continue
        data[field.attname] = _jsonable(field.value_from_object(instance))
    return data


def _label(sender):
    return f"{sender._meta.app_label}.{sender._meta.model_name}"


def _is_audited(sender):
    if _disabled.get():
        return False
    label = _label(sender)
    return sender._meta.app_label in settings.AUDIT_LOG_APPS and label not in EXCLUDED_MODELS


def write(action, model_label, object_id="", object_repr="", changes=None, user=None, ip=None):
    from .models import AuditLog

    if user is None and ip is None:
        user, ip = _current_actor()
    return AuditLog.objects.create(
        user=user if user is not None and user.pk else None,
        user_email=getattr(user, "email", "") or "",
        action=action,
        model=model_label,
        object_id=str(object_id or ""),
        object_repr=str(object_repr)[:200],
        changes=changes or {},
        ip_address=ip,
    )


def _pre_save(sender, instance, raw=False, **kwargs):
    if raw or not _is_audited(sender) or instance.pk is None:
        return
    old = sender._default_manager.filter(pk=instance.pk).first()
    instance._audit_before = _snapshot(old) if old is not None else None


def _post_save(sender, instance, created, raw=False, **kwargs):
    if raw or not _is_audited(sender):
        return
    after = _snapshot(instance)
    before = getattr(instance, "_audit_before", None)
    if created or before is None:
        changes = {key: [None, value] for key, value in after.items()}
        action = "create"
    else:
        changes = {key: [before.get(key), value] for key, value in after.items() if before.get(key) != value}
        if not changes:
            return
        action = "update"
    write(action, _label(sender), instance.pk, instance, changes)
    instance._audit_before = after


def _post_delete(sender, instance, **kwargs):
    if not _is_audited(sender):
        return
    write("delete", _label(sender), instance.pk, instance, {k: [v, None] for k, v in _snapshot(instance).items()})


def connect():
    pre_save.connect(_pre_save, dispatch_uid="audit_pre_save")
    post_save.connect(_post_save, dispatch_uid="audit_post_save")
    post_delete.connect(_post_delete, dispatch_uid="audit_post_delete")

    from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed

    def on_login(sender, request, user, **kwargs):
        from .middleware import get_client_ip

        write("login", "accounts.user", user.pk, user, user=user, ip=get_client_ip(request))

    def on_logout(sender, request, user, **kwargs):
        from .middleware import get_client_ip

        if user is not None:
            write("logout", "accounts.user", user.pk, user, user=user, ip=get_client_ip(request))

    def on_failed(sender, credentials, request=None, **kwargs):
        from .middleware import get_client_ip

        email = str(credentials.get("username") or credentials.get("email") or "")
        from .models import AuditLog

        AuditLog.objects.create(
            action="login_failed",
            model="accounts.user",
            user_email=email[:254],
            object_repr=email[:200],
            ip_address=get_client_ip(request) if request is not None else None,
        )

    user_logged_in.connect(on_login, dispatch_uid="audit_login", weak=False)
    user_logged_out.connect(on_logout, dispatch_uid="audit_logout", weak=False)
    user_login_failed.connect(on_failed, dispatch_uid="audit_login_failed", weak=False)
