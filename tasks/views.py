from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import AdminTaskForm, EmployeeTaskStatusForm, TaskUpdateForm
from .models import Task, Notification, TaskUpdate
from accounts.permissions import admin_required
import logging
User = get_user_model()
logger = logging.getLogger(__name__)


def notify_employee(task, subject=None, message=None):
    """
    Send both in-app notification and email to the task's assigned employee.
    """

    employee = task.assigned_to

    if not subject:
        subject = f"Task Notification: {task.title}"

    if not message:
        message = (
            f'You have a task notification for "{task.title}".\n\n'
            f"Description: {task.description}\n"
            f"Start Date: {task.start_date}\n"
            f"Deadline: {task.deadline}\n"
            f"Priority: {task.get_priority_display()}\n"
            f"Status: {task.get_status_display()}\n\n"
            f"Please log in to ETMS to view the task details."
        )

    # In-app notification
    Notification.objects.create(
        recipient=employee,
        task=task,
        message=message,
    )

    # Email notification - best-effort. A mail-server hiccup should never
    # block task creation/assignment, which already succeeded in the DB
    # by the time this runs.
    if employee.email:
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[employee.email],
                fail_silently=False,
            )
        except Exception:
            logger.exception(
                "Failed to send task notification email to %s", employee.email
            )
@login_required
@admin_required
def create_task(request):
    if request.method == "POST":
        form = AdminTaskForm(request.POST)

        if form.is_valid():
            task = form.save(commit=False)
            task.created_by = request.user
            task.save()

            notify_employee(
                task,
                subject=f"New Task Assigned: {task.title}",
                message=(
                    f'Hello {task.assigned_to.get_full_name() or task.assigned_to.username},\n\n'
                    f'You have been assigned a new task.\n\n'
                    f"Task: {task.title}\n"
                    f"Description: {task.description}\n"
                    f"Start Date: {task.start_date}\n"
                    f"Deadline: {task.deadline}\n"
                    f"Priority: {task.get_priority_display()}\n"
                    f"Status: {task.get_status_display()}\n\n"
                    f"Please log in to ETMS to view the task details.\n\n"
                    f"Regards,\n"
                    f"ETMS Admin"
                ),
            )

            messages.success(
                request,
                f'Task "{task.title}" created and assigned successfully.'
            )

            return redirect("post_login_redirect")

    else:
        form = AdminTaskForm()

    return render(
        request,
        "tasks/task_form.html",
        {
            "form": form,
            "is_admin": True,
        },
    )

@login_required
def task_list(request):
    """
    Lists tasks, scoped by role.

    Security note: the queryset is filtered server-side from
    `request.user`, never from anything in the URL or query string -
    there is no task-owner parameter accepted from the request at all.
    An employee cannot see another employee's tasks by manipulating the
    URL/query parameters, because nothing about which tasks are returned
    is ever read from the request other than the authenticated user.

    - Admins (role=ADMIN) see every task.
    - Everyone else sees only tasks assigned to themselves
      (`assigned_to=request.user`).
    """
    if request.user.is_admin_role:
        tasks = Task.objects.select_related("assigned_to", "created_by").all()
    else:
        tasks = Task.objects.select_related("assigned_to", "created_by").filter(
            assigned_to=request.user
        )

    return render(
        request,
        "tasks/task_list.html",
        {"tasks": tasks, "is_admin": request.user.is_admin_role},
    )

@login_required
def task_detail(request, task_id):
    if request.user.is_admin_role:
        task = get_object_or_404(
            Task.objects.select_related("assigned_to", "created_by"),
            pk=task_id,
        )
    else:
        task = get_object_or_404(
            Task.objects.select_related("assigned_to", "created_by"),
            pk=task_id,
            assigned_to=request.user,
        )

    updates = task.updates.select_related("employee").order_by("-date", "-created_at")
    update_form = TaskUpdateForm() if not request.user.is_admin_role else None

    return render(
        request,
        "tasks/task_detail.html",
        {
            "task": task,
            "updates": updates,
            "update_form": update_form,
        },
    )

@login_required
def add_task_update(request, task_id):
    """
    Lets an employee log a performance entry (date + half + note) against
    a task assigned to them. Admins cannot log entries here - only the
    assigned employee can, since this is a self-reported performance log.
    """
    task = get_object_or_404(
        Task,
        pk=task_id,
        assigned_to=request.user,
    )

    if request.method == "POST":
        form = TaskUpdateForm(request.POST)

        if form.is_valid():
            selected_date = form.cleaned_data["date"]
            selected_half = form.cleaned_data["half"]

            already_exists = TaskUpdate.objects.filter(
                task=task,
                employee=request.user,
                date=selected_date,
                half=selected_half,
            ).exists()

            if already_exists:
                messages.error(
                    request,
                    f"{form.cleaned_data['half']} has already been logged for this date."
                )
            else:
                update = form.save(commit=False)
                update.task = task
                update.employee = request.user
                update.save()

                messages.success(request, "Update logged.")

    return redirect("task_detail", task_id=task.pk)


