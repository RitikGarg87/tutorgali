import json
import os
from django.conf import settings
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models import Profile, TutorGradeRate
import re

class SignUpForm(UserCreationForm):
    role = forms.ChoiceField(
        choices=Profile.USER_ROLES, 
        required=True,
        widget=forms.RadioSelect(attrs={'class': 'role-radio'})
    )
    
    full_name = forms.CharField(
        max_length=200,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Enter your Full name Eg: Amit Singh'})
    )
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'placeholder': 'Enter your Email Eg: amit@gmail.com'})
    )
    
    mobile_number = forms.CharField(
        max_length=10,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Enter your Mobile Number', 'maxlength': '10'})
    )
    
    gender = forms.ChoiceField(
        choices=[('', 'Select Gender')] + list(Profile.GENDER_CHOICES),
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    # REMOVED: pincode field

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={'style': 'display:none'}),
        }
        labels = {
            'password1': 'Set Password',
            'password2': 'Confirm Password',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].required = False
        self.fields['password1'].label = 'Set Password'
        self.fields['password2'].label = 'Confirm Password'
        self.fields['password1'].widget.attrs.update({'placeholder': 'Create a strong password'})
        self.fields['password2'].widget.attrs.update({'placeholder': 'Re-enter your password'})

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('This email is already registered. Please login or use another email.')
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            raise forms.ValidationError('Please enter a valid email address.')
        return email

    def clean_mobile_number(self):
        mobile = self.cleaned_data.get('mobile_number')
        mobile = re.sub(r'[^0-9]', '', mobile)
        if len(mobile) != 10:
            raise forms.ValidationError('Mobile number must be exactly 10 digits.')
        if not mobile[0] in ['6', '7', '8', '9']:
            raise forms.ValidationError('Please enter a valid Indian mobile number.')
        if Profile.objects.filter(mobile_number=mobile).exists():
            raise forms.ValidationError('This mobile number is already registered.')
        return mobile
    
    def clean_full_name(self):
        name = self.cleaned_data.get('full_name')
        if len(name) < 3:
            raise forms.ValidationError('Please enter your full name (at least 3 characters).')
        if not re.match(r'^[a-zA-Z\s]+$', name):
            raise forms.ValidationError('Name should contain only letters and spaces.')
        return name.strip()

    def save(self, commit=True):
        email = self.cleaned_data['email']
        base_username = email.split('@')[0]
        username = base_username
        counter = 1
        
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
        
        user = User.objects.create_user(
            username=username,
            email=email,
            password=self.cleaned_data['password1']
        )
        
        if commit:
            user.save()
            profile = user.profile
            profile.role = self.cleaned_data['role']
            profile.full_name = self.cleaned_data['full_name']
            profile.mobile_number = self.cleaned_data['mobile_number']
            profile.gender = self.cleaned_data['gender']
            # REMOVED: profile.pincode = self.cleaned_data['pincode']
            
            if profile.role == 'tutor':
                profile.tutor_type = 'individual'
            
            profile.save()
        
        return user


class EmailOrMobileLoginForm(AuthenticationForm):
    username = forms.CharField(
        label='Email or Mobile Number',
        max_length=254,
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter Email or Mobile Number',
            'autofocus': True
        })
    )
    password = forms.CharField(
        label='Password',
        strip=False,
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Enter Password'
        })
    )
    
    error_messages = {
        'invalid_login': 'Please enter a valid email/mobile number and password.',
        'inactive': 'This account is inactive.',
    }


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['location']

    def __init__(self, *args, **kwargs):
        role = kwargs.pop('role', None)
        super(ProfileForm, self).__init__(*args, **kwargs)
        
        if role == 'tutor':
            self.fields['location'].widget = forms.HiddenInput()


class VerificationForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['education_certificate', 'id_proof']
        widgets = {
            'education_certificate': forms.FileInput(attrs={'accept': '.pdf,.jpg,.jpeg,.png'}),
            'id_proof': forms.FileInput(attrs={'accept': '.pdf,.jpg,.jpeg,.png'}),
        }


