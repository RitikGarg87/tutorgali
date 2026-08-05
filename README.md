# TutorGali

TutorGali is a Django-based web application that connects students with tutors. Students can search for tutors by subject, grade, teaching mode, and location. Tutors can create profiles, set their availability, manage booking requests, and purchase subscriptions to unlock lead access.

## Features

- User registration and login with email or mobile number
- Separate dashboards for students and tutors
- Tutor profile onboarding with qualifications, subjects, rates, and availability
- Location-based tutor search using latitude and longitude
- Student-to-tutor booking requests with accept/reject workflow
- Admin verification workflow for tutors
- Razorpay subscription payments for tutors

## Tech Stack

- Python 3.12
- Django 6.0.7
- SQLite
- Razorpay Python SDK
- geopy
- HTML, CSS, JavaScript

## Setup

1. Clone the repository and navigate to the project directory.

2. Activate the virtual environment:

   ```bash
   source env/bin/activate
   ```

3. Run migrations:

   ```bash
   python manage.py migrate
   ```

4. Create a superuser:

   ```bash
   python manage.py createsuperuser
   ```

5. Start the development server:

   ```bash
   python manage.py runserver
   ```

6. Open http://127.0.0.1:8000/ in your browser.

## Project Structure

- `tutorgali/` — Django project settings and URL configuration
- `users/` — Main Django app containing models, views, forms, templates, and admin
- `static/` — Static assets (CSS)
- `media/` — User-uploaded files such as certificates and ID proofs

## Important Notes

- `requirements.txt` is currently empty. Installed packages are tracked in the virtual environment.
- Hardcoded secrets in `tutorgali/settings.py` (SECRET_KEY, email password, Razorpay keys) should be moved to environment variables before production use.
- Tutor verification is managed through the Django admin panel.
