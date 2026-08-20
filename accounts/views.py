from django.contrib import messages
from tasks.views import send_via_brevo
from django.contrib.auth import get_user_model
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from tasks.models import Task
from .forms import (
    AdminCreateEmployeeForm,
    AdminUserEditForm,
    ProfileForm,
    StyledAuthenticationForm,
    StyledPasswordChangeForm,
)
from .permissions import admin_required
import logging
logger = logging.getLogger(__name__)
User = get_user_model()

def landing(request):
    """Public system landing page with live operational metrics."""
    total_users = User.objects.count()
    total_employees = User.objects.filter(role=User.Role.EMPLOYEE).count()

    active_users = User.objects.filter(is_active=True).count()
    total_tasks = Task.objects.count()
    todo_tasks = Task.objects.filter(status=Task.Status.TODO).count()
    in_progress_tasks = Task.objects.filter(status=Task.Status.IN_PROGRESS).count()
    completed_tasks = Task.objects.filter(status=Task.Status.COMPLETED).count()

    context = {
        "user": request.user,
        "total_users": total_users,
        "total_employees": total_employees,
        "active_users": active_users,
        "total_tasks": total_tasks,
        "todo_tasks": todo_tasks,
        "in_progress_tasks": in_progress_tasks,
        "completed_tasks": completed_tasks,
    }

    return render(request, "landing.html", context)


class LoginView(auth_views.LoginView):
    """
    Thin wrapper around Django's built-in LoginView.

    Django's LoginView already handles CSRF, password hashing/checking via
    the auth backend, and honours `is_active` (inactive users are rejected
    automatically by AuthenticationForm). We only customise the template
    and widget styling.
    """

    template_name = "accounts/login.html"
    authentication_form = StyledAuthenticationForm
    redirect_authenticated_user = True


class LogoutView(auth_views.LogoutView):
    """Thin wrapper so logout is available via a named URL and POST-only by default."""

    next_page = "login"


@login_required
def post_login_redirect(request):
    """
    Landing page shown right after login.

    Admins are sent straight to their dedicated dashboard route so that
    the "Dashboard" nav link always resolves consistently for both roles.
    Employees see a role-labelled placeholder here ("Employee Dashboard").
    No statistics/content yet - that's a later phase.
    """
    if request.user.is_admin_role:
        return redirect("admin_dashboard")

    my_tasks = Task.objects.filter(assigned_to=request.user)
    context = {
        "user": request.user,
        "total_tasks": my_tasks.count(),
        "todo_tasks": my_tasks.filter(status=Task.Status.TODO).count(),
        "in_progress_tasks": my_tasks.filter(status=Task.Status.IN_PROGRESS).count(),
        "completed_tasks": my_tasks.filter(status=Task.Status.COMPLETED).count(),
    }
    return render(request, "accounts/home.html", context)


@admin_required
def admin_dashboard(request):
    total_users = User.objects.count()

    total_employees = User.objects.filter(
        role=User.Role.EMPLOYEE
    ).count()

    active_users = User.objects.filter(
        is_active=True
    ).count()

    total_tasks = Task.objects.count()

    context = {
        "user": request.user,
        "total_users": total_users,
        "total_employees": total_employees,
        "active_users": active_users,
        "total_tasks": total_tasks,
    }

    return render(
        request,
        "accounts/admin_dashboard.html",
        context,
    )

@login_required
def profile(request):
    """
    Lets the currently logged-in user view and edit their own profile.

    Security note: this view only ever reads/writes `request.user` - the
    user object Django's session middleware attached based on the
    authenticated session. There is no user id taken from the URL or from
    POST data, so there is no way to point this view at a different
    account; a user can never view or modify anyone else's information
    through this endpoint, regardless of what a manually crafted request
    contains.

    `ProfileForm` only exposes first_name/last_name/email as fields, so
    even if a request includes extra POST keys like `role` or `is_active`
    (e.g. from a hand-crafted request bypassing the UI), Django's
    ModelForm simply ignores unknown/non-form fields - those attributes
    are never read from `request.POST` and can't be changed this way.
    """
    if request.method == "POST":
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated.")
            return redirect("profile")
    else:
        form = ProfileForm(instance=request.user)

    return render(request, "accounts/profile.html", {"form": form})


class PasswordChangeView(auth_views.PasswordChangeView):
    """
    Thin wrapper around Django's built-in PasswordChangeView.

    Django handles: requiring the correct current password, validating
    the new password against AUTH_PASSWORD_VALIDATORS, hashing it with
    the configured hasher (never custom/home-grown hashing), and
    invalidating other sessions for the account via
    `update_session_auth_hash`. We only customise the template and add a
    success message, then send the user back to their profile page.
    """

    template_name = "accounts/password_change.html"
    form_class = StyledPasswordChangeForm
    success_url = reverse_lazy("profile")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Your password has been changed successfully.")
        return response

@login_required
@admin_required
def create_employee(request):
    if request.method == "POST":
        form = AdminCreateEmployeeForm(request.POST)

        if form.is_valid():
            user = form.save()

            temporary_password = user._temporary_password

            email_sent = send_via_brevo(
                subject="KS Management System - Your Employee Account",
                message=(
                    f"Hello {user.username},\n\n"
                    f"Your Employee Task Management System account has been created.\n\n"
                    f"Username: {user.username}\n"
                    f"Temporary Password: {temporary_password}\n"
                    f"Role: {user.get_role_display()}\n\n"
                    f"Please log in and change your password after your first login.\n\n"
                    f"Login here:\n"
                    f"https://ks-management-portal.onrender.com/accounts/login/\n\n"
                    f"Regards,\n"
                    f"KSMS Admin"
                ),
                recipient_email=user.email,
            )

            if email_sent:
                messages.success(
                    request,
                    f"Employee '{user.username}' created successfully "
                    f"and credentials emailed."
                )
            else:
                messages.warning(
                    request,
                    f"Employee '{user.username}' created, but the welcome "
                    f"email could not be sent. Share the temporary password "
                    f"with them manually: {temporary_password}"
                )
            return redirect("admin_dashboard")
    else:
        form = AdminCreateEmployeeForm()

    return render(
        request,
        "accounts/create_employee.html",
        {"form": form},
    )
@login_required
@admin_required
def user_list(request):
    users = User.objects.all().order_by("username")

    return render(
        request,
        "accounts/user_list.html",
        {"users": users},
    )



@login_required
@admin_required
def user_edit(request, user_id):
    user = get_object_or_404(User, pk=user_id)

    if request.method == "POST":
        form = AdminUserEditForm(request.POST, instance=user)

        if form.is_valid():
            if (user == request.user and form.cleaned_data["role"] != User.Role.ADMIN ):
                messages.error( request, "You cannot change your own role." )
                return redirect("user_list")
            form.save()

            messages.success(
                request,f"User '{user.username}' updated successfully.")

            return redirect("user_list")
    else:
        form = AdminUserEditForm(instance=user)

    return render(
        request,
        "accounts/user_edit.html",
        {
            "form": form,
            "user_obj": user,
        },
    )


@login_required
@admin_required
def toggle_user_status(request, user_id):
    user = get_object_or_404(User, pk=user_id)

    # Prevent the admin from accidentally disabling their own account.
    if user == request.user:
        messages.error(request, "You cannot change your own account status.")
        return redirect("user_list")

    user.is_active = not user.is_active
    user.save(update_fields=["is_active"])

    status = "activated" if user.is_active else "deactivated"

    messages.success(
        request,
        f"User '{user.username}' {status} successfully.",
    )

    return redirect("user_list")