class TutorOnboardingForm(forms.ModelForm):
    QUALIFICATION_CHOICES = [
        ('', 'Select Your Degree'),
        ('PhD', 'PhD'),
        ('M.Tech', 'M.Tech'),
        ('M.Sc', 'M.Sc'),
        ('M.A', 'M.A'),
        ('MBA', 'MBA'),
        ('B.Tech', 'B.Tech'),
        ('B.E', 'B.E'),
        ('B.Sc', 'B.Sc'),
        ('B.A', 'B.A'),
        ('B.Com', 'B.Com'),
        ('BCA', 'BCA'),
        ('MCA', 'MCA'),
        ('12th Pass', '12th Pass (Higher Secondary)'),
        ('Diploma', 'Diploma'),
        ('Other', 'Other (Please Specify)'),
    ]
    
    qualification = forms.ChoiceField(
        choices=QUALIFICATION_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_qualification'})
    )
    
    qualification_other = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Please specify', 'class': 'form-control'})
    )
    
    education_institute = forms.CharField(
        max_length=300,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'College/University/School Name', 'class': 'form-control'})
    )
    
    # Address fields
    address_line1 = forms.CharField(
        max_length=300,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'House/Flat No., Building Name, Street',
            'class': 'form-control'
        })
    )
    
    address_line2 = forms.CharField(
        max_length=300,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Area, Landmark (Optional)',
            'class': 'form-control'
        })
    )
    
    city = forms.ChoiceField(
        choices=[('', 'Select City')],
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'id_city'
        })
    )
    
    state = forms.ChoiceField(
        choices=[('', 'Select State')],
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'id_state'
        })
    )
    
    pincode = forms.CharField(
        max_length=6,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'Pincode (6 digits)',
            'class': 'form-control',
            'maxlength': '6'
        })
    )
    
    languages = forms.MultipleChoiceField(
        choices=[
            ('english', 'English'),
            ('hindi', 'Hindi'),
            ('tamil', 'Tamil'),
            ('telugu', 'Telugu'),
            ('kannada', 'Kannada'),
            ('malayalam', 'Malayalam'),
            ('bengali', 'Bengali'),
            ('marathi', 'Marathi'),
            ('gujarati', 'Gujarati'),
            ('punjabi', 'Punjabi'),
        ],
        widget=forms.CheckboxSelectMultiple,
        required=True
    )
    
    teaching_mode = forms.MultipleChoiceField(
        choices=[
            ('online', 'I can teach Live Online using Video Call'),
            ('student_home', "I can teach at the student's home"),
            ('my_home', 'I can teach at my home'),
        ],
        widget=forms.CheckboxSelectMultiple,
        required=True
    )
    
    school_boards = forms.MultipleChoiceField(
        choices=[
            ('cbse', 'CBSE'),
            ('icse', 'ICSE'),
            ('state', 'State Board'),
            ('igcse', 'IGCSE'),
            ('ib', 'IB'),
            ('nios', 'NIOS'),
        ],
        widget=forms.CheckboxSelectMultiple,
        required=True
    )
    latitude = forms.FloatField(required=False, widget=forms.HiddenInput())
    longitude = forms.FloatField(required=False, widget=forms.HiddenInput())  
    class Meta:
        model = Profile
        fields = ['languages', 'qualification', 'qualification_other', 'education_institute',
                  'address_line1', 'address_line2', 'city', 'state', 'pincode',
                  'teaching_mode', 'school_boards', 'experience_years', 'bio','latitude', 'longitude']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Tell students about yourself...', 'class': 'form-control'}),
            'experience_years': forms.NumberInput(attrs={'placeholder': 'Years', 'min': '0', 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        json_path = os.path.join(
            settings.BASE_DIR,
            'static',
            'data',
            'india_state_city_map.json'
        )

        state_city_map = {}

        if os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    raw = f.read().strip()
                    if raw:
                        state_city_map = json.loads(raw)
            except json.JSONDecodeError:
                state_city_map = {}

        self.fields['state'].choices = [('', 'Select State')] + [
            (state, state) for state in sorted(state_city_map.keys())
        ]

        selected_state = None
        if self.is_bound:
            selected_state = self.data.get('state')
        elif self.instance and self.instance.state:
            selected_state = self.instance.state

        if selected_state and selected_state in state_city_map:
            self.fields['city'].choices = [('', 'Select City')] + [
                (city, city) for city in state_city_map[selected_state]
            ]
        else:
            self.fields['city'].choices = [('', 'Select City')]
    
    def clean_pincode(self):
        pincode = self.cleaned_data.get('pincode')
        if pincode and not pincode.isdigit():
            raise forms.ValidationError('Pincode must contain only digits.')
        if pincode and len(pincode) != 6:
            raise forms.ValidationError('Pincode must be exactly 6 digits.')
        return pincode
    
    def clean(self):
        cleaned_data = super().clean()
        qualification = cleaned_data.get('qualification')
        qualification_other = cleaned_data.get('qualification_other')
        
        if qualification == 'Other' and not qualification_other:
            raise forms.ValidationError('Please specify your qualification.')
        
        return cleaned_data


class TutorGradeRateForm(forms.ModelForm):
    """Form for each grade with subjects and rates"""
    
    class Meta:
        model = TutorGradeRate
        fields = ['subjects', 'rate_online', 'rate_student_home', 'rate_my_home']
        widgets = {
            'subjects': forms.TextInput(attrs={
                'placeholder': 'Enter subjects (comma-separated)',
                'class': 'form-control'
            }),
            'rate_online': forms.NumberInput(attrs={
                'placeholder': '₹/hour',
                'class': 'form-control',
                'min': '0',
                'step': '50'
            }),
            'rate_student_home': forms.NumberInput(attrs={
                'placeholder': '₹/hour',
                'class': 'form-control',
                'min': '0',
                'step': '50'
            }),
            'rate_my_home': forms.NumberInput(attrs={
                'placeholder': '₹/hour',
                'class': 'form-control',
                'min': '0',
                'step': '50'
            }),
        }
