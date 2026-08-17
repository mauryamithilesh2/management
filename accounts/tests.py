from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class UserModelTests(TestCase):
    def test_default_role_is_employee(self):
        user = User.objects.create_user(username="alice", password="strong-pass-123")
        self.assertEqual(user.role, User.Role.EMPLOYEE)
        self.assertTrue(user.is_employee_role)
        self.assertFalse(user.is_admin_role)

    def test_admin_role_flags(self):
        admin = User.objects.create_user(
            username="boss", password="strong-pass-123", role=User.Role.ADMIN
        )
        self.assertTrue(admin.is_admin_role)
        self.assertFalse(admin.is_employee_role)

    def test_password_is_hashed(self):
        user = User.objects.create_user(username="bob", password="strong-pass-123")
        self.assertNotEqual(user.password, "strong-pass-123")
        self.assertTrue(user.check_password("strong-pass-123"))

    def test_createsuperuser_defaults_to_admin_role(self):
        # `createsuperuser` sets is_superuser/is_staff via Django's base
        # manager, but role is our own field - this confirms our manager
        # override wires it up so the first bootstrap account is an Admin.
        superuser = User.objects.create_superuser(
            username="root", email="root@example.com", password="strong-pass-123"
        )
        self.assertEqual(superuser.role, User.Role.ADMIN)
        self.assertTrue(superuser.is_admin_role)

    def test_createsuperuser_role_can_still_be_overridden(self):
        superuser = User.objects.create_superuser(
            username="root2",
            email="root2@example.com",
            password="strong-pass-123",
            role=User.Role.EMPLOYEE,
        )
        self.assertEqual(superuser.role, User.Role.EMPLOYEE)


