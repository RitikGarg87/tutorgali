from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import views as auth_views, login as auth_login, logout as auth_logout, authenticate
from django.contrib import messages
from django.forms import modelformset_factory
from django.contrib.auth.models import User
from django.db.models import Count, Sum, Q, Avg
from functools import wraps
from django.urls import reverse_lazy, reverse
from math import radians, sin, cos, asin, sqrt
from urllib.parse import urlencode
from .forms import (
    SignUpForm, ProfileForm, VerificationForm,
    EmailOrMobileLoginForm, TutorOnboardingForm, TutorGradeRateForm,
    TutorReviewForm, CITIES_BY_STATE,
)
from .models import TutorGradeRate, TutorAvailability, Profile, BookingRequest, SubscriptionPlan, TutorSubscription, SubscriptionPayment, TutorReview
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import timedelta
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.mail import send_mail
from django.template.loader import render_to_string
import razorpay
import json
import random
import requests
import hmac
import hashlib
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone as tz
import logging

logger = logging.getLogger(__name__)

def get_razorpay_client():
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

class CustomLoginView(auth_views.LoginView):
    template_name = 'users/login.html'
    authentication_form = EmailOrMobileLoginForm

    def form_valid(self, form):
        """Handle remember me checkbox"""
        remember = self.request.POST.get('remember')
        if remember:
            self.request.session.set_expiry(1209600)  # 2 weeks
        else:
            self.request.session.set_expiry(0)
        return super().form_valid(form)

    def get_success_url(self):
        """Redirect to appropriate dashboard after login"""
        if self.request.user.profile.role == 'student':
            return reverse_lazy('student_dashboard')
        elif self.request.user.profile.role == 'tutor':
            if not self.request.user.profile.profile_completed:
                return reverse_lazy('tutor_onboarding')
            return reverse_lazy('tutor_dashboard')
        else:
            return reverse_lazy('login')

def home(request):
    return render(request, 'users/home.html')

def _filter_tutors_with_distance(request):
    """
    Shared tutor search/filter logic used by both the logged-in student
    search (search_tutors) and the public homepage search (public_search_tutors).
    Returns (tutors_with_distance, filters_dict) - does NOT attach any
    per-user data (booking_status / my_review) - callers add that themselves
    if a logged-in student profile is available.
    """
    grade = request.GET.get('grade')
    subject = (request.GET.get('subject') or '').strip().lower()
    mode = request.GET.get('mode')
    distance_km = float(request.GET.get('distance_km') or 5)
    lat = request.GET.get('lat')
    lng = request.GET.get('lng')
    time_slot_pref = request.GET.get('time_slot')

    tutors = Profile.objects.filter(
        role='tutor',
        profile_completed=True,
        verification_status='approved',
    ).select_related('user').prefetch_related('grade_rates', 'availability')

    # Grade + Subject must match the SAME grade_rates row (not separate rows)
    if grade and subject:
        tutors = tutors.filter(
            grade_rates__grade=grade,
            grade_rates__subjects__icontains=subject
        )
    elif grade:
        tutors = tutors.filter(grade_rates__grade=grade)
    elif subject:
        tutors = tutors.filter(grade_rates__subjects__icontains=subject)

    if mode:
        tutors = tutors.filter(teaching_mode__icontains=mode)

    tutors = tutors.distinct()

    user_lat = user_lng = None
    if lat and lng:
        try:
            user_lat = float(lat)
            user_lng = float(lng)
        except ValueError:
            user_lat = user_lng = None

    tutors_with_distance = []
    for tutor in tutors:
        if tutor.latitude is not None and tutor.longitude is not None and user_lat is not None:
            dist = haversine_km(user_lat, user_lng, tutor.latitude, tutor.longitude)
        else:
            dist = None

        # availability filter (exact 1-hour slot)
        availability = getattr(tutor, 'availability', None)
        if not slot_in_preference(
            getattr(availability, 'time_slots', []),
            time_slot_pref
        ):
            continue

        if dist is None or dist <= distance_km:
            tutors_with_distance.append((tutor, dist))

    tutors_with_distance.sort(
        key=lambda x: float('inf') if x[1] is None else x[1]
    )

    filters = {
        'grade': grade,
        'subject': subject,
        'mode': mode,
        'distance_km': int(distance_km),
        'time_slot': time_slot_pref,
        'user_lat': user_lat,
        'user_lng': user_lng,
    }

    return tutors_with_distance, filters

def public_search_tutors(request):
    """
    Public tutor search - no login required. Anyone can see results.
    Does not attach booking_status / my_review - the template shows a "Sign Up to Contact" CTA instead
    of the real booking form for anonymous visitors.

    Requires at least one filter (grade/subject/mode) before running the
    query - prevents anonymous visitors from listing every tutor in the database.
    """
    has_filter = bool(
        (request.GET.get('grade') or '').strip()
        or (request.GET.get('subject') or '').strip()
        or (request.GET.get('mode') or '').strip()
    )

    if not has_filter:
        context = {
            'results': None,
            'GOOGLE_MAPS_API_KEY': settings.GOOGLE_MAPS_API_KEY,
            'grade': '',
            'subject': '',
            'mode': '',
            'distance_km': 5,
        }
        return render(request, 'users/public_tutor_results.html', context)

    tutors_with_distance, filters = _filter_tutors_with_distance(request)

    paginator = Paginator(tutors_with_distance, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'results': page_obj,
        'GOOGLE_MAPS_API_KEY': settings.GOOGLE_MAPS_API_KEY,
        **filters,
    }

    return render(request, 'users/public_tutor_results.html', context)



