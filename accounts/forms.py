from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django import forms
import secrets
import string

User = get_user_model()


class ProfileForm(forms.ModelForm):
    """
    Lets a user edit their own profile details.

    Username, role, and account permissions are intentionally excluded.
    The view binds this form to request.user.
    """

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "email",
            "phone",
            "department",
            "designation",
        ]
        widgets = {
            "first_name": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "last_name": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-control"}
            ),
            "phone": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "department": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "designation": forms.TextInput(
                attrs={"class": "form-control"}
            ),
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

def generate_temporary_password(length=12):
    characters = string.ascii_letters + string.digits + "!@#$%^&*"

    return "".join(
        secrets.choice(characters)
        for _ in range(length)
    )

class AdminCreateEmployeeForm(forms.ModelForm):

    role = forms.ChoiceField(
        choices=User.Role.choices,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    class Meta:
        model = User
        fields = [
            "email",
            "username",
            "role",
            "designation",
            "subteam",
        ]
        widgets = {
            "email": forms.EmailInput(
                attrs={"class": "form-control"}
            ),
            "username": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "role": forms.Select(
                attrs={"class": "form-control"}
            ),
            "designation": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "subteam": forms.TextInput(
                attrs={"class": "form-control"}
            ),
        }

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "An account with this email address already exists."
            )

        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        temporary_password = generate_temporary_password()
        user.set_password(temporary_password)

        if commit:
            user.save()

        user._temporary_password = temporary_password
        return user




class AdminUserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            "username",
            "role",
            "first_name",
            "last_name",
            "email",
            "designation",
            "subteam",
            "is_active",
        ]
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control"}),
            "role": forms.Select(attrs={"class": "form-control"}),
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "designation": forms.TextInput(attrs={"class": "form-control"}),
            "subteam": forms.TextInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(),
        }