class LoginLogoutTests(TestCase):
    def setUp(self):
        self.password = "strong-pass-123"
        self.user = User.objects.create_user(
            username="employee1",
            password=self.password,
            role=User.Role.EMPLOYEE,
        )

    def test_login_page_loads(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sign in")

    def test_successful_login_redirects_to_home(self):
        response = self.client.post(
            reverse("login"),
            {"username": "employee1", "password": self.password},
        )
        self.assertRedirects(response, reverse("post_login_redirect"))

    def test_successful_login_creates_authenticated_session(self):
        self.client.post(
            reverse("login"),
            {"username": "employee1", "password": self.password},
        )
        response = self.client.get(reverse("post_login_redirect"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "employee1")

    def test_invalid_password_does_not_log_in(self):
        response = self.client.post(
            reverse("login"),
            {"username": "employee1", "password": "wrong-password"},
        )
        self.assertEqual(response.status_code, 200)  # re-renders form, no redirect
        self.assertContains(response, "Please enter a correct username and password")

    def test_unknown_username_does_not_log_in(self):
        response = self.client.post(
            reverse("login"),
            {"username": "does-not-exist", "password": "whatever-123"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please enter a correct username and password")

    def test_inactive_user_cannot_log_in(self):
        self.user.is_active = False
        self.user.save()
        response = self.client.post(
            reverse("login"),
            {"username": "employee1", "password": self.password},
        )
        self.assertEqual(response.status_code, 200)
        # Not authenticated: home page redirects to login instead.
        home_response = self.client.get(reverse("post_login_redirect"))
        self.assertNotEqual(home_response.status_code, 200)

    def test_logout_ends_session(self):
        self.client.login(username="employee1", password=self.password)
        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, reverse("login"))

        # After logout, the protected home page should redirect to login.
        home_response = self.client.get(reverse("post_login_redirect"))
        self.assertNotEqual(home_response.status_code, 200)

    def test_home_requires_login(self):
        response = self.client.get(reverse("post_login_redirect"))
        self.assertNotEqual(response.status_code, 200)
        self.assertIn(reverse("login"), response.url)


class RoleBasedAuthorizationTests(TestCase):
    """
    Phase 3: role-based authorization.

    Covers the minimum set of scenarios called out in the Phase 3 spec:
    employee/admin login, admin-only view protection, unauthenticated
    access, and protection against one user modifying another user's
    data through the profile view.
    """

    def setUp(self):
        self.password = "strong-pass-123"
        self.employee = User.objects.create_user(
            username="employee1", password=self.password, role=User.Role.EMPLOYEE,
            email="employee1@example.com",
        )
        self.other_employee = User.objects.create_user(
            username="employee2", password=self.password, role=User.Role.EMPLOYEE,
            email="employee2@example.com",
        )
        self.admin = User.objects.create_user(
            username="admin1", password=self.password, role=User.Role.ADMIN,
        )

    # 1 & 2: employee and admin can both log in.
    def test_employee_can_log_in(self):
        logged_in = self.client.login(username="employee1", password=self.password)
        self.assertTrue(logged_in)

    def test_admin_can_log_in(self):
        logged_in = self.client.login(username="admin1", password=self.password)
        self.assertTrue(logged_in)

    # 3: employee cannot access admin-only view.
    def test_employee_cannot_access_admin_dashboard(self):
        self.client.login(username="employee1", password=self.password)
        response = self.client.get(reverse("admin_dashboard"))
        self.assertEqual(response.status_code, 403)

    # 4: admin can access admin-only view.
    def test_admin_can_access_admin_dashboard(self):
        self.client.login(username="admin1", password=self.password)
        response = self.client.get(reverse("admin_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Admin Dashboard")

    # 5: unauthenticated user cannot access protected pages.
    def test_anonymous_cannot_access_admin_dashboard(self):
        response = self.client.get(reverse("admin_dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_anonymous_cannot_access_profile(self):
        response = self.client.get(reverse("profile"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_anonymous_post_to_admin_dashboard_is_also_rejected(self):
        # Admin-only protection must reject POST, not just GET.
        response = self.client.post(reverse("admin_dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_logged_in_employee_post_to_admin_dashboard_is_forbidden(self):
        self.client.login(username="employee1", password=self.password)
        response = self.client.post(reverse("admin_dashboard"))
        self.assertEqual(response.status_code, 403)

    # 6: employee cannot modify another user's protected information.
    def test_employee_can_view_own_profile(self):
        self.client.login(username="employee1", password=self.password)
        response = self.client.get(reverse("profile"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "employee1")

    def test_profile_post_only_ever_updates_request_user(self):
        self.client.login(username="employee1", password=self.password)
        # Even if the POST body tries to smuggle in a reference to a
        # different account, the view has no field/mechanism that reads a
        # target user from the request - it always saves to request.user.
        response = self.client.post(
            reverse("profile"),
            {
                "first_name": "Alice",
                "last_name": "Employee",
                "email": "alice-updated@example.com",
                # Not a real field on the form; simulates a tampering
                # attempt. Django simply ignores unknown fields.
                "user_id": self.other_employee.pk,
                "username": "employee2",
            },
        )
        self.assertEqual(response.status_code, 302)

        self.employee.refresh_from_db()
        self.other_employee.refresh_from_db()

        self.assertEqual(self.employee.email, "alice-updated@example.com")
        self.assertEqual(self.employee.username, "employee1")  # unchanged, not editable

        # The other employee's record must be completely untouched.
        self.assertEqual(self.other_employee.email, "employee2@example.com")
        self.assertEqual(self.other_employee.username, "employee2")

    # 7: role checking works correctly (decorator-level, beyond the
    # model-property tests in UserModelTests above).
    def test_admin_required_allows_admin_and_blocks_employee(self):
        self.client.login(username="admin1", password=self.password)
        self.assertEqual(self.client.get(reverse("admin_dashboard")).status_code, 200)

        self.client.logout()
        self.client.login(username="employee1", password=self.password)
        self.assertEqual(self.client.get(reverse("admin_dashboard")).status_code, 403)

    # 8: inactive users cannot authenticate (admin included, in addition
    # to the employee case already covered in LoginLogoutTests).
    def test_inactive_admin_cannot_log_in(self):
        self.admin.is_active = False
        self.admin.save()
        logged_in = self.client.login(username="admin1", password=self.password)
        self.assertFalse(logged_in)


class NavigationProfilePasswordTests(TestCase):
    """
    Small-enhancements pass on top of Phase 3:
    role-aware navigation, expanded profile page, change-password page,
    the custom 403 "Access Denied" page, and the role-aware dashboard
    placeholder.
    """

    def setUp(self):
        self.password = "strong-pass-123"
        self.employee = User.objects.create_user(
            username="employee1",
            password=self.password,
            role=User.Role.EMPLOYEE,
            email="employee1@example.com",
            first_name="Employee",
            last_name="One",
        )
        self.admin = User.objects.create_user(
            username="admin1",
            password=self.password,
            role=User.Role.ADMIN,
        )

    # --- Role-aware navigation -------------------------------------------------

    def test_employee_sees_employee_navigation(self):
        self.client.login(username="employee1", password=self.password)
        response = self.client.get(reverse("post_login_redirect"))
        self.assertContains(response, "My Profile")
        self.assertContains(response, "Admin Request")
        # Admin-only nav items must not be rendered for an employee.
        self.assertNotContains(response, "Admin Requests")
        self.assertNotContains(response, ">Users<")
        self.assertNotContains(response, ">Tasks<")

    def test_admin_sees_admin_navigation(self):
        self.client.login(username="admin1", password=self.password)
        response = self.client.get(reverse("admin_dashboard"))
        self.assertContains(response, ">Users<")
        self.assertContains(response, ">Tasks<")
        self.assertContains(response, "Admin Requests")
        self.assertContains(response, "My Profile")

    # --- Role-aware dashboard placeholder --------------------------------------

    def test_employee_dashboard_heading(self):
        self.client.login(username="employee1", password=self.password)
        response = self.client.get(reverse("post_login_redirect"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Employee Dashboard")

    def test_admin_dashboard_heading_and_auto_redirect(self):
        self.client.login(username="admin1", password=self.password)
        # Admins hitting the generic post-login URL are sent to their
        # dedicated dashboard, which shows the admin heading.
        response = self.client.get(reverse("post_login_redirect"))
        self.assertRedirects(response, reverse("admin_dashboard"))
        dashboard_response = self.client.get(reverse("admin_dashboard"))
        self.assertContains(dashboard_response, "Admin Dashboard")

    # --- Admin-only URL protection (still enforced server-side) ---------------

    def test_employee_cannot_access_admin_url(self):
        self.client.login(username="employee1", password=self.password)
        response = self.client.get(reverse("admin_dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_admin_can_access_admin_url(self):
        self.client.login(username="admin1", password=self.password)
        response = self.client.get(reverse("admin_dashboard"))
        self.assertEqual(response.status_code, 200)

    # --- Profile page -----------------------------------------------------------

    def test_employee_can_access_profile(self):
        self.client.login(username="employee1", password=self.password)
        response = self.client.get(reverse("profile"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "employee1")
        self.assertContains(response, "Employee")  # role display
        self.assertContains(response, "Active")

    def test_admin_can_access_profile(self):
        self.client.login(username="admin1", password=self.password)
        response = self.client.get(reverse("profile"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "admin1")

    def test_profile_shows_readonly_role_status_and_date_joined(self):
        self.client.login(username="employee1", password=self.password)
        response = self.client.get(reverse("profile"))
        self.assertContains(response, "Role")
        self.assertContains(response, "Account Status")
        self.assertContains(response, "Active")

    def test_user_cannot_modify_own_role_through_profile_form(self):
        self.client.login(username="employee1", password=self.password)
        self.client.post(
            reverse("profile"),
            {
                "first_name": "Employee",
                "last_name": "One",
                "email": "employee1@example.com",
                "role": User.Role.ADMIN,  # tampering attempt
            },
        )
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.role, User.Role.EMPLOYEE)

    def test_user_cannot_modify_is_active_through_profile_form(self):
        self.client.login(username="employee1", password=self.password)
        self.client.post(
            reverse("profile"),
            {
                "first_name": "Employee",
                "last_name": "One",
                "email": "employee1@example.com",
                "is_active": "false",  # tampering attempt
            },
        )
        self.employee.refresh_from_db()
        self.assertTrue(self.employee.is_active)

    def test_profile_form_updates_allowed_fields(self):
        self.client.login(username="employee1", password=self.password)
        self.client.post(
            reverse("profile"),
            {
                "first_name": "Updated",
                "last_name": "Name",
                "email": "updated@example.com",
            },
        )
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.first_name, "Updated")
        self.assertEqual(self.employee.last_name, "Name")
        self.assertEqual(self.employee.email, "updated@example.com")

    # --- Change password ---------------------------------------------------

    def test_password_change_page_requires_login(self):
        response = self.client.get(reverse("password_change"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_password_change_works(self):
        self.client.login(username="employee1", password=self.password)
        response = self.client.post(
            reverse("password_change"),
            {
                "old_password": self.password,
                "new_password1": "new-strong-pass-456",
                "new_password2": "new-strong-pass-456",
            },
        )
        self.assertRedirects(response, reverse("profile"))

        self.employee.refresh_from_db()
        self.assertTrue(self.employee.check_password("new-strong-pass-456"))
        self.assertFalse(self.employee.check_password(self.password))

    def test_password_change_invalid_current_password_is_rejected(self):
        self.client.login(username="employee1", password=self.password)
        response = self.client.post(
            reverse("password_change"),
            {
                "old_password": "totally-wrong-password",
                "new_password1": "new-strong-pass-456",
                "new_password2": "new-strong-pass-456",
            },
        )
        self.assertEqual(response.status_code, 200)  # re-renders form, no redirect

        self.employee.refresh_from_db()
        self.assertTrue(self.employee.check_password(self.password))  # unchanged

    def test_password_change_mismatched_confirmation_is_rejected(self):
        self.client.login(username="employee1", password=self.password)
        response = self.client.post(
            reverse("password_change"),
            {
                "old_password": self.password,
                "new_password1": "new-strong-pass-456",
                "new_password2": "does-not-match-789",
            },
        )
        self.assertEqual(response.status_code, 200)

        self.employee.refresh_from_db()
        self.assertTrue(self.employee.check_password(self.password))  # unchanged

    # --- Custom 403 page -----------------------------------------------------

    def test_admin_only_page_shows_access_denied_template(self):
        self.client.login(username="employee1", password=self.password)
        response = self.client.get(reverse("admin_dashboard"))
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "Access Denied", status_code=403)
        self.assertContains(
            response, "You do not have permission to access this page.", status_code=403
        )
        # No Python traceback / error details leaked to the user.
        self.assertNotContains(response, "Traceback", status_code=403)
