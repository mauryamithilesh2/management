"""
Reusable authorization helpers for the Employee Task Management System.

Phase 3 introduces exactly one new authorization rule that matters for the
whole app going forward: "some views are admin-only". Every future
admin-only feature (user management, task management, admin requests)
should reuse `admin_required` / `AdminRequiredMixin` from here instead of
re-implementing the role check inline in each view.

Design notes:
- Anonymous users are redirected to the login page (302), exactly like any
  other `@login_required` view in this project.
- Authenticated users who are logged in but are not ADMIN get an HTTP 403
  (PermissionDenied), because they *are* allowed to use the system - they
  just aren't allowed to use *this* view. This is different from being
  unauthenticated, and Django's default 403 handling is sufficient for a
  server-side, non-frontend-reliant rejection.
- Nothing here trusts request data (GET/POST params, hidden form fields,
  headers, etc.) to determine the role. The role always comes from
  `request.user`, which is populated by Django's session-backed
  AuthenticationMiddleware from the authenticated user's database record.
"""

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import PermissionDenied
from functools import wraps


def admin_required(view_func):
    """
    Decorator for function-based views that restricts access to
    authenticated users whose `role` is ADMIN.

    Usage:
        @admin_required
        def admin_dashboard(request):
            ...
    """

    @login_required
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_admin_role:
            raise PermissionDenied("Admin access required.")
        return view_func(request, *args, **kwargs)

    return _wrapped_view


class AdminRequiredMixin(AccessMixin):
    """
    Class-based-view equivalent of `admin_required`, ready for future
    admin-only functionality that is implemented as a CBV (e.g.
    ListView/DetailView for user or task management).

    Usage:
        class UserManagementView(AdminRequiredMixin, ListView):
            ...

    Reuses Django's `AccessMixin` so the "not logged in -> redirect to
    login" behaviour matches the rest of the project, and only adds the
    role check on top.
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.is_admin_role:
            raise PermissionDenied("Admin access required.")
        return super().dispatch(request, *args, **kwargs)
