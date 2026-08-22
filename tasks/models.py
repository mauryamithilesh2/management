from django.conf import settings
from django.db import models


class Task(models.Model):
    """
    A unit of work assigned to an employee.

    This is the data model only - task views, forms, templates, URLs,
    dashboards, and assignment UI are implemented in a later phase.

    Both user relationships point at the project's existing custom User
    model (settings.AUTH_USER_MODEL) rather than storing names as text,
    so a task always references a real account and stays consistent with
    that account's role/permissions.
    """

    class Status(models.TextChoices):
        TODO = "TODO", "To Do"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        COMPLETED = "COMPLETED", "Completed"
       

    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"
        URGENT = "URGENT", "Urgent"

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assigned_tasks",
        help_text="The employee this task is assigned to.",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_tasks",
        help_text="The user (typically an admin) who created this task.",
    )

    start_date = models.DateField()
    deadline = models.DateField()

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.TODO,
    )
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

class TaskUpdate(models.Model):
    """
    A performance log entry an employee adds against a task assigned to
    them - date + which half of the day the work covers, plus a note.

    This is separate from `Task.status`: status is the current state of
    the task (To Do / In Progress / Completed / Blocked), while
    TaskUpdate is a running, timestamped log of work done over time -
    an employee can add many entries against the same task.
    """

    class Half(models.TextChoices):
        FIRST_HALF = "FIRST_HALF", "1st Half"
        SECOND_HALF = "SECOND_HALF", "2nd Half"

    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="updates",
    )
    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="task_updates",
        help_text="The employee who logged this entry.",
    )
    date = models.DateField()
    half = models.CharField(
        max_length=20,
        choices=Half.choices,
    )
    note = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["task", "employee", "date", "half"],
                name="unique_task_employee_date_half",
            )
        ]

    def __str__(self):
        return f"{self.task.title} - {self.date} ({self.get_half_display()})"


class Notification(models.Model):
    """
    A simple in-app notification for an employee, created automatically
    when an admin assigns (or reassigns) a task to them.

    Deliberately minimal: no notification "types" system, no generic
    foreign key. If more notification triggers are added later, this can
    be extended - for now it only needs to cover task assignment.
    """

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        help_text="The employee this notification is for.",
    )
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.recipient} - {self.message}"

class ScheduledTask(models.Model):
    """
    A task queued to be released to its assigned employee at a future
    time - part of a batch where each employee gets their task 24h after
    the previous one, instead of everyone getting it at once.

    Only admins see these before release. Once released, a real Task row
    is created (via the normal Task model) and the employee sees it
    exactly like any other assigned task - ScheduledTask itself is just
    the "waiting room."
    """

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="scheduled_tasks",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_scheduled_tasks",
    )

    start_date = models.DateField()
    deadline = models.DateField()
    priority = models.CharField(max_length=20, choices=Task.Priority.choices, default=Task.Priority.MEDIUM)

    release_at = models.DateTimeField(
        help_text="When this task becomes a real, visible task for the employee.",
    )
    released = models.BooleanField(default=False)
    on_hold = models.BooleanField(
    default=False,
    help_text="If true, this task will NOT auto-release even if its time has passed, until an admin resumes it.",
    )
    released_task = models.OneToOneField(
        Task,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scheduled_source",
        help_text="The real Task created once this was released.",
    )

    batch_id = models.CharField(
        max_length=36,
        help_text="Groups tasks created together in one batch (same title, staggered release).",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["release_at"]

    def __str__(self):
        return f"{self.title} -> {self.assigned_to} (releases {self.release_at})"