@admin_required
def notify_task_employee(request, task_id):
    task = get_object_or_404(
        Task.objects.select_related("assigned_to"),
        pk=task_id,
    )

    if request.method != "POST":
        return redirect("task_detail", task_id=task.pk)

    if not task.assigned_to:
        messages.error(request, "This task has no assigned employee.")
        return redirect("task_detail", task_id=task.pk)

    notify_employee(
        task,
        subject=f"Task Reminder: {task.title}",
        message=(
            f'Hello {task.assigned_to.get_full_name() or task.assigned_to.username},\n\n'
            f'The administrator has sent you a notification regarding your task.\n\n'
            f"Task: {task.title}\n"
            f"Description: {task.description}\n"
            f"Start Date: {task.start_date}\n"
            f"Deadline: {task.deadline}\n"
            f"Priority: {task.get_priority_display()}\n"
            f"Status: {task.get_status_display()}\n\n"
            f"Please log in to ETMS for more details."
        ),
    )

    messages.success(
        request,
        f"Notification and email sent to "
        f"{task.assigned_to.get_full_name() or task.assigned_to.username}.",
    )

    return redirect("task_detail", task_id=task.pk)
@login_required
def task_edit(request, task_id):
    """
    Admins can edit the complete task.

    Employees can only update the status of tasks assigned to them.

    When an admin reassigns a task to a different employee:
    - The new employee gets an in-app notification.
    - The new employee gets an email notification.

    Editing a task without changing the employee does not
    automatically send another notification.
    """

    if request.user.is_admin_role:
        task = get_object_or_404(
            Task.objects.select_related("assigned_to", "created_by"),
            pk=task_id,
        )
        form_class = AdminTaskForm

    else:
        task = get_object_or_404(
            Task.objects.select_related("assigned_to", "created_by"),
            pk=task_id,
            assigned_to=request.user,
        )
        form_class = EmployeeTaskStatusForm

    if request.method == "POST":

        # Remember the employee before saving.
        previous_assignee_id = (
            task.assigned_to_id
            if request.user.is_admin_role
            else None
        )

        form = form_class(
            request.POST,
            instance=task,
        )

        if form.is_valid():

            task = form.save()

            # -------------------------------------------------
            # ADMIN REASSIGNED TASK TO A DIFFERENT EMPLOYEE
            # -------------------------------------------------
            if (
                request.user.is_admin_role
                and task.assigned_to_id != previous_assignee_id
            ):
                notify_employee(
                    task,
                    subject=f"Task Assigned: {task.title}",
                    message=(
                        f'Hello {task.assigned_to.get_full_name() or task.assigned_to.username},\n\n'
                        f'You have been assigned a task.\n\n'
                        f"Task: {task.title}\n"
                        f"Description: {task.description}\n"
                        f"Start Date: {task.start_date}\n"
                        f"Deadline: {task.deadline}\n"
                        f"Priority: {task.get_priority_display()}\n"
                        f"Status: {task.get_status_display()}\n\n"
                        f"Please log in to ETMS to view the task details.\n\n"
                        f"Regards,\n"
                        f"ETMS Admin"
                    ),
                )

            messages.success(
                request,
                "Task updated successfully."
            )

            return redirect(
                "task_detail",
                task_id=task.pk,
            )

    else:
        form = form_class(instance=task)

    return render(
        request,
        "tasks/task_form.html",
        {
            "form": form,
            "is_admin": request.user.is_admin_role,
            "is_edit": True,
            "task": task,
        },
    )

@admin_required
def task_delete(request, task_id):
    task = get_object_or_404(Task, pk=task_id)

    if request.method == "POST":
        task.delete()
        messages.success(request, "Task deleted successfully.")
        return redirect("task_list")

    return render(
        request,
        "tasks/task_confirm_delete.html",
        {"task": task},
    )


@login_required
def notification_list(request):
    notifications = Notification.objects.filter(
        recipient=request.user
    ).select_related("task")

    unread_ids = list(
        notifications.filter(is_read=False).values_list("id", flat=True)
    )
    if unread_ids:
        Notification.objects.filter(id__in=unread_ids).update(is_read=True)

    return render(
        request,
        "tasks/notification_list.html",
        {"notifications": notifications},
    )


@admin_required
def employee_overview(request):
    """
    Admin-facing directory of employees, with designation and subteam,
    so an admin can drill into any employee's task breakdown.
    """
    employees = User.objects.filter(role=User.Role.EMPLOYEE).order_by("username")

    return render(
        request,
        "tasks/employee_overview.html",
        {"employees": employees},
    )

@admin_required
def employee_task_detail(request, employee_id):
    employee = get_object_or_404(User, pk=employee_id, role=User.Role.EMPLOYEE)

    tasks = Task.objects.filter(assigned_to=employee).select_related("created_by")

    latest_task = tasks.order_by("-created_at").first()

    updates = TaskUpdate.objects.filter(employee=employee).select_related("task").order_by("-date", "-created_at")
    context = {
        "employee": employee,
        "latest_task": latest_task,
        "tasks": tasks,
        "updates": updates,
        "todo_count": tasks.filter(status=Task.Status.TODO).count(),
        "in_progress_count": tasks.filter(status=Task.Status.IN_PROGRESS).count(),
        "completed_count": tasks.filter(status=Task.Status.COMPLETED).count(),
    }

    return render(
        request,
        "tasks/employee_task_detail.html",
        context,
    )

