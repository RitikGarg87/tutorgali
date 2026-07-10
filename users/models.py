from django.contrib.auth.models import User
from django.db import models
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderServiceError
import logging
import requests
from django.utils import timezone
from datetime import timedelta
logger = logging.getLogger(__name__)

class Profile(models.Model):
    @property
    def has_active_subscription(self):
        today = timezone.now().date()
        return self.subscriptions.filter(end_date__gte=today).exists()
    
    USER_ROLES = (
        ('student', 'Student'),
        ('tutor', 'Tutor'),
    )
    
    TUTOR_TYPE = (
        ('individual', 'Individual'),
        ('institute', 'Institute'),
    )
    
    GENDER_CHOICES = (
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    )
    
    VERIFICATION_STATUS = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=USER_ROLES)
    
    # Common fields
    full_name = models.CharField(max_length=200, blank=True, null=True)
    mobile_number = models.CharField(max_length=15, blank=True, null=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True, null=True)
    
    # Address fields
    address_line1 = models.CharField(max_length=300, blank=True, null=True)
    address_line2 = models.CharField(max_length=300, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    pincode = models.CharField(max_length=10, blank=True, null=True)
    locality = models.CharField(max_length=200, blank=True, null=True)
    
    # Profile completion
    profile_completed = models.BooleanField(default=False)
    
    # Tutor fields
    tutor_type = models.CharField(max_length=15, choices=TUTOR_TYPE, default='individual', blank=True, null=True)
    qualification = models.CharField(max_length=100, blank=True, null=True)
    qualification_other = models.CharField(max_length=200, blank=True, null=True)
    education_institute = models.CharField(max_length=300, blank=True, null=True)
    
    # Onboarding fields
    teaching_mode = models.CharField(max_length=200, blank=True, null=True)  # Comma-separated
    bio = models.TextField(blank=True, null=True)
    languages = models.CharField(max_length=200, blank=True, null=True)
    school_boards = models.CharField(max_length=200, blank=True, null=True)
    experience_years = models.IntegerField(blank=True, null=True)
    
    # Verification fields
    verification_status = models.CharField(max_length=10, choices=VERIFICATION_STATUS, default='pending')
    education_certificate = models.FileField(upload_to='certificates/', blank=True, null=True)
    id_proof = models.FileField(upload_to='id_proofs/', blank=True, null=True)
    verification_notes = models.TextField(blank=True, null=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    
    # Student-specific
    location = models.CharField(max_length=100, blank=True, null=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.role}"
    
    @property
    def is_verified(self):
        return self.verification_status == 'approved'
    
    @property
    def full_address(self):
        """Returns formatted full address"""
        parts = []
        if self.address_line1:
            parts.append(self.address_line1)
        if self.address_line2:
            parts.append(self.address_line2)
        if self.city:
            parts.append(self.city)
        if self.state:
            parts.append(self.state)
        if self.pincode:
            parts.append(self.pincode)
        return ', '.join(parts) if parts else 'Address not provided'


class TutorGradeRate(models.Model):
    """Stores tutor's teaching grades, subjects, and rates for different teaching modes"""
    
    GRADE_CHOICES = (
        ('nursery_to_5', 'Nursery to 5th'),
        ('grade_6', '6th'),
        ('grade_7', '7th'),
        ('grade_8', '8th'),
        ('grade_9', '9th'),
        ('grade_10', '10th'),
        ('grade_11', '11th'),
        ('grade_12', '12th'),
    )
    
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='grade_rates')
    grade = models.CharField(max_length=20, choices=GRADE_CHOICES)
    subjects = models.TextField()  # Comma-separated subjects
    
    # Rates for different teaching modes
    rate_online = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    rate_student_home = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    rate_my_home = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('profile', 'grade')
        ordering = ['grade']
    
    def __str__(self):
        return f"{self.profile.user.username} - {self.get_grade_display()}"
    

class TutorAvailability(models.Model):
    """Stores tutor's availability in a single row - Monday to Saturday only"""
    
    profile = models.OneToOneField(Profile, on_delete=models.CASCADE, related_name='availability')
    
    # Common time slots for Monday to Saturday
    # Structure: ["04:00-05:00", "05:00-06:00", "06:00-07:00", ...]
    time_slots = models.JSONField(default=list, blank=True, help_text="Time slots for Mon-Sat")
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Tutor Availability'
        verbose_name_plural = 'Tutor Availabilities'
    
    def __str__(self):
        return f"{self.profile.user.username} - Availability"
    
    def get_total_hours(self):
        """Calculate total hours per week (6 days)"""
        return len(self.time_slots) * 6  # Mon-Sat only


class BookingRequest(models.Model):
    student = models.ForeignKey('Profile', on_delete=models.CASCADE, related_name='student_requests')
    tutor = models.ForeignKey('Profile', on_delete=models.CASCADE, related_name='tutor_requests')

    grade = models.CharField(max_length=50, blank=True, null=True)
    subject = models.CharField(max_length=100, blank=True, null=True)
    time_slot = models.CharField(max_length=50, blank=True, null=True)

    message = models.TextField(blank=True, null=True)

    price = models.PositiveIntegerField(blank=True, null=True, help_text="Price in INR per hour")

    status = models.CharField(
        max_length=20,
        default='pending',
        choices=(
            ('pending', 'Pending'),
            ('accepted', 'Accepted'),
            ('rejected', 'Rejected'),
        )
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'tutor')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student} → {self.tutor} ({self.status})"
    

class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=50)
    duration_months = models.PositiveIntegerField()
    price_inr = models.PositiveIntegerField(help_text="Price in INR")

    def __str__(self):
        return f"{self.name} - {self.duration_months} months ({self.price_inr} INR)"


class TutorSubscription(models.Model):
    tutor = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name='subscriptions'
    )
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_active(self):
        today = timezone.now().date()
        return self.start_date <= today <= self.end_date

    def __str__(self):
        return f"{self.tutor.user.username} - {self.plan.name} ({self.start_date} to {self.end_date})"


class SubscriptionPayment(models.Model):
    STATUS_CHOICES = (
        ('created', 'Created'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
    )

    tutor = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name='subscription_payments'
    )
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE)

    # Razorpay info
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=255, blank=True, null=True)

    amount = models.PositiveIntegerField(help_text="Amount in paise")
    currency = models.CharField(max_length=10, default='INR')

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='created'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Sub payment {self.tutor.user.username} - {self.plan.name} ({self.status})"