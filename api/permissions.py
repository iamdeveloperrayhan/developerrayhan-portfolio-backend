"""
B-13. Custom permission class.

Safe methods (GET/HEAD/OPTIONS) are open to everyone. Any write method is
allowed only for the authenticated superuser (the single site owner). We do
NOT rely on IsAdminUser alone, and the check lives in the backend (S-1).
"""
from rest_framework import permissions


def is_owner(user):
    return bool(user and user.is_authenticated and user.is_superuser)


class IsOwnerOrReadOnly(permissions.BasePermission):
    message = "Only the site owner may perform this action."

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return is_owner(request.user)

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return is_owner(request.user)


class IsOwner(permissions.BasePermission):
    """Owner-only for every method (used by dashboard/moderation endpoints)."""

    message = "Only the site owner may access this resource."

    def has_permission(self, request, view):
        return is_owner(request.user)

    def has_object_permission(self, request, view, obj):
        return is_owner(request.user)
