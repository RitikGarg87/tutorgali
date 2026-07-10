from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import views as auth_views
from django.contrib import messages
from django.forms import modelformset_factory
from django.urls import reverse_lazy, reverse
from math import radians, sin, cos, asin, sqrt
from urllib.parse import urlencode
from .forms import (
    SignUpForm, ProfileForm, VerificationForm,
    EmailOrMobileLoginForm, TutorOnboardingForm, TutorGradeRateForm
)
from .models import TutorGradeRate, TutorAvailability, Profile, BookingRequest, SubscriptionPlan, TutorSubscription, SubscriptionPayment
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import timedelta
import razorpay

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


def register(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
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

        print("POST Data:", request.POST)  # Debug
        print("Profile Form Valid:", profile_form.is_valid())  # Debug
        print("Profile Form Errors:", profile_form.errors)  # Debug
        print("Formset Valid:", formset.is_valid())  # Debug
        print("Formset Errors:", formset.errors)  # Debug

        if profile_form.is_valid() and formset.is_valid():
            # Save profile
            profile = profile_form.save(commit=False)
            lat = request.POST.get('latitude')
            lng = request.POST.get('longitude')

            profile.latitude = float(lat) if lat else None
            profile.longitude = float(lng) if lng else None

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

            print("Profile saved successfully!")  # Debug

            # Delete existing grade rates for this tutor
            TutorGradeRate.objects.filter(profile=request.user.profile).delete()

            # Save grade rates
            grade_choices = [
                'nursery_to_5', 'grade_6', 'grade_7', 'grade_8',
                'grade_9', 'grade_10', 'grade_11', 'grade_12'
            ]
            saved_count = 0

            for i, form in enumerate(formset):
                if form.cleaned_data and form.cleaned_data.get('subjects'):
                    grade_rate = form.save(commit=False)
                    grade_rate.profile = request.user.profile
                    grade_rate.grade = grade_choices[i]
                    grade_rate.save()
                    saved_count += 1
                    print(f"Saved grade rate {i+1}: {grade_choices[i]}")  # Debug

            print(f"Total grade rates saved: {saved_count}")  # Debug

            messages.success(request, 'Profile completed successfully! Welcome to TutorGali!')
            return redirect('tutor_dashboard')
        else:
            # Show errors
            messages.error(request, 'Please correct the errors below.')
            print("Form validation failed!")  # Debug
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
    return render(request, 'users/student_dashboard.html', {'profile': request.user.profile})


@login_required
def tutor_dashboard(request):
    grade_rates = TutorGradeRate.objects.filter(profile=request.user.profile)

    # Get availability (single row, Mon-Sat only)
    try:
        availability = request.user.profile.availability
        total_hours = availability.get_total_hours()  # slots * 6 days
    except TutorAvailability.DoesNotExist:
        total_hours = 0
        availability = None

    return render(request, 'users/tutor_dashboard.html', {
        'profile': request.user.profile,
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

        # Prepare grade labels
        grade_labels = [
            'Nursery to 5th', '6th', '7th', '8th',
            '9th', '10th', '11th', '12th'
        ]

        # Get existing grades for JavaScript
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
        'is_edit': True,
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
        'profile': request.user.profile
    })


@login_required
def search_tutors(request):
    if request.user.profile.role != 'student':
        return redirect('tutor_dashboard')

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

    if grade:
        tutors = tutors.filter(grade_rates__grade=grade)

    if subject:
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
        # distance
        if tutor.latitude is not None and tutor.longitude is not None and user_lat is not None:
            dist = haversine_km(user_lat, user_lng, tutor.latitude, tutor.longitude)
        else:
            dist = None

        # availability filter (exact 1-hour slot)
        availability = getattr(tutor, 'availability', None)
        if not slot_in_preference(getattr(availability, 'time_slots', []), time_slot_pref):
            continue

        if dist is None or dist <= distance_km:
            tutors_with_distance.append((tutor, dist))

    # yahan LOOP ke baad list banao (pehle andar thi)
    tutor_profiles = [t for (t, _) in tutors_with_distance]

    # agar koi tutor nahi mila, to aage ka code safely handle karo
    if tutor_profiles:
        existing_reqs = BookingRequest.objects.filter(
            student=request.user.profile,
            tutor__in=tutor_profiles
        )
        status_by_tutor = {br.tutor_id: br.status for br in existing_reqs}
    else:
        status_by_tutor = {}

    # har tutor object me booking_status attribute laga do
    for tutor, dist in tutors_with_distance:
        tutor.booking_status = status_by_tutor.get(tutor.id)

    tutors_with_distance.sort(key=lambda x: float('inf') if x[1] is None else x[1])

    context = {
        'profile': request.user.profile,
        'results': tutors_with_distance,
        'grade': grade,
        'subject': subject,
        'mode': mode,
        'distance_km': int(distance_km),
        'time_slot': time_slot_pref,
        'user_lat': user_lat,
        'user_lng': user_lng,
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
        grade = (request.POST.get('grade') or '').strip()
        subject = (request.POST.get('subject') or '').strip()
        time_slot = (request.POST.get('time_slot') or '').strip()
        message = (request.POST.get('message') or '').strip()

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
            status='pending'
        )

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

    has_active_subscription = profile.has_active_subscription

    return render(request, 'users/tutor_booking_requests.html', {
        'profile': profile,
        'incoming_requests': incoming_requests,
        'has_active_subscription': has_active_subscription,
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
        messages.success(request, "You accepted this request.")
    elif action == 'reject':
        booking.status = 'rejected'
        booking.save()
        messages.info(request, "You rejected this request.")
    else:
        messages.error(request, "Invalid action.")

    return redirect('tutor_booking_requests')

@login_required
def student_bookings(request):
    profile = request.user.profile

    if profile.role != 'student':
        messages.error(request, "Only students can view this page.")
        return redirect('tutor_dashboard')

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