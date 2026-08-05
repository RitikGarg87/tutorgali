from django.contrib.auth import views as auth_views
from . import views
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, reverse_lazy

urlpatterns = [
    path('register/', views.register, name='register'),
    path('send-otp/', views.send_otp, name='send_otp'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),    
    # Password Reset URLs - USING reverse_lazy
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(
             template_name='users/password_reset.html',
             email_template_name='users/password_reset_email.html',
             subject_template_name='users/password_reset_subject.txt',
             success_url=reverse_lazy('password_reset_done')
         ), 
         name='password_reset'),
    
    path('password-reset-done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name='users/password_reset_done.html'
         ), 
         name='password_reset_done'),
    
    path('password-reset-confirm/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(
             template_name='users/password_reset_confirm.html',
             success_url=reverse_lazy('password_reset_complete')
         ), 
         name='password_reset_confirm'),
    
    path('password-reset-complete/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='users/password_reset_complete.html'
         ), 
         name='password_reset_complete'),
    
    # Other URLs
    path('tutor-onboarding/', views.tutor_onboarding, name='tutor_onboarding'),
    path('profile/', views.profile, name='profile'),
    path('verification/', views.verification, name='verification'),
    path('student-dashboard/', views.student_dashboard, name='student_dashboard'),
    path('tutor-dashboard/', views.tutor_dashboard, name='tutor_dashboard'),
    path('tutor-edit-profile/', views.tutor_edit_profile, name='tutor_edit_profile'),
    path('tutor-availability/', views.tutor_availability, name='tutor_availability'),
    path('browse-tutors/', views.browse_tutors, name='browse_tutors'),
    path('search-tutors/', views.search_tutors, name='search_tutors'),
        # 🔹 Booking / Contact URLs (NEW)
    path(
        'tutors/<int:tutor_id>/request/',
        views.create_booking_request,
        name='create_booking_request'
    ),
    path(
        'tutor/requests/',
        views.tutor_booking_requests,
        name='tutor_booking_requests'
    ),
    path(
        'tutor/requests/<int:pk>/<str:action>/',
        views.update_booking_request_status,
        name='update_booking_request_status'
    ),
    path('student/bookings/', views.student_bookings, name='student_bookings'),
    path('my-reviews/', views.my_reviews, name='my_reviews'),
    # Tutor public profile + reviews
    path('tutors/<int:tutor_id>/',               views.tutor_public_profile, name='tutor_public_profile'),
    path('tutors/<int:tutor_id>/review/',        views.submit_review,        name='submit_review'),
    path('tutors/<int:tutor_id>/review/delete/', views.delete_review,        name='delete_review'),
    # ── Custom Admin Panel ──────────────────────────────────
    path('admin-panel/login/',            views.admin_panel_login,            name='admin_panel_login'),
    path('admin-panel/logout/',           views.admin_panel_logout,           name='admin_panel_logout'),
    path('admin-panel/',                  views.admin_panel_dashboard,        name='admin_panel_dashboard'),
    path('admin-panel/tutors/',           views.admin_panel_tutors,           name='admin_panel_tutors'),
    path('admin-panel/tutors/<int:tutor_id>/', views.admin_panel_tutor_detail, name='admin_panel_tutor_detail'),
    path('admin-panel/students/',         views.admin_panel_students,         name='admin_panel_students'),
    path('admin-panel/bookings/',         views.admin_panel_bookings,         name='admin_panel_bookings'),
    path('admin-panel/reviews/',          views.admin_panel_reviews,          name='admin_panel_reviews'),
    path('admin-panel/reviews/<int:review_id>/delete/', views.admin_panel_delete_review, name='admin_panel_delete_review'),
    path('admin-panel/subscriptions/',    views.admin_panel_subscriptions,    name='admin_panel_subscriptions'),
    path('admin-panel/register-admin/',   views.admin_panel_register_admin,   name='admin_panel_register_admin'),
    # ────────────────────────────────────────────────────────
    path('subscriptions/', views.subscription_plans, name='subscription_plans'),
    path('subscriptions/<int:plan_id>/pay/', views.create_subscription_payment, name='create_subscription_payment'),
    path('subscriptions/callback/', views.subscription_payment_callback, name='subscription_payment_callback'),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