@require_POST
def send_otp(request):
    """AJAX view — generate OTP and send via Fast2SMS (plain SMS)."""
    import re as _re
    import logging
    logger = logging.getLogger(__name__)

    mobile = request.POST.get('mobile_number', '').strip()
    mobile = _re.sub(r'[^0-9]', '', mobile)

    if len(mobile) != 10 or mobile[0] not in '6789':
        return JsonResponse({'success': False, 'error': 'Enter a valid 10-digit Indian mobile number.'})

    if Profile.objects.filter(mobile_number=mobile).exists():
        return JsonResponse({'success': False, 'error': 'This mobile number is already registered.'})

    # ── 60-second cooldown (session-based) ──────────────────────────────────
    from datetime import datetime as _dt
    last_sent_str = request.session.get('otp_last_sent')
    if last_sent_str:
        try:
            last_sent = _dt.fromisoformat(last_sent_str)
            elapsed = (tz.now() - last_sent).total_seconds()
            if elapsed < 60:
                remaining = int(60 - elapsed)
                return JsonResponse({
                    'success': False,
                    'error': f'Please wait {remaining} second(s) before requesting a new OTP.',
                })
        except (ValueError, TypeError):
            pass  # malformed timestamp — allow resend

    # Generate 6-digit OTP
    otp = str(random.randint(100000, 999999))

    # ── Send via Fast2SMS ────────────────────────────────────────────────────
    dev_mode = False
    try:
        import requests as _requests
        api_key = getattr(settings, 'FAST2SMS_API_KEY', '')
        if not api_key or api_key.startswith('YOUR_'):
            raise ValueError('Fast2SMS API key not configured')

        response = _requests.post(
            'https://www.fast2sms.com/dev/bulkV2',
            headers={
                'authorization': api_key,
                'Content-Type': 'application/json',
            },
            json={
                'route': 'otp',
                'variables_values': otp,
                'numbers': mobile,
            },
            timeout=10,
        )
        data = response.json()
        if not data.get('return', False):
            raise ValueError(f"Fast2SMS error: {data.get('message', 'Unknown error')}")

    except Exception as e:
        logger.warning('[DEV OTP] Fast2SMS unavailable (%s). OTP for +91%s: %s', e, mobile, otp)
        dev_mode = True

    # ── Store OTP in session after send attempt ──────────────────────────────
    # Stored regardless of SMS success so dev fallback works locally
    now_iso = tz.now().isoformat()
    request.session['otp']           = otp
    request.session['otp_mobile']    = mobile
    request.session['otp_time']      = now_iso
    request.session['otp_attempts']  = 0
    request.session['otp_verified']  = False
    request.session['otp_last_sent'] = now_iso

    if dev_mode:
        return JsonResponse({
            'success': True,
            'message': '[DEV] SMS unavailable — OTP printed to Django console. Check your terminal.',
        })

    masked = f'+91-{mobile[:3]}XXXXXXX{mobile[-2:]}'
    return JsonResponse({'success': True, 'message': f'OTP sent to {masked} via SMS. Check your messages!'})


@require_POST
def verify_otp(request):
    """AJAX view — verify OTP entered by user."""
    mobile  = request.POST.get('mobile_number', '').strip()
    entered = request.POST.get('otp', '').strip()

    session_otp    = request.session.get('otp')
    session_mobile = request.session.get('otp_mobile')
    otp_time_str   = request.session.get('otp_time')
    attempts       = request.session.get('otp_attempts', 0)

    # Max attempts check
    if attempts >= 3:
        return JsonResponse({'success': False, 'error': 'Too many wrong attempts. Please request a new OTP.'})

    # Expiry check (10 minutes)
    if otp_time_str:
        from datetime import datetime, timezone as dt_tz
        otp_time = datetime.fromisoformat(otp_time_str)
        if (tz.now() - otp_time).total_seconds() > 600:
            return JsonResponse({'success': False, 'error': 'OTP has expired. Please request a new one.'})

    # Match check
    if session_mobile != mobile or session_otp != entered:
        request.session['otp_attempts'] = attempts + 1
        remaining = 3 - (attempts + 1)
        return JsonResponse({'success': False, 'error': f'Invalid OTP. {remaining} attempt(s) remaining.'})

    # All good
    request.session['otp_verified'] = True
    return JsonResponse({'success': True, 'message': 'Mobile number verified successfully!'})


def register(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)

        # Gate 1 — OTP must have been verified in this session
        # if not request.session.get('otp_verified'):
        #     messages.error(request, 'Please verify your mobile number with OTP before registering.')
        #     return render(request, 'users/register.html', {'form': form})

        if form.is_valid():
            # Gate 2 — submitted mobile must match the one that was OTP-verified
            # submitted_mobile = form.cleaned_data.get('mobile_number')
            # if submitted_mobile != request.session.get('otp_mobile'):
            #     form.add_error(
            #         'mobile_number',
            #         'Mobile number does not match the verified number. Please re-verify.',
            #     )
            #     return render(request, 'users/register.html', {'form': form})

            user = form.save()
            # Clear all OTP session keys after successful registration
            for key in ('otp', 'otp_mobile', 'otp_time', 'otp_attempts', 'otp_verified', 'otp_last_sent'):
                request.session.pop(key, None)
            messages.success(request, 'Account created successfully! Please login.')
            return redirect('login')
    else:
        form = SignUpForm()
    return render(request, 'users/register.html', {'form': form})


@login_required
def tutor_onboarding(request):
    if request.user.profile.role != 'tutor':
        return redirect('student_dashboard')

    # if request.user.profile.profile_completed:
    #     return redirect('tutor_dashboard')

    # Create formset for 8 grades
    GradeRateFormSet = modelformset_factory(
        TutorGradeRate,
        form=TutorGradeRateForm,
        extra=8,
        max_num=8,
        can_delete=False
    )

    if request.method == 'POST':
        profile_form = TutorOnboardingForm(request.POST, instance=request.user.profile)
        formset = GradeRateFormSet(request.POST, queryset=TutorGradeRate.objects.none())

        if profile_form.is_valid() and formset.is_valid():
            # Save profile
            profile = profile_form.save(commit=False)

            # Handle qualification
            if profile_form.cleaned_data['qualification'] == 'Other':
                profile.qualification = profile_form.cleaned_data['qualification_other']
            else:
                profile.qualification = profile_form.cleaned_data['qualification']

            # Save comma-separated values
            profile.languages = ','.join(profile_form.cleaned_data['languages'])
            profile.school_boards = ','.join(profile_form.cleaned_data['school_boards'])
            profile.teaching_mode = ','.join(profile_form.cleaned_data['teaching_mode'])
            profile.profile_completed = True
            profile.save()

            # Delete existing grade rates for this tutor
            TutorGradeRate.objects.filter(profile=request.user.profile).delete()

            # Save grade rates
            grade_choices = [
                'nursery_to_5', 'grade_6', 'grade_7', 'grade_8',
                'grade_9', 'grade_10', 'grade_11', 'grade_12'
            ]

            for i, form in enumerate(formset):
                if form.cleaned_data and form.cleaned_data.get('subjects'):
                    grade_rate = form.save(commit=False)
                    grade_rate.profile = request.user.profile
                    grade_rate.grade = grade_choices[i]
                    grade_rate.save()

            messages.success(request, 'Profile completed successfully! Welcome to TutorGali!')
            return redirect('tutor_dashboard')
        else:
            # Show errors
            messages.error(request, 'Please correct the errors below.')
    else:
        profile_form = TutorOnboardingForm(instance=request.user.profile)
        formset = GradeRateFormSet(queryset=TutorGradeRate.objects.none())

    # Prepare grade labels
    grade_labels = [
        'Nursery to 5th', '6th', '7th', '8th',
        '9th', '10th', '11th', '12th'
    ]

    # Zip formset with labels
    forms_with_labels = zip(formset, grade_labels)

    return render(request, 'users/tutor_onboarding.html', {
        'profile_form': profile_form,
        'formset': formset,
        'forms_with_labels': forms_with_labels,
        'cities_by_state_json': json.dumps(CITIES_BY_STATE),
        'GOOGLE_MAPS_API_KEY': settings.GOOGLE_MAPS_API_KEY,
    })


