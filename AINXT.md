# AINXT.md

This file provides guidance to AiNxt (AiNxt platform) when working with code in this repository.

## Project Overview

TutorGali is a Django web application that connects students with tutors. It supports two roles (student and tutor), tutor profile onboarding, tutor search by location/subject/grade, booking requests, and Razorpay-based subscription payments.

## Tech Stack

- Python 3.12
- Django 5.2.7 / 6.0.7 (currently installed: 6.0.7)
- SQLite (`db.sqlite3`)
- Razorpay Python SDK (`razorpay`)
- geopy (`geopy`) for address geocoding
- HTML templates with vanilla JavaScript; static files in `static/`

## Common Commands

Activate the virtual environment before running any Django command:

```bash
source env/bin/activate
```

Run the development server:

```bash
python manage.py runserver
```

Run migrations:

```bash
python manage.py migrate
```

Create a superuser:

```bash
python manage.py createsuperuser
```

Open the Django shell:

```bash
python manage.py shell
```

Run Django checks:

```bash
python manage.py check
```

There are no configured test suites for this project. `users/tests.py` is empty and `test.py` at the repository root is an unrelated algorithmic snippet.

## Architecture

### Project Layout

- `tutorgali/` — Django project configuration (`settings.py`, `urls.py`, `wsgi.py`, `asgi.py`).
- `users/` — Single Django app containing all business logic: models, forms, views, templates, custom auth backend, and admin configuration.
- `static/` — CSS and other static assets.
- `media/` — User-uploaded files (certificates, ID proofs).
- `env/` — Python virtual environment.

### Authentication

- Custom authentication backend: `users/backends.py::EmailOrMobileBackend`.
- Users can log in with email, mobile number (10 digits), or username.
- `AUTHENTICATION_BACKENDS` in `tutorgali/settings.py` lists the custom backend first and the default `ModelBackend` as fallback.
- A `Profile` instance is auto-created for every new `User` via `users/signals.py`.

### Core Models (`users/models.py`)

- `Profile` — One-to-one with `User`. Stores role (student/tutor), address, verification status, lat/long, and tutor-specific fields.
- `TutorGradeRate` — Grade/subject/rate rows per tutor profile.
- `TutorAvailability` — Single-row availability with JSON time slots (Mon-Sat).
- `BookingRequest` — Student-to-tutor booking request with status (pending/accepted/rejected).
- `SubscriptionPlan`, `TutorSubscription`, `SubscriptionPayment` — Razorpay subscription flow.

### Key Views (`users/views.py`)

- `tutor_onboarding` — Multi-step tutor profile completion with grade-rate formset.
- `search_tutors` — Filters approved/completed tutors by grade, subject, teaching mode, availability slot, and distance (Haversine formula).
- `create_booking_request` / `tutor_booking_requests` / `update_booking_request_status` — Booking request lifecycle.
- `subscription_plans`, `create_subscription_payment`, `subscription_payment_callback` — Razorpay subscription payments.

### Forms (`users/forms.py`)

- `SignUpForm` — Creates `User` + `Profile`; auto-generates username from email.
- `TutorOnboardingForm` — Captures tutor details; stores multiple-choice fields as comma-separated strings.
- `TutorGradeRateForm` — Used inside a formset for grade/subject/rates.

### Admin (`users/admin.py`)

- Custom `UserAdmin` with inline `Profile`.
- `ProfileAdmin` exposes verification actions (`approve_verification`, `reject_verification`).

## Important Notes

- `requirements.txt` is currently empty. Installed packages are tracked only in the virtual environment. Use `pip freeze > requirements.txt` if a dependency manifest is needed.
- `tutorgali/settings.py` contains hardcoded secrets (`SECRET_KEY`, Gmail app password, Razorpay test keys). These should be moved to environment variables for any non-local deployment.
- `LOGIN_REDIRECT_URL` is defined twice in `settings.py`; the second value (`'after_login_redirect'`) takes effect.
- The map/location picker on the tutor onboarding page currently uses Google Maps with a hardcoded API key. If coordinates fail to save, the issue is almost always that the Google Maps script did not load or `initMap` did not run.
- Subscription end dates are calculated as `today + timedelta(days=30 * months)` — an approximation, not calendar-accurate.
