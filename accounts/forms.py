from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django import forms

User = get_user_model()


class ProfileForm(forms.ModelForm):
    """
    Lets a user edit their own basic profile details.

    Intentionally excludes `username` and `role`: role changes are an
    administrative action reserved for later phases, and this form is
    always bound to `request.user` by the view (never to a user looked up
    from a URL/POST parameter), so there is no field here - and no way via
    this form - for one account to edit another account's data.
    """

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
        }


class StyledAuthenticationForm(AuthenticationForm):
    """
    Django's AuthenticationForm with CSS classes added to widgets and
    autofocus on the username field. No authentication logic is changed -
    Django's ModelBackend + password hashing + is_active checks still apply
    exactly as they do by default.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update(
            {"class": "form-control", "autofocus": True, "placeholder": "Username"}
        )
        self.fields["password"].widget.attrs.update(
            {"class": "form-control", "placeholder": "Password"}
        )


class StyledPasswordChangeForm(PasswordChangeForm):
    """
    Django's built-in PasswordChangeForm with CSS classes added to
    widgets. All validation (correct current password, new-password
    confirmation match, AUTH_PASSWORD_VALIDATORS) and hashing stay exactly
    as Django implements them - only the widget styling is customised.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ("old_password", "new_password1", "new_password2"):
            self.fields[field_name].widget.attrs.update({"class": "form-control"})

class AdminCreateEmployeeForm(forms.ModelForm):
    password = forms.CharField(
        label="Temporary Password",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )
    password_confirm = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )

    class Meta:
        model = User
        fields = ["username", "password", "password_confirm"]

    def clean(self):
        cleaned_data = super().clean()

        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError("Passwords do not match.")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)

        user.role = User.Role.EMPLOYEE
        user.set_password(self.cleaned_data["password"])

        if commit:
            user.save()

        return user