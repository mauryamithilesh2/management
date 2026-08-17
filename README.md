# Employee Task Management System

Internal Django application for managing employee tasks, for a team of
approximately 10–15 users. Two roles: **Employee** and **Admin**.

> **Status:** Phase 2 complete — project foundation, custom user model,
> roles, and authentication. Tasks and dashboards are not implemented yet.

## Tech stack

- Python / Django (Django templates, no frontend framework in V1)
- SQLite for local development (PostgreSQL-compatible from day one)
- Plain HTML/CSS (no JS framework)

## Project layout

```
etms/
├── manage.py
├── config/            # settings, root urls, wsgi/asgi
├── accounts/          # custom User model, auth views, forms
├── templates/          # base.html + app templates
├── static/css/         # app stylesheet
├── requirements.txt
├── .env.example
└── .gitignore
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env and set a real SECRET_KEY (see "Generating a secret key" below)

python manage.py migrate
python manage.py createsuperuser   # create your first Admin account
python manage.py runserver
```

Visit `http://127.0.0.1:8000/login/` to sign in.

### Generating a secret key

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

Paste the output into `SECRET_KEY` in your `.env` file.

## Environment variables (`.env`)

| Variable        | Purpose                                             | Default (dev)         |
|-----------------|------------------------------------------------------|------------------------|
| `SECRET_KEY`    | Django cryptographic signing key                     | *(must be set)*        |
| `DEBUG`         | Enable/disable debug mode                            | `True`                 |
| `ALLOWED_HOSTS` | Comma-separated list of allowed hostnames             | `127.0.0.1,localhost`  |
| `DATABASE_URL`  | If set, overrides SQLite with e.g. a Postgres URL     | *(empty → SQLite)*     |

## Users & roles

- A single custom `User` model (`accounts.User`, extends Django's
  `AbstractUser`) is used for both Employees and Admins — there is no
  separate authentication system per role.
- `role` is either `EMPLOYEE` (default) or `ADMIN`.
- The very first Admin account should be created with
  `python manage.py createsuperuser` and setting `role=ADMIN` via the Django
  admin site (`/admin/`) — after that, admins can promote further employees
  through the in-app Admin Request workflow (a later phase).

## Running tests

```bash
python manage.py test
```

Current test coverage (Phase 2): user model defaults/roles, password
hashing, login (valid/invalid/inactive user), logout, and access control on
the protected landing page.

## Roadmap

See the phased implementation plan: roles/permissions → tasks → employee
dashboard → admin dashboard → admin request workflow → user management →
UI polish → full test/security pass.
