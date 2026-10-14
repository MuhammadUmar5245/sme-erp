"""API permission classes. Access always follows Django model permissions held by the role groups."""
from rest_framework import permissions


class ModelPermissions(permissions.DjangoModelPermissions):
    """Like DjangoModelPermissions but reads also require the `view_<model>` permission."""

    perms_map = {
        **permissions.DjangoModelPermissions.perms_map,
        "GET": ["%(app_label)s.view_%(model_name)s"],
        "HEAD": ["%(app_label)s.view_%(model_name)s"],
        "OPTIONS": ["%(app_label)s.view_%(model_name)s"],
    }


def has_perms(*perms):
    """Permission class factory for APIViews that are not tied to one model queryset."""

    class _HasPerms(permissions.BasePermission):
        required = perms

        def has_permission(self, request, view):
            user = request.user
            return bool(user and user.is_authenticated and user.has_perms(self.required))

    _HasPerms.__name__ = "HasPerms_" + "_".join(p.replace(".", "_") for p in perms)
    return _HasPerms
