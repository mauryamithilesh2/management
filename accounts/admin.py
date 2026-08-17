from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    """
    Registers the custom User model with Django's built-in admin site,
    reusing Django's proven UserAdmin (correct password widgets, hashing,
    permissions UI, etc.) and simply adding the `role` field.
    """

    fieldsets = DjangoUserAdmin.fieldsets + (
        ("Role", {"fields": ("role",)}),
    )
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        ("Role", {"fields": ("role",)}),
    )
    list_display = ("username", "email", "first_name", "last_name", "role", "is_active", "date_joined")
    list_filter = DjangoUserAdmin.list_filter + ("role",)
