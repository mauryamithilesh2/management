from django import forms
from django.contrib.auth import get_user_model

from .models import Task

User = get_user_model()


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


class EmployeeTaskForm(TaskFormBase):
    """
    Form used when an employee creates/edits their own task.

    Deliberately excludes `assigned_to`, `created_by`, and `status`:
    - `assigned_to`/`created_by` are set by the view from `request.user`,
      not chosen by the employee (this is the same pattern already used
      for the profile form - never trust an identity field from a
      request when the view already knows who the user is).
    - `status` progression (e.g. marking a task Completed/Blocked) is
      handled separately, not as a field an employee sets while
      creating/editing the task's basic details.
    """

    class Meta(TaskFormBase.Meta):
        fields = ["title", "description", "start_date", "deadline", "priority"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "start_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "deadline": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "priority": forms.Select(attrs={"class": "form-control"}),
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
