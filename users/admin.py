from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from .models import Profile, TutorGradeRate, TutorAvailability, \
BookingRequest, SubscriptionPlan, TutorSubscription, SubscriptionPayment, TutorReview, \
RazorpayWebhookEvent


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'


class CustomUserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_role')
    list_select_related = ('profile',)

    def get_role(self, instance):
        return instance.profile.role

    get_role.short_description = 'Role'

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return list()
        return super(CustomUserAdmin, self).get_inline_instances(request, obj)


class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'full_name', 'role', 'mobile_number',
        'city', 'state', 'latitude', 'longitude',
        'verification_status', 'profile_completed'
    )
    list_filter = ('role', 'verification_status', 'profile_completed', 'gender', 'tutor_type')
    search_fields = (
        'user__username', 'user__email', 'full_name',
        'mobile_number', 'city', 'state', 'pincode',
        'locality', 'qualification', 'education_institute'
    )
    readonly_fields = ('user',)

    fieldsets = (
        ('User Info', {
            'fields': (
                'user',
                'role',
                'full_name',
                'mobile_number',
                'gender',
            ),
        }),
        ('Address Info', {
            'fields': (
                'address_line1',
                'address_line2',
                'city',
                'state',
                'pincode',
                'locality',
                'location',
                'latitude',
                'longitude',
            ),
        }),
        ('Profile Status', {
            'fields': (
                'profile_completed',
            ),
        }),
        ('Tutor Details', {
            'fields': (
                'tutor_type',
                'qualification',
                'qualification_other',
                'education_institute',
                'teaching_mode',
                'bio',
                'languages',
                'school_boards',
                'experience_years',
            ),
        }),
        ('Verification', {
            'fields': (
                'verification_status',
                'education_certificate',
                'id_proof',
                'verification_notes',
            ),
        }),
    )

    actions = ['approve_verification', 'reject_verification']

    def approve_verification(self, request, queryset):
        updated = queryset.filter(role='tutor').update(
            verification_status='approved',
        )
        self.message_user(request, f'{updated} tutor(s) verified successfully.')

    approve_verification.short_description = "✓ Approve selected tutors"

    def reject_verification(self, request, queryset):
        updated = queryset.filter(role='tutor').update(
            verification_status='rejected'
        )
        self.message_user(
            request,
            f'{updated} tutor(s) rejected. Please add rejection reason in edit page.'
        )

    reject_verification.short_description = "✗ Reject selected tutors"

class TutorGradeRateAdmin(admin.ModelAdmin):
    list_display = (
        'profile', 'grade', 'subjects_preview',
        'rate_online', 'rate_student_home', 'rate_my_home'
    )
    list_filter = ('grade', 'profile__user__username')
    search_fields = ('profile__user__username', 'profile__full_name', 'subjects')

    def subjects_preview(self, obj):
        return obj.subjects[:50] + '...' if len(obj.subjects) > 50 else obj.subjects

    subjects_preview.short_description = 'Subjects'


# Simple admin for availability (optional but useful)
@admin.register(TutorAvailability)
class TutorAvailabilityAdmin(admin.ModelAdmin):
    list_display = ('profile', 'is_active', 'created_at', 'updated_at')
    search_fields = ('profile__user__username', 'profile__full_name')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(BookingRequest)
class BookingRequestAdmin(admin.ModelAdmin):
    list_display = ('student', 'tutor', 'subject', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = (
        'student__user__username',
        'student__full_name',
        'tutor__user__username',
        'tutor__full_name',
        'subject',
    )
    ordering = ('-created_at',)


# Unregister default User admin
admin.site.unregister(User)

# Register custom User admin
admin.site.register(User, CustomUserAdmin)

# Register other models
admin.site.register(Profile, ProfileAdmin)
admin.site.register(TutorGradeRate, TutorGradeRateAdmin)

admin.site.register(SubscriptionPlan)
admin.site.register(TutorSubscription)
admin.site.register(SubscriptionPayment)


@admin.register(TutorReview)
class TutorReviewAdmin(admin.ModelAdmin):
    list_display  = ('tutor', 'student', 'rating', 'comment_preview', 'created_at')
    list_filter   = ('rating',)
    search_fields = ('tutor__full_name', 'student__full_name', 'comment')
    ordering      = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')

    def comment_preview(self, obj):
        if not obj.comment:
            return '—'
        return obj.comment[:60] + ('…' if len(obj.comment) > 60 else '')
    comment_preview.short_description = 'Comment'


@admin.register(RazorpayWebhookEvent)
class RazorpayWebhookEventAdmin(admin.ModelAdmin):
    list_display = ('event_type', 'event_id', 'processed', 'processing_note', 'created_at')
    list_filter = ('event_type', 'processed')
    search_fields = ('event_id', 'event_type', 'processing_note')
    ordering = ('-created_at',)
    readonly_fields = ('event_id', 'event_type', 'payload', 'processed', 'processing_note', 'created_at')

    def has_add_permission(self, request):
        # Records are only ever created by the webhook view, never by staff.
        return False
