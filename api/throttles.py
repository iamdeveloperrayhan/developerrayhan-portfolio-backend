"""
B-17. Scoped throttles.

Global anonymous throttling (20/min) is configured via DEFAULT_THROTTLE_RATES.
The classes below tie specific actions to their scope and key comment/contact
throttling to the client IP so a single visitor cannot spam them.
"""
from rest_framework.throttling import ScopedRateThrottle, SimpleRateThrottle


class CommentThrottle(SimpleRateThrottle):
    scope = "comment"

    def get_cache_key(self, request, view):
        if request.method != "POST":
            return None
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),  # per IP
        }


class ContactThrottle(SimpleRateThrottle):
    scope = "contact"

    def get_cache_key(self, request, view):
        if request.method != "POST":
            return None
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),  # per IP
        }


class LikeThrottle(ScopedRateThrottle):
    """30/min on the like toggle (keyed by the ScopedRateThrottle default)."""

    scope = "like"
