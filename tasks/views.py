from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404,  redirect, render

from .forms import AdminTaskForm, EmployeeTaskStatusForm, TaskUpdateForm
from .models import Task, Notification, TaskUpdate
from accounts.permissions import admin_required


@admin_required
def create_task(request):
    if request.method == "POST":
        form = AdminTaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.created_by = request.user
            task.save()

            Notification.objects.create(
                recipient=task.assigned_to,
                task=task,
                message=f"You have been assigned a new task: \"{task.title}\".",
            )

            messages.success(request, "Task created successfully.")
            return redirect("post_login_redirect")
    else:
        form = AdminTaskForm()

    return render(
        request,
        "tasks/task_form.html",
        {"form": form, "is_admin": True},
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

    updates = task.updates.select_related("employee")
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
            update = form.save(commit=False)
            update.task = task
            update.employee = request.user
            update.save()
            messages.success(request, "Update logged.")

    return redirect("task_detail", task_id=task.pk)

@login_required
def task_edit(request, task_id):
    """
    Edit an existing task.

    Admins can edit any task's full details (including reassignment).
    Employees can only update the status of a task assigned to them -
    they cannot touch title, description, dates, priority, or assignment.
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
        previous_assignee_id = task.assigned_to_id if request.user.is_admin_role else None
        form = form_class(request.POST, instance=task)

        if form.is_valid():
            task = form.save()

            if (
                request.user.is_admin_role
                and task.assigned_to_id != previous_assignee_id
            ):
                Notification.objects.create(
                    recipient=task.assigned_to,
                    task=task,
                    message=f"You have been assigned a task: \"{task.title}\".",
                )

            messages.success(request, "Task updated successfully.")
            return redirect("task_detail", task_id=task.pk)
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