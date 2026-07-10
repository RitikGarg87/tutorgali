from django.contrib.auth import views as auth_views
from . import views
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, reverse_lazy

urlpatterns = [
    path('register/', views.register, name='register'),
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
    path('subscriptions/', views.subscription_plans, name='subscription_plans'),
    path('subscriptions/<int:plan_id>/pay/', views.create_subscription_payment, name='create_subscription_payment'),
    path('subscriptions/callback/', views.subscription_payment_callback, name='subscription_payment_callback'),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
