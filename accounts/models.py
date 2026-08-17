from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models


class ETMSUserManager(UserManager):
    """
    Same behaviour as Django's default UserManager, except that
    `create_superuser` (used by the `createsuperuser` management command)
    also sets role=ADMIN. Without this override, a superuser would have
    Django's `is_superuser`/`is_staff` flags set correctly but our own
    `role` field would still default to EMPLOYEE, since `role` is a custom
    field Django's built-in command doesn't know about.
    """

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("role", User.Role.ADMIN)
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    """
    Custom user model for the Employee Task Management System.

    Extends Django's AbstractUser (keeping username, email, first_name,
    last_name, is_active, date_joined, and built-in password hashing) and
    adds the role field that drives all authorization decisions in the app.

    There is intentionally only one User model / one auth system for both
    roles - "admin" is not a separate account type, it is a permission
    level on the same account.
    """

    class Role(models.TextChoices):
        EMPLOYEE = "EMPLOYEE", "Employee"
        ADMIN = "ADMIN", "Admin"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.EMPLOYEE,
        help_text="Determines what the user is permitted to do in the system.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    objects = ETMSUserManager()

    class Meta:
        ordering = ["username"]

    def __str__(self):
        full_name = self.get_full_name()
        return f"{full_name} ({self.username})" if full_name else self.username

    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMIN

    @property
    def is_employee_role(self):
        return self.role == self.Role.EMPLOYEE