@login_required
def profile(request):
    profile = request.user.profile
    role = profile.role

    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=profile, role=role)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
    else:
        form = ProfileForm(instance=profile, role=role)

    return render(request, 'users/profile.html', {'form': form, 'profile': profile})


@login_required
def verification(request):
    if request.user.profile.role != 'tutor':
        messages.error(request, 'Only tutors can access verification.')
        return redirect('student_dashboard')

    profile = request.user.profile

    if request.method == 'POST':
        form = VerificationForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.verification_status = 'pending'
            profile.save()
            messages.success(request, 'Documents submitted successfully! Awaiting admin approval.')
            return redirect('tutor_dashboard')
    else:
        form = VerificationForm(instance=profile)

    return render(request, 'users/verification.html', {'form': form, 'profile': profile})


@login_required
def student_dashboard(request):
    profile = request.user.profile
    if profile.role == 'tutor':
        if not profile.profile_completed:
            return redirect('tutor_onboarding')
        return redirect('tutor_dashboard')

    return render(request, 'users/student_dashboard.html', {'profile': profile})


@login_required
def tutor_dashboard(request):
    profile = request.user.profile
    if profile.role != 'tutor':
        return redirect('student_dashboard')
    if not profile.profile_completed:
        return redirect('tutor_onboarding')

    grade_rates = TutorGradeRate.objects.filter(profile=profile)

    # Get availability (single row, Mon-Sat only)
    try:
        availability = profile.availability
        total_hours = availability.get_total_hours()  # slots * 6 days
    except TutorAvailability.DoesNotExist:
        total_hours = 0
        availability = None

    return render(request, 'users/tutor_dashboard.html', {
        'profile': profile,
        'grade_rates': grade_rates,
        'hours_per_week': total_hours,
        'total_slots': total_hours,
        'availability': availability,
    })


