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
        BLOCKED = "BLOCKED", "Blocked"

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
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.recipient} - {self.message}"

