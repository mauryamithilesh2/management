from django import forms
from django.contrib.auth import get_user_model
import bleach
from .models import Task, TaskUpdate, ScheduledTask

User = get_user_model()

ALLOWED_TAGS = ["p", "br", "strong", "b", "em", "i", "ul", "ol", "li", "h2", "h3"]

class AdminTaskCreateForm(forms.ModelForm):
    """
    Used only for creating a NEW task. Unlike AdminTaskForm (single
    assigned_to, used for editing an existing task), this lets an admin
    select multiple employees at once - the view creates one separate
    Task row per selected employee, so every other part of the app
    (permissions, notifications, performance logs) keeps working with
    the existing one-task-per-employee assumption.
    """

    assigned_to = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(role=User.Role.EMPLOYEE, is_active=True),
        widget=forms.CheckboxSelectMultiple,
        label="Assign to",
        help_text="Select one or more employees - a separate task is created for each.",
    )

    class Meta:
        model = Task
        fields = ["title", "description", "start_date", "deadline", "status", "priority"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "start_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "deadline": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "status": forms.Select(attrs={"class": "form-control"}),
            "priority": forms.Select(attrs={"class": "form-control"}),
        }

    def clean_description(self):
        raw = self.cleaned_data.get("description", "")
        return bleach.clean(raw, tags=ALLOWED_TAGS, strip=True)


class TaskFormBase(forms.ModelForm):
    """
    Shared validation for both task forms, so the two rules below aren't
    duplicated between `EmployeeTaskForm` and `AdminTaskForm`.
    """

    class Meta:
        model = Task
        fields = []  # overridden by subclasses

    def clean_title(self):
        title = self.cleaned_data.get("title", "").strip()
        if not title:
            raise forms.ValidationError("Title cannot be empty.")
        return title

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        deadline = cleaned_data.get("deadline")

        if start_date and deadline and deadline < start_date:
            raise forms.ValidationError("Deadline cannot be before the start date.")

        return cleaned_data


class EmployeeTaskStatusForm(TaskFormBase):
    """
    Form used when an employee updates a task assigned to them.

    Only `status` is editable - title, description, dates, priority, and
    assignment are all set by the admin who created the task. An employee
    can move a task through its lifecycle (e.g. To Do -> In Progress ->
    Completed) but cannot change what the task is or who it's for.
    """

    class Meta(TaskFormBase.Meta):
        fields = ["status"]
        widgets = {
            "status": forms.Select(attrs={"class": "form-control"}),
        }


class TaskUpdateForm(forms.ModelForm):
    """
    Form an employee uses to log a performance entry against a task
    assigned to them - date + which half of the day + an optional note.

    `task` and `employee` are deliberately excluded: the view sets both
    from `request.user` and the task already loaded from the URL, never
    from submitted form data - same pattern as ProfileForm/EmployeeTaskStatusForm.
    """

    class Meta:
        model = TaskUpdate
        fields = ["date", "half", "note"]
        widgets = {
            "date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "half": forms.Select(attrs={"class": "form-control"}),
            "note": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }

class AdminTaskForm(TaskFormBase):
    """
    Form used when an admin creates/edits a task, including assignment.

    `assigned_to` is a `ModelChoiceField` scoped to active employee
    accounts. Because it's a `ModelChoiceField` backed by this queryset,
    Django validates the submitted value against it automatically - a
    tampered/arbitrary user id that isn't in the queryset (inactive user,
    admin account, or a non-existent id) is rejected as an invalid choice
    before the form is considered valid. There is no way to bypass this
    via a hand-crafted POST value.
    """

    assigned_to = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True, role=User.Role.EMPLOYEE),
        widget=forms.Select(attrs={"class": "form-control"}),
        help_text="Only active employee accounts can be assigned tasks.",
    )

    class Meta(TaskFormBase.Meta):
        fields = [
            "title",
            "description",
            "assigned_to",
            "start_date",
            "deadline",
            "status",
            "priority",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "start_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "deadline": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "status": forms.Select(attrs={"class": "form-control"}),
            "priority": forms.Select(attrs={"class": "form-control"}),
        }

    def clean_description(self):
        raw = self.cleaned_data.get("description", "")
        return bleach.clean(raw, tags=ALLOWED_TAGS, strip=True)

from django.utils import timezone
class ScheduledTaskRowForm(forms.Form):
    """
    One row on the Schedule Task page: which employee, and exactly which
    date and time they should receive it. Required - this page is only
    for scheduling future sends; use the plain Assign Task page for
    immediate assignment.
    """

    employee = forms.ModelChoiceField(
        queryset=User.objects.filter(role=User.Role.EMPLOYEE, is_active=True),
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    release_at = forms.DateTimeField(
        required=True,
        widget=forms.DateTimeInput(
            attrs={"class": "form-control", "type": "datetime-local"}
        ),
        help_text="Exact date and time this task should be sent (e.g. tomorrow 9:00 AM).",
    )

    def clean_release_at(self):
        release_at = self.cleaned_data.get("release_at")
        if release_at and release_at < timezone.now():
            raise forms.ValidationError("Release time must be in the future.")
        return release_at


from django.forms import formset_factory

ScheduledTaskFormSet = formset_factory(
    ScheduledTaskRowForm, extra=1, min_num=1, validate_min=True
)

class ScheduledTaskDetailsForm(forms.Form):
    """
    The shared task details for a create-task batch - title, description,
    dates, priority. Paired with ScheduledTaskFormSet (one row per
    employee + their individual send time) on the same page.
    """

    title = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 4}),
    )
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )
    deadline = forms.DateField(
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )
    priority = forms.ChoiceField(
        choices=Task.Priority.choices,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    def clean_description(self):
        raw = self.cleaned_data.get("description", "")
        return bleach.clean(raw, tags=ALLOWED_TAGS, strip=True)

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        deadline = cleaned_data.get("deadline")

        if start_date and deadline and deadline < start_date:
            raise forms.ValidationError("Deadline cannot be before the start date.")

        return cleaned_data

class ScheduledTaskEditForm(forms.ModelForm):
    """
    Edit a single pending ScheduledTask row - not the whole batch, just
    this one employee's entry (title/description/dates/priority and
    when it releases).
    """

    class Meta:
        model = ScheduledTask
        fields = ["title", "description", "start_date", "deadline", "priority", "release_at"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "start_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "deadline": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "priority": forms.Select(attrs={"class": "form-control"}),
            "release_at": forms.DateTimeInput(attrs={"class": "form-control", "type": "datetime-local"}),
        }

    def clean_description(self):
        raw = self.cleaned_data.get("description", "")
        return bleach.clean(raw, tags=ALLOWED_TAGS, strip=True)

    def clean_release_at(self):
        release_at = self.cleaned_data.get("release_at")
        if release_at and release_at < timezone.now():
            raise forms.ValidationError("Release time must be in the future.")
        return release_at

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        deadline = cleaned_data.get("deadline")
        if start_date and deadline and deadline < start_date:
            raise forms.ValidationError("Deadline cannot be before the start date.")
        return cleaned_data