@login_required
def tutor_edit_profile(request):
    """Edit tutor profile with pre-filled data"""
    if request.user.profile.role != 'tutor':
        return redirect('student_dashboard')

    # Create formset for 8 grades
    GradeRateFormSet = modelformset_factory(
        TutorGradeRate,
        form=TutorGradeRateForm,
        extra=8,
        max_num=8,
        can_delete=False
    )

    # Grade choices
    grade_choices = [
        'nursery_to_5', 'grade_6', 'grade_7', 'grade_8',
        'grade_9', 'grade_10', 'grade_11', 'grade_12'
    ]

    if request.method == 'POST':
        profile_form = TutorOnboardingForm(request.POST, instance=request.user.profile)
        formset = GradeRateFormSet(request.POST, queryset=TutorGradeRate.objects.none())

        if profile_form.is_valid() and formset.is_valid():
            # Save profile
            profile = profile_form.save(commit=False)

            # Handle qualification
            if profile_form.cleaned_data['qualification'] == 'Other':
                profile.qualification = profile_form.cleaned_data['qualification_other']
            else:
                profile.qualification = profile_form.cleaned_data['qualification']

            # Save comma-separated values
            profile.languages = ','.join(profile_form.cleaned_data['languages'])
            profile.school_boards = ','.join(profile_form.cleaned_data['school_boards'])
            profile.teaching_mode = ','.join(profile_form.cleaned_data['teaching_mode'])
            profile.save()

            # Delete all existing grade rates
            TutorGradeRate.objects.filter(profile=request.user.profile).delete()

            # Save new grade rates
            for i, form in enumerate(formset):
                if form.cleaned_data and form.cleaned_data.get('subjects'):
                    grade_rate = form.save(commit=False)
                    grade_rate.profile = request.user.profile
                    grade_rate.grade = grade_choices[i]
                    grade_rate.save()

            messages.success(request, 'Profile updated successfully!')
            return redirect('tutor_dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        # GET request - Pre-fill form
        profile = request.user.profile
        profile_form = TutorOnboardingForm(instance=profile)

        # Pre-select checkboxes for languages, boards, teaching modes
        if profile.languages:
            profile_form.initial['languages'] = profile.languages.split(',')
        if profile.school_boards:
            profile_form.initial['school_boards'] = profile.school_boards.split(',')
        if profile.teaching_mode:
            profile_form.initial['teaching_mode'] = profile.teaching_mode.split(',')

        # Pre-fill lat/lng hidden fields from saved profile values
        if profile.latitude is not None:
            profile_form.initial['latitude'] = profile.latitude
        if profile.longitude is not None:
            profile_form.initial['longitude'] = profile.longitude

        # Get existing grade rates
        existing_rates = TutorGradeRate.objects.filter(profile=profile)
        existing_dict = {rate.grade: rate for rate in existing_rates}

        # Create empty formset
        formset = GradeRateFormSet(queryset=TutorGradeRate.objects.none())

        # Pre-fill formset with existing data
        for i, form in enumerate(formset.forms):
            grade = grade_choices[i]
            if grade in existing_dict:
                rate = existing_dict[grade]
                form.initial = {
                    'subjects': rate.subjects,
                    'rate_online': rate.rate_online,
                    'rate_student_home': rate.rate_student_home,
                    'rate_my_home': rate.rate_my_home,
                }

    # Prepare grade labels (needed for both GET and failed POST)
    grade_labels = [
        'Nursery to 5th', '6th', '7th', '8th',
        '9th', '10th', '11th', '12th'
    ]

    # Get existing grades for JavaScript (needed for both GET and failed POST)
    existing_grades_list = list(
        TutorGradeRate.objects.filter(
            profile=request.user.profile
        ).values_list('grade', flat=True)
    )

    # Map grade names to indices for JavaScript
    existing_grade_indices = []
    for grade in existing_grades_list:
        if grade in grade_choices:
            existing_grade_indices.append(grade_choices.index(grade))

    # Zip formset with labels
    forms_with_labels = zip(formset, grade_labels)

    return render(request, 'users/tutor_edit_profile.html', {
        'profile_form': profile_form,
        'formset': formset,
        'forms_with_labels': forms_with_labels,
        'existing_grade_indices': existing_grade_indices,
        'cities_by_state_json': json.dumps(CITIES_BY_STATE),
        'is_edit': True,
        'GOOGLE_MAPS_API_KEY': settings.GOOGLE_MAPS_API_KEY,
    })


@login_required
def tutor_availability(request):
    """Manage tutor's availability - Monday to Saturday only"""
    if request.user.profile.role != 'tutor':
        messages.error(request, 'Only tutors can access this page.')
        return redirect('home')

    time_slots = [
        ('04:00-05:00', '04:00 AM - 05:00 AM'),
        ('05:00-06:00', '05:00 AM - 06:00 AM'),
        ('06:00-07:00', '06:00 AM - 07:00 AM'),
        ('07:00-08:00', '07:00 AM - 08:00 AM'),
        ('08:00-09:00', '08:00 AM - 09:00 AM'),
        ('09:00-10:00', '09:00 AM - 10:00 AM'),
        ('10:00-11:00', '10:00 AM - 11:00 AM'),
        ('11:00-12:00', '11:00 AM - 12:00 PM'),
        ('12:00-13:00', '12:00 PM - 01:00 PM'),
        ('13:00-14:00', '01:00 PM - 02:00 PM'),
        ('14:00-15:00', '02:00 PM - 03:00 PM'),
        ('15:00-16:00', '03:00 PM - 04:00 PM'),
        ('16:00-17:00', '04:00 PM - 05:00 PM'),
        ('17:00-18:00', '05:00 PM - 06:00 PM'),
        ('18:00-19:00', '06:00 PM - 07:00 PM'),
        ('19:00-20:00', '07:00 PM - 08:00 PM'),
        ('20:00-21:00', '08:00 PM - 09:00 PM'),
    ]

    # Get or create availability record
    availability, created = TutorAvailability.objects.get_or_create(
        profile=request.user.profile
    )

    if request.method == 'POST':
        selected_slots = request.POST.getlist('time_slots')
        availability.time_slots = selected_slots
        availability.save()
        messages.success(request, 'Availability updated successfully!')
        return redirect('tutor_dashboard')

    return render(request, 'users/tutor_availability.html', {
        'time_slots': time_slots,
        'selected_slots': availability.time_slots,
        'profile': request.user.profile
    })


# ---------- Student tutor search ----------

def haversine_km(lat1, lon1, lat2, lon2):
    """Calculate distance between two points (in km) using Haversine formula."""
    R = 6371  # Earth radius in km
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    return R * c


def slot_in_preference(time_slots, pref):
    """
    For 1-hour exact slots, just check if the selected slot is in tutor's list.
    """
    if not pref or not time_slots:
        return True
    return pref in (time_slots or [])


@login_required
def browse_tutors(request):
    if request.user.profile.role != 'student':
        return redirect('tutor_dashboard')
    return render(request, 'users/browse_tutors.html', {
        'profile': request.user.profile,
        'GOOGLE_MAPS_API_KEY': settings.GOOGLE_MAPS_API_KEY,
    })


@login_required
def search_tutors(request):
    if request.user.profile.role != 'student':
        return redirect('tutor_dashboard')

    tutors_with_distance, filters = _filter_tutors_with_distance(request)
    tutor_profiles = [t for t, _ in tutors_with_distance]

    if tutor_profiles:
        existing_reqs = BookingRequest.objects.filter(
            student=request.user.profile,
            tutor__in=tutor_profiles
        )
        status_by_tutor = {
            br.tutor_id: br.status for br in existing_reqs
        }
    else:
        status_by_tutor = {}

    for tutor, dist in tutors_with_distance:
        tutor.booking_status = status_by_tutor.get(tutor.id)

    # Attach student's existing review for each tutor (if any)
    student_profile = request.user.profile
    if tutor_profiles:
        reviews_by_tutor = {
            r.tutor_id: r
            for r in TutorReview.objects.filter(
                student=student_profile,
                tutor__in=tutor_profiles
            )
        }

        for tutor, dist in tutors_with_distance:
            tutor.my_review = reviews_by_tutor.get(tutor.id)
    else:
        for tutor, dist in tutors_with_distance:
            tutor.my_review = None

    paginator = Paginator(tutors_with_distance, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'profile': request.user.profile,
        'results': page_obj,
        'page_obj': page_obj,
        'GOOGLE_MAPS_API_KEY': settings.GOOGLE_MAPS_API_KEY,
        **filters,
    }

    return render(request, 'users/tutor_list.html', context)


# ---------- Booking / Contact Tutor ----------

@login_required
def create_booking_request(request, tutor_id):
    """
    Student → Tutor booking request create.
    URL me tutor_id = Profile.id (role='tutor') maana hai.
    """
    student_profile = request.user.profile

    if student_profile.role != 'student':
        messages.error(request, "Only students can send requests.")
        return redirect('tutor_dashboard')

    tutor_profile = get_object_or_404(
        Profile,
        id=tutor_id,
        role='tutor',
        profile_completed=True,
        verification_status='approved'
    )

    if request.method == 'POST':
        grade     = (request.POST.get('grade')     or '').strip()
        subject   = (request.POST.get('subject')   or '').strip()
        time_slot = (request.POST.get('time_slot') or '').strip()
        message   = (request.POST.get('message')   or '').strip()
        mode      = (request.POST.get('mode')      or '').strip()

        # Auto-calculate price from tutor's grade rate
        price = None
        if grade:
            try:
                grade_rate = TutorGradeRate.objects.get(
                    profile=tutor_profile, grade=grade
                )
                # Pick rate based on mode, fallback to first available
                if mode == 'online' and grade_rate.rate_online:
                    price = int(grade_rate.rate_online)
                elif mode == 'student_home' and grade_rate.rate_student_home:
                    price = int(grade_rate.rate_student_home)
                elif mode == 'my_home' and grade_rate.rate_my_home:
                    price = int(grade_rate.rate_my_home)
                else:
                    # fallback: pick first non-null rate
                    price = int(
                        grade_rate.rate_online or
                        grade_rate.rate_student_home or
                        grade_rate.rate_my_home or 0
                    ) or None
            except TutorGradeRate.DoesNotExist:
                price = None

        BookingRequest.objects.filter(
            student=student_profile,
            tutor=tutor_profile,
        ).delete()

        BookingRequest.objects.create(
            student=student_profile,
            tutor=tutor_profile,
            subject=subject,
            message=message,
            time_slot=time_slot,
            grade=grade,
            mode=mode,
            price=price,
            status='pending'
        )

        # Send email notification to tutor
        tutor_email = tutor_profile.user.email
        if tutor_email:
            MODE_LABELS = {
                'online':       'Online',
                'student_home': "At Student's Home",
                'my_home':      "At Tutor's Home",
            }
            GRADE_LABELS = {
                'nursery_to_5': 'Nursery to 5th',
                'grade_6': '6th', 'grade_7': '7th', 'grade_8': '8th',
                'grade_9': '9th', 'grade_10': '10th', 'grade_11': '11th', 'grade_12': '12th',
            }
            requests_url = request.build_absolute_uri(reverse('tutor_booking_requests'))
            email_context = {
                'tutor_name':   tutor_profile.full_name or tutor_profile.user.username,
                'student_name': student_profile.full_name or student_profile.user.username,
                'grade':        GRADE_LABELS.get(grade, grade),
                'subject':      subject,
                'mode':         MODE_LABELS.get(mode, mode),
                'time_slot':    time_slot,
                'price':        price,
                'message':      message,
                'requests_url': requests_url,
            }
            html_message = render_to_string('users/booking_request_email.html', email_context)
            try:
                send_mail(
                    subject='New Booking Request — TutorGali',
                    message=(
                        f"Hi {email_context['tutor_name']},\n\n"
                        f"You have a new booking request from {email_context['student_name']}.\n"
                        f"Grade: {email_context['grade']}\n"
                        f"Subject: {subject}\n"
                        f"Mode: {email_context['mode']}\n"
                        f"Time Slot: {time_slot}\n\n"
                        f"Log in to TutorGali to accept or reject: {requests_url}"
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[tutor_email],
                    html_message=html_message,
                    fail_silently=True,
                )
            except Exception:
                pass  # Never block the booking flow due to email failure

        messages.success(request, "Request sent to tutor.")

        ref_url = request.META.get('HTTP_REFERER')
        if ref_url:
            return redirect(ref_url)

        return redirect('browse_tutors')

    messages.error(request, "Invalid request method.")
    return redirect('browse_tutors')


@login_required
def tutor_booking_requests(request):
    profile = request.user.profile
    if profile.role != 'tutor':
        messages.error(request, "Only tutors can see booking requests.")
        return redirect('student_dashboard')

    incoming_requests = (
        BookingRequest.objects
        .filter(tutor=profile)
        .select_related('student', 'student__user')
        .order_by('-created_at')
    )

    has_active_subscription  = profile.has_active_subscription
    free_contacts_remaining  = profile.free_contacts_remaining
    can_view_contact         = profile.can_view_contact

    return render(request, 'users/tutor_booking_requests.html', {
        'profile':                 profile,
        'incoming_requests':       incoming_requests,
        'has_active_subscription': has_active_subscription,
        'free_contacts_remaining': free_contacts_remaining,
        'can_view_contact':        can_view_contact,
    })


@login_required
def update_booking_request_status(request, pk, action):
    """
    Tutor accepts / rejects a booking request.
    """
    profile = request.user.profile
    if profile.role != 'tutor':
        messages.error(request, "Only tutors can update requests.")
        return redirect('student_dashboard')

    booking = get_object_or_404(BookingRequest, pk=pk, tutor=profile)

    if request.method != 'POST':
        messages.error(request, "Invalid request method.")
        return redirect('tutor_booking_requests')

    if action == 'accept':
        booking.status = 'accepted'
        booking.save()
        # Increment free contact counter if still within free quota
        if profile.free_contacts_used < profile.FREE_CONTACT_LIMIT:
            profile.free_contacts_used += 1
            profile.save(update_fields=['free_contacts_used'])
        messages.success(request, "You accepted this request.")
    elif action == 'reject':
        booking.status = 'rejected'
        booking.save()
        messages.info(request, "You rejected this request.")
    else:
        messages.error(request, "Invalid action.")
        return redirect('tutor_booking_requests')

    # Send email notification to student
    student_email = booking.student.user.email
    if student_email:
        MODE_LABELS = {
            'online':       'Online',
            'student_home': "At Student's Home",
            'my_home':      "At Tutor's Home",
        }
        GRADE_LABELS = {
            'nursery_to_5': 'Nursery to 5th',
            'grade_6': '6th', 'grade_7': '7th', 'grade_8': '8th',
            'grade_9': '9th', 'grade_10': '10th', 'grade_11': '11th', 'grade_12': '12th',
        }
        email_context = {
            'student_name': booking.student.full_name or booking.student.user.username,
            'tutor_name':   profile.full_name or profile.user.username,
            'grade':        GRADE_LABELS.get(booking.grade, booking.grade),
            'subject':      booking.subject,
            'mode':         MODE_LABELS.get(booking.mode, booking.mode),
            'time_slot':    booking.time_slot,
            'price':        booking.price,
            'action':       booking.status,  # 'accepted' or 'rejected'
            'bookings_url': request.build_absolute_uri(reverse('student_bookings')),
            'browse_url':   request.build_absolute_uri(reverse('browse_tutors')),
        }
        html_message = render_to_string('users/booking_status_email.html', email_context)
        subject_line = (
            f"Your booking request was accepted — TutorGali"
            if booking.status == 'accepted'
            else f"Your booking request was rejected — TutorGali"
        )
        plain_message = (
            f"Hi {email_context['student_name']},\n\n"
            f"Your booking request to {email_context['tutor_name']} has been "
            f"{booking.status}.\n\n"
            f"Grade: {email_context['grade']}\n"
            f"Subject: {booking.subject}\n"
            f"Mode: {email_context['mode']}\n"
            f"Time Slot: {booking.time_slot}\n\n"
            + (
                f"View your bookings: {email_context['bookings_url']}"
                if booking.status == 'accepted'
                else f"Find another tutor: {email_context['browse_url']}"
            )
        )
        try:
            send_mail(
                subject=subject_line,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[student_email],
                html_message=html_message,
                fail_silently=True,
            )
        except Exception:
            pass  # Never block the flow due to email failure

    return redirect('tutor_booking_requests')

@login_required
def student_bookings(request):
    profile = request.user.profile

    if profile.role != 'student':
        if profile.role == 'tutor':
            messages.error(request, "Only students can view this page.")
            return redirect('tutor_dashboard')
        # No role set (e.g. admin/superuser) — show empty page gracefully
        return render(request, 'users/student_bookings.html', {
            'profile': profile,
            'bookings': [],
        })

    bookings = (
        BookingRequest.objects
        .filter(student=profile)
        .select_related('tutor', 'tutor__user')
        .order_by('-created_at')
    )

    return render(request, 'users/student_bookings.html', {
        'profile': profile,
        'bookings': bookings,
    })

@login_required
def subscription_plans(request):
    profile = request.user.profile
    if profile.role != 'tutor':
        messages.error(request, "Only tutors can access subscriptions.")
        return redirect('student_dashboard')

    plans = SubscriptionPlan.objects.all().order_by('price_inr')

    # active subscription info
    active_sub = None
    for sub in profile.subscriptions.select_related('plan'):
        if sub.is_active:
            active_sub = sub
            break

    return render(request, 'users/subscription_plans.html', {
        'profile': profile,
        'plans': plans,
        'active_subscription': active_sub,
    })

@login_required
def create_subscription_payment(request, plan_id):
    profile = request.user.profile
    if profile.role != 'tutor':
        messages.error(request, "Only tutors can make subscription payments.")
        return redirect('student_dashboard')

    plan = get_object_or_404(SubscriptionPlan, id=plan_id)

    amount_paise = plan.price_inr * 100  # Razorpay amount must be in paise

    client = get_razorpay_client()
    order_data = {
        "amount": amount_paise,
        "currency": "INR",
        "receipt": f"sub_{profile.id}_{plan.id}",
        "payment_capture": 1,
    }
    order = client.order.create(data=order_data)

    payment = SubscriptionPayment.objects.create(
        tutor=profile,
        plan=plan,
        amount=amount_paise,
        currency="INR",
        razorpay_order_id=order["id"],
        status="created",
    )

    callback_url = request.build_absolute_uri(reverse('subscription_payment_callback'))

    context = {
        "profile": profile,
        "plan": plan,
        "payment": payment,
        "razorpay_key": settings.RAZORPAY_KEY_ID,
        "order_id": order["id"],
        "amount": amount_paise,
        "currency": "INR",
        "callback_url": callback_url,
    }
    return render(request, "payments/subscription_checkout.html", context)

@csrf_exempt
def subscription_payment_callback(request):
    if request.method != "POST":
        messages.error(request, "Invalid payment callback method.")
        return redirect('subscription_plans')

    razorpay_order_id = request.POST.get("razorpay_order_id")
    razorpay_payment_id = request.POST.get("razorpay_payment_id")
    razorpay_signature = request.POST.get("razorpay_signature")

    if not (razorpay_order_id and razorpay_payment_id and razorpay_signature):
        messages.error(request, "Missing payment details.")
        return redirect('subscription_plans')

    client = get_razorpay_client()
    params_dict = {
        "razorpay_order_id": razorpay_order_id,
        "razorpay_payment_id": razorpay_payment_id,
        "razorpay_signature": razorpay_signature,
    }

    try:
        client.utility.verify_payment_signature(params_dict)  # official way
    except razorpay.errors.SignatureVerificationError:
        try:
            payment = SubscriptionPayment.objects.get(razorpay_order_id=razorpay_order_id)
            payment.status = "failed"
            payment.razorpay_payment_id = razorpay_payment_id
            payment.razorpay_signature = razorpay_signature
            payment.save()
        except SubscriptionPayment.DoesNotExist:
            pass

        messages.error(request, "Payment verification failed.")
        return redirect('subscription_plans')

    try:
        payment = SubscriptionPayment.objects.select_related('plan', 'tutor').get(
            razorpay_order_id=razorpay_order_id
        )
    except SubscriptionPayment.DoesNotExist:
        messages.error(request, "Payment record not found.")
        return redirect('subscription_plans')

    payment.razorpay_payment_id = razorpay_payment_id
    payment.razorpay_signature = razorpay_signature
    payment.status = "paid"
    payment.save()

    tutor = payment.tutor
    plan = payment.plan

    today = timezone.now().date()
    months = plan.duration_months
    end_date = today + timedelta(days=30 * months)  # approx month; simple approach

    TutorSubscription.objects.create(
        tutor=tutor,
        plan=plan,
        start_date=today,
        end_date=end_date,
    )

    messages.success(request, "Subscription activated successfully!")
    return redirect('tutor_booking_requests')

@csrf_exempt
def razorpay_webhook(request):
    if request.method != "POST":
        return JsonResponse({"status": "method_not_allowed"}, status=405)

    webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET
    received_signature = request.headers.get("X-Razorpay-Signature", "")

    expected_signature = hmac.new(
        webhook_secret.encode("utf-8"),
        request.body,
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(received_signature, expected_signature):
        return JsonResponse({"status": "invalid_signature"}, status=400)

    try:
        payload = json.loads(request.body)
        event = payload.get("event")

        if event == "payment.captured":
            payment_entity = payload["payload"]["payment"]["entity"]

            razorpay_payment_id = payment_entity["id"]
            razorpay_order_id = payment_entity.get("order_id")

            if razorpay_order_id:
                payment = SubscriptionPayment.objects.filter(
                    razorpay_order_id=razorpay_order_id
                ).first()

                if payment and payment.status != "paid":
                    payment.razorpay_payment_id = razorpay_payment_id
                    payment.status = "paid"
                    payment.save()

        elif event == "payment.failed":
            payment_entity = payload["payload"]["payment"]["entity"]

            razorpay_payment_id = payment_entity["id"]
            razorpay_order_id = payment_entity.get("order_id")

            if razorpay_order_id:
                payment = SubscriptionPayment.objects.filter(
                    razorpay_order_id=razorpay_order_id
                ).first()

                if payment and payment.status != "paid":
                    payment.razorpay_payment_id = razorpay_payment_id
                    payment.status = "failed"
                    payment.save()

        return JsonResponse({"status": "ok"})

    except Exception:
        logger.exception("Razorpay webhook processing failed")
        return JsonResponse({"status": "error"}, status=500)

# ─────────────────────────────────────────────
# Tutor: My Reviews page
# ─────────────────────────────────────────────

@login_required
def my_reviews(request):
    """Tutor sees all their own reviews with full details."""
    profile = request.user.profile
    if profile.role != 'tutor':
        messages.error(request, "Only tutors can view this page.")
        return redirect('student_dashboard')

    reviews = TutorReview.objects.filter(
        tutor=profile
    ).select_related('student').order_by('-created_at')

    # Rating breakdown (count per star)
    from django.db.models import Count
    breakdown = {i: 0 for i in range(1, 6)}
    for row in reviews.values('rating').annotate(count=Count('rating')):
        breakdown[row['rating']] = row['count']

    return render(request, 'users/my_reviews.html', {
        'profile':    profile,
        'reviews':    reviews,
        'breakdown':  breakdown,
    })


# ─────────────────────────────────────────────
# Tutor Public Profile + Reviews
# ─────────────────────────────────────────────

def tutor_public_profile(request, tutor_id):
    """Public profile page for a tutor — visible to everyone."""
    tutor_profile = get_object_or_404(
        Profile, id=tutor_id, role='tutor',
        profile_completed=True, verification_status='approved'
    )

    grade_rates = TutorGradeRate.objects.filter(profile=tutor_profile).order_by('grade')
    reviews     = TutorReview.objects.filter(tutor=tutor_profile).select_related('student')

    # Availability
    try:
        availability = tutor_profile.availability
    except TutorAvailability.DoesNotExist:
        availability = None

    # Slot label map
    SLOT_LABELS = {
        '04:00-05:00': '04:00 AM – 05:00 AM', '05:00-06:00': '05:00 AM – 06:00 AM',
        '06:00-07:00': '06:00 AM – 07:00 AM', '07:00-08:00': '07:00 AM – 08:00 AM',
        '08:00-09:00': '08:00 AM – 09:00 AM', '09:00-10:00': '09:00 AM – 10:00 AM',
        '10:00-11:00': '10:00 AM – 11:00 AM', '11:00-12:00': '11:00 AM – 12:00 PM',
        '12:00-13:00': '12:00 PM – 01:00 PM', '13:00-14:00': '01:00 PM – 02:00 PM',
        '14:00-15:00': '02:00 PM – 03:00 PM', '15:00-16:00': '03:00 PM – 04:00 PM',
        '16:00-17:00': '04:00 PM – 05:00 PM', '17:00-18:00': '05:00 PM – 06:00 PM',
        '18:00-19:00': '06:00 PM – 07:00 PM', '19:00-20:00': '07:00 PM – 08:00 PM',
        '20:00-21:00': '08:00 PM – 09:00 PM',
    }
    slot_labels = []
    if availability and availability.time_slots:
        slot_labels = [SLOT_LABELS.get(s, s) for s in availability.time_slots]

    # Review eligibility + booking status for logged-in student
    can_review     = False
    my_review      = None
    review_form    = None
    booking_status = None   # None / 'pending' / 'accepted' / 'rejected'

    if request.user.is_authenticated:
        student_profile = getattr(request.user, 'profile', None)
        if student_profile and student_profile.role == 'student':
            existing_booking = BookingRequest.objects.filter(
                student=student_profile, tutor=tutor_profile
            ).first()
            booking_status = existing_booking.status if existing_booking else None

            my_review  = TutorReview.objects.filter(
                tutor=tutor_profile, student=student_profile
            ).first()
            can_review = (booking_status == 'accepted')
            if can_review:
                review_form = TutorReviewForm(instance=my_review)

    # Pre-split comma-separated fields for clean template rendering
    MODE_LABELS = {
        'online':       'Online',
        'student_home': "At Student's Home",
        'my_home':      "At Tutor's Home",
    }
    teaching_modes  = [MODE_LABELS.get(m.strip(), m.strip())
                       for m in (tutor_profile.teaching_mode or '').split(',') if m.strip()]
    languages_list  = [l.strip().title()
                       for l in (tutor_profile.languages or '').split(',') if l.strip()]
    boards_list     = [b.strip().upper()
                       for b in (tutor_profile.school_boards or '').split(',') if b.strip()]

    # Carry over search filters from the URL (passed by tutor_list.html links)
    search_grade     = request.GET.get('grade', '')
    search_subject   = request.GET.get('subject', '')
    search_time_slot = request.GET.get('time_slot', '')
    search_mode      = request.GET.get('mode', '')

    return render(request, 'users/tutor_public_profile.html', {
        'tutor':            tutor_profile,
        'grade_rates':      grade_rates,
        'availability':     availability,
        'slot_labels':      slot_labels,
        'reviews':          reviews,
        'can_review':       can_review,
        'my_review':        my_review,
        'review_form':      review_form,
        'booking_status':   booking_status,
        'teaching_modes':   teaching_modes,
        'languages_list':   languages_list,
        'boards_list':      boards_list,
        'search_grade':     search_grade,
        'search_subject':   search_subject,
        'search_time_slot': search_time_slot,
        'search_mode':      search_mode,
    })


@login_required
def submit_review(request, tutor_id):
    """Student submits or updates a review for a tutor."""
    student_profile = request.user.profile

    if student_profile.role != 'student':
        messages.error(request, "Only students can submit reviews.")
        return redirect('tutor_dashboard')

    tutor_profile = get_object_or_404(Profile, id=tutor_id, role='tutor')

    # Must have an accepted booking
    if not BookingRequest.objects.filter(
        student=student_profile, tutor=tutor_profile, status='accepted'
    ).exists():
        messages.error(request, "You can only review tutors who have accepted your booking request.")
        return redirect('tutor_public_profile', tutor_id=tutor_id)

    if request.method == 'POST':
        form = TutorReviewForm(request.POST)
        if form.is_valid():
            TutorReview.objects.update_or_create(
                tutor=tutor_profile,
                student=student_profile,
                defaults={
                    'rating':  form.cleaned_data['rating'],
                    'comment': form.cleaned_data['comment'],
                }
            )
            messages.success(request, "Your review has been saved! Thank you.")
        else:
            messages.error(request, "Please select a star rating.")

    return redirect('tutor_public_profile', tutor_id=tutor_id)


@login_required
def delete_review(request, tutor_id):
    """Student deletes their review for a tutor."""
    student_profile = request.user.profile
    tutor_profile   = get_object_or_404(Profile, id=tutor_id, role='tutor')

    if request.method == 'POST':
        deleted, _ = TutorReview.objects.filter(
            tutor=tutor_profile, student=student_profile
        ).delete()
        if deleted:
            messages.success(request, "Your review has been deleted.")
        else:
            messages.error(request, "No review found to delete.")

    return redirect('tutor_public_profile', tutor_id=tutor_id)


# ═══════════════════════════════════════════════════════════
#  LEGAL / COMPLIANCE PAGES  —  required for Razorpay activation
# ═══════════════════════════════════════════════════════════

LEGAL_PAGE_UPDATED = "12 August 2026"
SUPPORT_EMAIL = "tutorgalisupport@gmail.com"

def _legal_page(request, template_name, page_title):
    """Render a static legal/compliance page (Privacy Policy, Terms, etc.)."""
    return render(request, template_name, {
        'page_title': page_title,
        'last_updated': LEGAL_PAGE_UPDATED,
        'support_email': SUPPORT_EMAIL,
    })

def privacy_policy(request):
    return _legal_page(request, 'users/privacy_policy.html', 'Privacy Policy')

def terms_conditions(request):
    return _legal_page(request, 'users/terms_conditions.html', 'Terms & Conditions')

def refund_policy(request):
    return _legal_page(request, 'users/refund_policy.html', 'Refund & Cancellation Policy')

def contact_us(request):
    return _legal_page(request, 'users/contact_us.html', 'Contact Us')


# ═══════════════════════════════════════════════════════════
#  CUSTOM ADMIN PANEL  —  /admin-panel/
# ═══════════════════════════════════════════════════════════

def admin_required(view_func):
    """Decorator: only staff (is_staff=True) users can access admin panel."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('admin_panel_login')
        if not request.user.is_staff:
            messages.error(request, "You don't have permission to access the admin panel.")
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper


def admin_panel_login(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('admin_panel_dashboard')
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        user = authenticate(request, username=username, password=password)
        if user and user.is_staff:
            auth_login(request, user)
            return redirect('admin_panel_dashboard')
        else:
            messages.error(request, 'Invalid credentials or you are not an admin.')
    return render(request, 'admin_panel/login.html')


def admin_panel_logout(request):
    auth_logout(request)
    return redirect('admin_panel_login')


@admin_required
def admin_panel_dashboard(request):
    total_tutors      = Profile.objects.filter(role='tutor').count()
    total_students    = Profile.objects.filter(role='student').count()
    pending_tutors    = Profile.objects.filter(role='tutor', verification_status='pending').count()
    approved_tutors   = Profile.objects.filter(role='tutor', verification_status='approved').count()
    total_bookings    = BookingRequest.objects.count()
    accepted_bookings = BookingRequest.objects.filter(status='accepted').count()
    total_reviews     = TutorReview.objects.count()
    total_revenue     = SubscriptionPayment.objects.filter(status='paid').aggregate(total=Sum('amount'))['total'] or 0
    total_revenue_inr = total_revenue // 100

    recent_tutors         = Profile.objects.filter(role='tutor').select_related('user').order_by('-id')[:5]
    recent_bookings       = BookingRequest.objects.select_related('student', 'tutor').order_by('-created_at')[:5]
    recent_reviews        = TutorReview.objects.select_related('student', 'tutor').order_by('-created_at')[:5]
    pending_verifications = Profile.objects.filter(
        role='tutor', verification_status='pending',
        education_certificate__isnull=False
    ).exclude(education_certificate='').select_related('user')[:5]

    return render(request, 'admin_panel/dashboard.html', {
        'total_tutors':          total_tutors,
        'total_students':        total_students,
        'pending_tutors':        pending_tutors,
        'approved_tutors':       approved_tutors,
        'total_bookings':        total_bookings,
        'accepted_bookings':     accepted_bookings,
        'total_reviews':         total_reviews,
        'total_revenue_inr':     total_revenue_inr,
        'recent_tutors':         recent_tutors,
        'recent_bookings':       recent_bookings,
        'recent_reviews':        recent_reviews,
        'pending_verifications': pending_verifications,
    })


@admin_required
def admin_panel_tutors(request):
    status_filter = request.GET.get('status', '')
    search        = request.GET.get('q', '').strip()
    tutors = Profile.objects.filter(role='tutor').select_related('user').order_by('-id')
    if status_filter:
        tutors = tutors.filter(verification_status=status_filter)
    if search:
        tutors = tutors.filter(
            Q(full_name__icontains=search) | Q(user__email__icontains=search) |
            Q(mobile_number__icontains=search) | Q(city__icontains=search)
        )
    paginator = Paginator(tutors, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'admin_panel/tutors.html', {
        'tutors': page_obj, 'page_obj': page_obj,
        'status_filter': status_filter,
        'search': search, 'total': paginator.count,
    })


@admin_required
def admin_panel_tutor_detail(request, tutor_id):
    tutor       = get_object_or_404(Profile, id=tutor_id, role='tutor')
    grade_rates = TutorGradeRate.objects.filter(profile=tutor)
    reviews     = TutorReview.objects.filter(tutor=tutor).select_related('student')

    if request.method == 'POST':
        action = request.POST.get('action')
        notes  = request.POST.get('notes', '').strip()
        if action == 'approve':
            tutor.verification_status = 'approved'
            tutor.verification_notes  = ''
            tutor.save(update_fields=['verification_status', 'verification_notes'])
            messages.success(request, f'{tutor.full_name} approved as verified tutor.')
        elif action == 'reject':
            tutor.verification_status = 'rejected'
            tutor.verification_notes  = notes
            tutor.save(update_fields=['verification_status', 'verification_notes'])
            messages.warning(request, f'{tutor.full_name} verification rejected.')
        elif action == 'pending':
            tutor.verification_status = 'pending'
            tutor.save(update_fields=['verification_status'])
            messages.info(request, f'{tutor.full_name} set back to pending.')
        return redirect('admin_panel_tutor_detail', tutor_id=tutor_id)

    return render(request, 'admin_panel/tutor_detail.html', {
        'tutor': tutor, 'grade_rates': grade_rates, 'reviews': reviews,
    })


@admin_required
def admin_panel_students(request):
    search   = request.GET.get('q', '').strip()
    students = Profile.objects.filter(role='student').select_related('user').order_by('-id')
    if search:
        students = students.filter(
            Q(full_name__icontains=search) | Q(user__email__icontains=search) |
            Q(mobile_number__icontains=search)
        )
    paginator = Paginator(students, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'admin_panel/students.html', {
        'students': page_obj, 'page_obj': page_obj,
        'search': search, 'total': paginator.count,
    })


@admin_required
def admin_panel_bookings(request):
    status_filter = request.GET.get('status', '')
    search        = request.GET.get('q', '').strip()
    bookings = BookingRequest.objects.select_related('student', 'tutor').order_by('-created_at')
    if status_filter:
        bookings = bookings.filter(status=status_filter)
    if search:
        bookings = bookings.filter(
            Q(student__full_name__icontains=search) | Q(tutor__full_name__icontains=search) |
            Q(subject__icontains=search)
        )
    paginator = Paginator(bookings, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'admin_panel/bookings.html', {
        'bookings': page_obj, 'page_obj': page_obj,
        'status_filter': status_filter,
        'search': search, 'total': paginator.count,
    })


@admin_required
def admin_panel_reviews(request):
    search  = request.GET.get('q', '').strip()
    rating  = request.GET.get('rating', '')
    reviews = TutorReview.objects.select_related('tutor', 'student').order_by('-created_at')
    if rating:
        reviews = reviews.filter(rating=rating)
    if search:
        reviews = reviews.filter(
            Q(tutor__full_name__icontains=search) | Q(student__full_name__icontains=search) |
            Q(comment__icontains=search)
        )
    avg = reviews.aggregate(avg=Avg('rating'))['avg']
    paginator = Paginator(reviews, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'admin_panel/reviews.html', {
        'reviews': page_obj, 'page_obj': page_obj,
        'search': search, 'rating': rating,
        'total': paginator.count, 'avg': round(avg, 1) if avg else None,
    })


@admin_required
def admin_panel_delete_review(request, review_id):
    review = get_object_or_404(TutorReview, id=review_id)
    if request.method == 'POST':
        review.delete()
        messages.success(request, 'Review deleted.')
    return redirect('admin_panel_reviews')


@admin_required
def admin_panel_subscriptions(request):
    payments = SubscriptionPayment.objects.select_related('tutor', 'plan').order_by('-created_at')
    total_revenue     = payments.filter(status='paid').aggregate(total=Sum('amount'))['total'] or 0
    total_revenue_inr = total_revenue // 100
    paid_count   = payments.filter(status='paid').count()
    failed_count = payments.filter(status='failed').count()
    active_subs = TutorSubscription.objects.select_related('tutor', 'plan').filter(
        end_date__gte=timezone.now().date()).order_by('-start_date')

    payments_paginator = Paginator(payments, 20)
    payments_page_obj  = payments_paginator.get_page(request.GET.get('payments_page'))

    subs_paginator = Paginator(active_subs, 20)
    subs_page_obj  = subs_paginator.get_page(request.GET.get('subs_page'))

    return render(request, 'admin_panel/subscriptions.html', {
        'payments': payments_page_obj, 'payments_page_obj': payments_page_obj,
        'total_revenue_inr': total_revenue_inr,
        'active_subs': subs_page_obj, 'subs_page_obj': subs_page_obj,
        'paid_count': paid_count, 'failed_count': failed_count,
    })


@admin_required
def admin_panel_register_admin(request):
    if not request.user.is_superuser:
        messages.error(request, 'Only superusers can create new admin accounts.')
        return redirect('admin_panel_dashboard')
    if request.method == 'POST':
        username  = request.POST.get('username', '').strip()
        email     = request.POST.get('email', '').strip()
        password1 = request.POST.get('password1', '').strip()
        password2 = request.POST.get('password2', '').strip()
        errors = []
        if not username:
            errors.append('Username is required.')
        elif User.objects.filter(username=username).exists():
            errors.append('Username already taken.')
        if not email:
            errors.append('Email is required.')
        elif User.objects.filter(email=email).exists():
            errors.append('Email already registered.')
        if len(password1) < 8:
            errors.append('Password must be at least 8 characters.')
        if password1 != password2:
            errors.append('Passwords do not match.')
        if errors:
            for e in errors:
                messages.error(request, e)
        else:
            User.objects.create_user(
                username=username, email=email, password=password1,
                is_staff=True, is_active=True
            )
            messages.success(request, f'Admin account "{username}" created successfully.')
            return redirect('admin_panel_dashboard')
    return render(request, 'admin_panel/register_admin.html')