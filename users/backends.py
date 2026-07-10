from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from users.models import Profile

class EmailOrMobileBackend(ModelBackend):
    """
    Custom authentication backend that allows users to login with:
    - Email address
    - Mobile number
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            return None
        
        try:
            # Check if username is email
            if '@' in username:
                user = User.objects.get(email=username)
            # Check if username is mobile number (10 digits)
            elif username.isdigit() and len(username) == 10:
                profile = Profile.objects.get(mobile_number=username)
                user = profile.user
            else:
                # Fallback to username
                user = User.objects.get(username=username)
            
            # Verify password
            if user.check_password(password):
                return user
        except (User.DoesNotExist, Profile.DoesNotExist):
            return None
        
        return None
