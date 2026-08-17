from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404,  redirect, render

from .forms import AdminTaskForm, EmployeeTaskForm
from .models import Task


@login_required
def create_task(request):
    """
    Lets a logged-in user create a Task.

    - Employees use `EmployeeTaskForm` (no assigned_to/created_by/status
      fields exposed on the form) and the task is always saved with
      created_by = assigned_to = request.user.
    - Admins use `AdminTaskForm` (adds assigned_to, scoped to active
      employee accounts, and status) and the task is saved with
      created_by = request.user; assigned_to comes from the validated
      form field, which Django's ModelChoiceField already restricts to
      that safe queryset.

    Security note: `created_by` (and, for employees, `assigned_to`) are
    never read from request.POST - neither form exposes them as fields,
    and they are set here directly from `request.user` after validation.
    A hand-crafted POST cannot claim a task was created by or assigned to
    a different account.
    """
    is_admin = request.user.is_admin_role
    form_class = AdminTaskForm if is_admin else EmployeeTaskForm

    if request.method == "POST":
        form = form_class(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.created_by = request.user
            if not is_admin:
                task.assigned_to = request.user
            task.save()
            messages.success(request, "Task created successfully.")
            return redirect("post_login_redirect")
    else:
        form = form_class()

    return render(
        request,
        "tasks/task_form.html",
        {"form": form, "is_admin": is_admin},
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
    """
    Display a single task.

    Admins can view any task.

    Employees can view only tasks assigned to themselves.
    The ownership restriction is enforced in the database queryset,
    not in the template or frontend.
    """
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

    return render(
        request,
        "tasks/task_detail.html",
        {"task": task},
    )


@login_required
def task_edit(request, task_id):
    """
    Edit an existing task.

    Employees can edit only their own assigned tasks and cannot
    change ownership, creator, or status.

    Admins can edit any task and can change its assignment/status.
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
        form_class = EmployeeTaskForm

    if request.method == "POST":
        form = form_class(request.POST, instance=task)

        if form.is_valid():
            task = form.save(commit=False)

            if request.user.is_admin_role:
                task.created_by = task.created_by
            else:
                task.created_by = task.created_by
                task.assigned_to = request.user

            task.save()

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


@login_required
def task_delete(request, task_id):
    if request.user.is_admin_role:
        task = get_object_or_404(Task, pk=task_id)
    else:
        task = get_object_or_404(
            Task,
            pk=task_id,
            assigned_to=request.user,
        )

    if request.method == "POST":
        task.delete()
        messages.success(request, "Task deleted successfully.")
        return redirect("task_list")

    return render(
        request,
        "tasks/task_confirm_delete.html",
        {"task": task},
    )
