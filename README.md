# Restaurant Reservation System --- Backend README

## Overview

This repository contains the Django REST Framework backend for the
restaurant reservation application. It serves the customer-facing React
application and a separate admin portal. The backend is the source of
truth for reservations, menu data, capacity rules, verification, admin
permissions, and analytics.

### Main capabilities

-   Customer browser-session management and reservation lifecycle.
-   Draft reservation creation, menu selection, finalization, email OTP
    verification, confirmation, cancellation, and expiry.
-   Menu categories and menu items, including availability, special-item
    flags, and soft deletion.
-   Admin login with password verification followed by email OTP.
-   Server-side admin sessions stored using hashed tokens.
-   Dashboard summaries, reservation trends, peak hours, slot
    popularity, and trending special menu items.
-   Read-only admin reservation search, filters, pagination, and
    details.
-   Admin menu category/item management with role-based permissions.
-   Asynchronous email/background work through Celery and Redis.

## Contents

-   [Architecture](#architecture)
-   [Technology](#technology)
-   [Project layout](#project-layout)
-   [Setup](#setup)
-   [Configuration](#configuration)
-   [Database](#database)
-   [Run locally](#run-locally)
-   [Celery and Redis](#celery-and-redis)
-   [Domain models](#domain-models)
-   [Reservation lifecycle](#reservation-lifecycle)
-   [Customer API](#customer-api)
-   [Custom admin authentication](#custom-admin-authentication)
-   [Admin API reference](#admin-api-reference)
-   [Security](#security)
-   [Testing](#testing)
-   [Troubleshooting](#troubleshooting)
-   [Deployment checklist](#deployment-checklist)
-   [Implementation notes](#implementation-notes)

## Architecture

``` text
React frontend
  | HTTP, cookies, CSRF
  v
Django + Django REST Framework
  +-- Customer reservation API
  |     +-- Serializers: input validation and response shape
  |     +-- Selectors: database read/query logic
  |     +-- Services: reservation business rules and state transitions
  |     +-- Models: persistent domain data
  |
  +-- Admin API: /api/v1/admin/
  |     +-- Custom admin authentication
  |     +-- Role permissions
  |     +-- Dashboard, reservations, menu management
  |
  +-- Relational database
  |
  +-- Celery task queue --> Redis --> Celery worker --> email/background jobs
```

Keep responsibilities separate: views coordinate HTTP requests,
serializers validate data, selectors build read queries, services
enforce business rules, and models define persisted state and
constraints. Do not duplicate reservation rules across multiple views.

## Technology

The project uses Python, Django, Django REST Framework, a relational
database, Celery 5.6.x, and Redis for background processing. SQLite has
been used during development; check the active `DATABASES` setting
before assuming a different database engine. Exact package versions and
scripts should be taken from the repository's dependency files.

## Project layout

The following is a guide to the major areas; your repository may contain
additional files.

``` text
backend/
├── manage.py
├── config/
│   ├── settings.py
│   ├── urls.py
│   └── ... (WSGI/ASGI and Celery configuration)
├── reservations/
│   ├── models.py
│   ├── selectors/
│   │   └── menu.py
│   ├── services/
│   │   └── reservation_service.py
│   └── ... (customer APIs, serializers, URLs, tasks)
└── admin_portal/
    ├── models.py
    ├── middleware.py
    ├── tasks.py
    ├── services/
    │   ├── authentication.py
    │   ├── session_service.py
    │   ├── email_service.py
    │   └── dashboard.py
    ├── utils/
    │   ├── security.py
    │   └── otp.py
    └── api/
        ├── urls.py
        ├── permissions.py
        ├── pagination.py
        ├── serializers/
        └── views/
```

## Setup

### Prerequisites

-   Python compatible with the installed Django version.
-   `pip` and Python virtual environments.
-   Git.
-   Redis, if running Celery tasks locally.
-   Email backend credentials or a development email backend for OTP
    testing.
-   The frontend application for end-to-end browser testing.

### Create a virtual environment

Windows PowerShell:

``` powershell
python -m venv .venv
venv/Scripts/Activate
python -m pip install --upgrade pip
```

Install dependencies using the dependency file present in the
repository:

``` powershell
pip install -r requirements.txt
```

If the project uses `pyproject.toml` or another dependency manager,
follow that file instead. Do not maintain conflicting package-manager
lockfiles without a deliberate reason.

## Configuration

Keep secrets in environment variables or a secrets manager. Never commit
production credentials.

Example configuration concepts (the exact variable names must match
`config/settings.py` and the Celery configuration):

``` dotenv
DJANGO_SECRET_KEY=replace-with-a-long-random-secret
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
EMAIL_HOST=
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=
```

Project settings described by the current implementation include:

``` python
TIME_ZONE = "Asia/Karachi"
USE_TZ = True

BROWSER_SESSION_DAYS = 30
DRAFT_EXPIRY_MINUTES = 30

ADMIN_SESSION_DAYS = 1
ADMIN_LOGIN_CHALLENGE_MINUTES = 5
ADMIN_OTP_EXPIRY_MINUTES = 5
ADMIN_OTP_MAX_ATTEMPTS = 5
```

Verify the actual settings before changing these values.

Local frontend origins have included:

``` python
CORS_ALLOWED_ORIGINS = [
    "http://127.0.0.1:5173",
    "http://localhost:5173",
]
CSRF_TRUSTED_ORIGINS = [
    "http://127.0.0.1:5173",
    "http://localhost:5173",
]
```

Use the exact origin used by your browser. Production must use the
deployed HTTPS origin, not development origins.

## Database

After configuring dependencies and settings:

``` powershell
python manage.py check
python manage.py migrate
```

When model changes have not yet been captured in migration files, create
migrations deliberately:

``` powershell
python manage.py makemigrations
python manage.py migrate
python manage.py showmigrations
```

`makemigrations` is not required every time the server starts. Review
migration files before committing them.

### Django admin versus custom admin portal

`python manage.py createsuperuser` creates a Django built-in admin user.
The custom admin portal uses its own `AdminAccount` model and does not
rely on Django's built-in `User` login flow.

Create custom admin accounts only through a controlled management
command, approved admin interface, or trusted shell workflow. Use the
model's password hashing method rather than storing a raw password:

``` python
from admin_portal.models import AdminAccount, AdminRole

admin = AdminAccount(
    username="admin_name",
    email="admin@example.com",
    first_name="Admin",
    last_name="Account",
    role=AdminRole.SUPER_ADMIN,
)
admin.set_password("use-a-strong-unique-password")
admin.save()
```

The example is a pattern, not a production credential. Do not create
privileged accounts through an unauthenticated public endpoint.

## Run locally

Start Django:

``` powershell
python manage.py runserver
```

The usual local address is `http://127.0.0.1:8000/`. The frontend API
base URL currently defaults to `http://127.0.0.1:8000/api/v1`.

The admin API is mounted beneath:

``` text
/api/v1/admin/
```

Use the actual URL configuration as the authority for customer endpoint
paths.

## Celery and Redis

Redis must be running at the broker URL configured by the project. Start
the worker from the backend root:

``` powershell
celery -A config worker --loglevel=info --pool=solo
```

This is the command used by the current Windows development setup.
`config` must expose the project's Celery application.

Email tasks should run asynchronously. When a task depends on a database
transaction, enqueue it after commit where appropriate. The API must not
return plaintext OTP values. For local testing, use a development email
backend if desired, and ensure it is not accidentally enabled in
production.

## Domain models

### `BrowserSession`

Stores a hash of the browser token and its creation/expiry timestamps.
The raw token belongs in the browser cookie, not plaintext in the
database.

### `Customer`

Stores name, email, and phone and has a one-to-one relationship with
`BrowserSession` in the current design.

### `RestaurantSettings`

Stores slot capacity, opening/closing times, and the slot interval in
minutes.

### `TimeSlot`

Stores the unique slot datetime in `starts_at` and tracks
`booked_seats`.

### `MenuCategory`

Stores a unique name, description, active flag, and timestamps. A
category referenced by a menu item is protected from deletion.

### `MenuItem`

Stores category, title, description, image/source path, decimal price,
special status, availability, optional `seed_key`, soft-delete flag, and
timestamps. Normal item selectors hide records marked `is_deleted=True`.

### `Reservation`

Stores a unique UUID `reference_code`, customer, slot, `guest_count`,
status, selected menu item IDs in `selected_menu_items`, special-menu
eligibility, customer note, expiry, and timestamps. The actual datetime
field on `TimeSlot` is `starts_at`; the reservation guest field is
`guest_count`.

### `ReservationOTP`

Stores a hashed OTP, expiry, attempt count, sent/verified timestamps,
and active state. Do not store or log the plaintext OTP.

### `AdminAccount`

Stores username/email, password hash, names, role, active flag, last
login, and timestamps. Passwords use Django's password hashing
functions.

### `AdminLoginChallenge`

Represents the temporary OTP stage before authentication is complete. It
stores hashed challenge/OTP values, expiry, attempts, and
active/verified state.

### `AdminSession`

Stores a hash of the session token, admin relationship, expiry, last
activity, and revocation timestamp. Sessions can be revoked server-side.

## Reservation lifecycle

``` text
Browser session
    |
    v
DRAFT --> PENDING_VERIFICATION --> CONFIRMED
  |                 |                  |
  +--> EXPIRED      +--> EXPIRED       +--> COMPLETED
                    |
                    +--> CANCELLED (where permitted)
```

The frontend restores the active reservation from the backend and
renders the appropriate step based on status.

  Status                   Meaning
  ------------------------ ------------------------------------------
  `DRAFT`                  Reservation is being prepared.
  `PENDING_VERIFICATION`   Waiting for email OTP verification.
  `CONFIRMED`              Verification succeeded.
  `CANCELLED`              Reservation was cancelled.
  `COMPLETED`              Reservation is marked complete.
  `EXPIRED`                Reservation/verification window expired.

Services should own transitions, menu validation, slot-capacity checks,
OTP handling, and expiry logic. Capacity-changing operations must be
transactionally safe and reviewed for concurrency to prevent
overbooking.

## Customer API

Customer routes are defined in the reservations URL configuration.
Current capabilities include:

-   CSRF initialization.
-   Menu retrieval.
-   Draft reservation creation.
-   Draft menu update.
-   Draft finalization.
-   Active reservation retrieval.
-   OTP verification.
-   Customer reservation list/detail.
-   Cancellation where permitted.

The frontend has used `/api/v1/csrf/` for CSRF initialization and
`/reservations/active/` relative to the API base URL. Confirm the actual
URL patterns in your checkout.

Reservation request data can include `full_name`, `email`, `phone`,
`slot_id`, `guest_count`, `selected_menu_item_ids`, and `customer_note`.
The backend must validate IDs, slot capacity, guest count, menu
eligibility, and ownership; it must not trust the frontend to enforce
these rules.

Customer reservation endpoints must scope queries to the relevant
browser session/customer. A UUID reference is not a replacement for
authorization.

## Custom admin authentication

Admin authentication uses a custom sequence:

1.  The admin submits username/email and password.
2.  Credentials are checked against `AdminAccount`.
3.  A temporary `AdminLoginChallenge` is created and an OTP is emailed.
4.  The client submits challenge token and OTP.
5.  The backend validates challenge, expiry, attempts, and OTP.
6.  Only after successful verification is `AdminSession` created.
7.  A random raw session token is placed in an HttpOnly cookie; only its
    hash is stored in the database.
8.  Middleware resolves the cookie to a valid session and sets
    `request.admin`.
9.  DRF permissions separately enforce the admin role.

Known endpoints (verify exact suffixes in `admin_portal/api/urls.py`):

  -----------------------------------------------------------------------------
  Method                  Endpoint                      Purpose
  ----------------------- ----------------------------- -----------------------
  `POST`                  `/api/v1/admin/login/`        Validate credentials
                                                        and start OTP
                                                        challenge.

  `POST`                  `/api/v1/admin/verify-otp/`   Verify OTP and create
                                                        session.

  `POST`                  `/api/v1/admin/logout/`       Revoke session and
                                                        clear cookie.

  `GET`                   `/api/v1/admin/me/`           Return current admin
                                                        identity.
  -----------------------------------------------------------------------------

## Admin API reference

### Dashboard

  ------------------------------------------------------------------------------------------------
  Method                  Endpoint                                         Purpose
  ----------------------- ------------------------------------------------ -----------------------
  `GET`                   `/api/v1/admin/dashboard/`                       Summary cards and
                                                                           status breakdown.

  `GET`                   `/api/v1/admin/dashboard/trends/`                Reservation trends over
                                                                           a date range.

  `GET`                   `/api/v1/admin/dashboard/peak-hours/`            Distribution by hour.

  `GET`                   `/api/v1/admin/dashboard/slot-popularity/`       Popular time slots.

  `GET`                   `/api/v1/admin/dashboard/trending-food-items/`   Most-selected special
                                                                           items.
  ------------------------------------------------------------------------------------------------

Current dashboard reservation metrics use `CONFIRMED` reservations for
confirmed-reservation summaries; status breakdowns can include other
statuses. Trending-food logic counts selected item IDs in Python for
SQLite compatibility. Check serializer/query parameters for exact
date-range formats.

### Reservations

The admin reservations API is intentionally read-only in the current
requirements.

``` text
GET /api/v1/admin/reservations/
GET /api/v1/admin/reservations/<reference_code>/
```

List filters:

  Parameter     Purpose
  ------------- --------------------------------------------------------
  `search`      Customer name, email, phone, or reservation reference.
  `date_from`   Inclusive lower slot-date bound (`YYYY-MM-DD`).
  `date_to`     Inclusive upper slot-date bound (`YYYY-MM-DD`).
  `status`      Valid reservation status.
  `page`        Page number.
  `page_size`   Page size, bounded by the API maximum.

Example:

``` text
/api/v1/admin/reservations/?status=CONFIRMED&date_from=2026-10-01&date_to=2026-10-31&page=1&page_size=20
```

Paginated responses have a structure like:

``` json
{
  "count": 57,
  "next": null,
  "previous": null,
  "results": []
}
```

This is illustrative; actual data and next/previous links depend on the
request. Arbitrary search text can validly return zero matches. Invalid
dates or unsupported status values should fail validation. `date_from`
must not be later than `date_to`.

### Menu categories

  ---------------------------------------------------------------------------------------
  Method                  Endpoint                                Purpose
  ----------------------- --------------------------------------- -----------------------
  `GET`                   `/api/v1/admin/menu/categories/`        List categories.

  `POST`                  `/api/v1/admin/menu/categories/`        Create category.

  `GET`                   `/api/v1/admin/menu/categories/<id>/`   Retrieve category.

  `PATCH`                 `/api/v1/admin/menu/categories/<id>/`   Update category.

  `DELETE`                `/api/v1/admin/menu/categories/<id>/`   Delete if no protected
                                                                  relation blocks it.
  ---------------------------------------------------------------------------------------

Categories used by menu items are protected. Prefer deactivation with
`is_active=false` if the category should remain in historical data.

### Menu items

  Method     Endpoint                           Purpose
  ---------- ---------------------------------- -----------------------------
  `GET`      `/api/v1/admin/menu/items/`        List/filter/paginate items.
  `POST`     `/api/v1/admin/menu/items/`        Create item.
  `GET`      `/api/v1/admin/menu/items/<id>/`   Retrieve item.
  `PATCH`    `/api/v1/admin/menu/items/<id>/`   Update item.
  `DELETE`   `/api/v1/admin/menu/items/<id>/`   Soft-delete item.

Supported list filters include `search`, `category`, `is_special`,
`is_available`, `page`, and `page_size`. Example:

``` text
/api/v1/admin/menu/items/?search=chicken&category=2&is_special=true&is_available=true&page=1&page_size=20
```

The menu-management role set is `SUPER_ADMIN`, `ADMIN`, and
`MENU_MANAGER`. `RESERVATION_VIEWER` should not have menu management
access.

Soft deletion sets `is_deleted=True` and `is_available=False`. The
database row and historical reservation references remain. Ordinary menu
selectors exclude soft-deleted items, but historical analytics may still
need them.

## Authentication, authorization, cookies, and CSRF

Authentication answers "who is this request from?" Authorization answers
"may this identity perform this action?" Both checks are required.

The frontend uses cookie credentials. The browser session/admin session
cookie is HttpOnly. The CSRF cookie is readable by JavaScript so the
frontend can send it in `X-CSRFToken` for unsafe methods.

CORS and CSRF are different: - CORS governs whether browser JavaScript
can access cross-origin responses. - CSRF protects cookie-authenticated
unsafe requests from cross-site request forgery.

Do not disable CSRF on mutation endpoints to fix a CORS problem.
Production cookie settings must use HTTPS and appropriate `Secure`,
`HttpOnly`, `SameSite`, domain, path, and expiry settings.

## Security

Before production:

-   Set `DEBUG=False`.
-   Store secret key, database/email credentials, and broker secrets
    outside source control.
-   Set `ALLOWED_HOSTS` narrowly.
-   Use HTTPS and secure cookies.
-   Restrict CORS and CSRF trusted origins.
-   Keep CSRF protection enabled.
-   Never log raw tokens, OTPs, passwords, or sensitive customer
    information.
-   Retain OTP expiry and attempt limits; consider rate limiting login
    and OTP endpoints.
-   Apply role checks to every admin endpoint.
-   Validate all IDs and business rules server-side.
-   Use transactions/locking for capacity-changing operations.
-   Back up the database and test restoration.
-   Keep dependencies patched.
-   Run:

``` powershell
python manage.py check --deploy
```

## Testing

Run Django tests:

``` powershell
python manage.py test
```

Use pytest instead if that is what the repository configures.

Recommended test areas:

-   Draft lifecycle, expiry, slot capacity, duplicate menu IDs, guest
    count, OTP verification.
-   Concurrent booking attempts and correct capacity accounting.
-   Customer ownership isolation.
-   Admin invalid credentials, inactive account, OTP expiry/attempt
    limit, session expiry/revocation, logout.
-   Role-based access for every admin endpoint.
-   Reservation search/date/status validation and pagination.
-   Menu filters, category protection, and soft deletion.
-   Dashboard calculations and timezone handling.

### Useful shell diagnostics

``` powershell
python manage.py shell
```

``` python
from reservations.models import MenuItem
from reservations.selectors.menu import get_admin_menu_items

print("All rows:", MenuItem.objects.count())
print("Not deleted:", MenuItem.objects.filter(is_deleted=False).count())
print("Selector result:", get_admin_menu_items().count())
```

When an API seems to return one item, compare these counts with the
response `count`, `results` length, and actual query string.
`page_size=1` intentionally returns one item per page even if total
`count` is much larger.

## Troubleshooting

### CORS

Verify the exact browser origin, allow it in Django, ensure credential
support is configured, and restart the server. Do not use wildcard
origins for credentialed requests.

### CSRF failure

Initialize CSRF, verify the `csrftoken` cookie, send `X-CSRFToken`,
include credentials, and trust the exact frontend origin. Do not exempt
mutation endpoints.

### Admin API returns 401/403

Complete OTP verification, inspect the `admin_session` cookie, confirm
it is not expired/revoked, verify the account is active, and check the
role required by the view.

### OTP email is not sent

Check Redis, worker logs, email settings, task failure handling, and
whether the task was queued after the database transaction committed.

### Menu list contains fewer records than expected

Check query parameters, `page_size`, category/special/availability
filters, `is_deleted`, queryset count, and paginated `count` versus
`results.length`.

### Database-specific JSON errors

Trending-item selection counting currently uses Python `Counter` for
SQLite compatibility. If switching to database-specific JSON
aggregation, test against the actual target database engine.

## Deployment checklist

-   [ ] `DEBUG=False` and production secrets are externalized.
-   [X] `ALLOWED_HOSTS` Implemented.
-   [X] HTTPS and secure cookies are configured.
-   [X] CORS/CSRF origins match the deployed frontend.
-   [X] Migrations are applied and backups/restoration are tested.
-   [X] Redis and Celery worker are running if needed.
-   [X] Email provider is tested.
-   [X] Admin accounts have appropriate roles and strong credentials.
-   [X] Logging avoids sensitive information.
-   [X] `python manage.py check --deploy` has been reviewed.
-   [X] Tests cover authorization, OTP, ownership, capacity, filtering,
    and pagination.
-   [X] Monitoring and error reporting are configured.
-   [ ] .gitignore, env and settings are not configured properly, for both frontend and backend.

## Implementation notes

-   The custom admin portal uses `AdminAccount`, `AdminLoginChallenge`,
    and `AdminSession`, not Django's built-in user login.
-   Browser sessions and admin sessions are separate.
-   Customer reservation APIs must remain ownership-scoped.
-   Admin reservations are read-only under the current requirements.
-   Menu item deletion is soft deletion.
-   `TimeSlot.starts_at` is the actual datetime field;
    `Reservation.guest_count` is the actual guest-count field.
-   Selected menu item IDs are stored in the reservation JSON field.
-   Exact URL suffixes, dependency versions, settings variable names,
    and deployment commands must be confirmed against the current
    repository.
