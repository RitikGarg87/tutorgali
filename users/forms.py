from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models import Profile, TutorGradeRate, TutorReview
import re

# ── Indian States & Cities ──────────────────────────────────────────────────

INDIAN_STATES = [
    ('', 'Select State'),
    ('Andhra Pradesh', 'Andhra Pradesh'),
    ('Arunachal Pradesh', 'Arunachal Pradesh'),
    ('Assam', 'Assam'),
    ('Bihar', 'Bihar'),
    ('Chhattisgarh', 'Chhattisgarh'),
    ('Goa', 'Goa'),
    ('Gujarat', 'Gujarat'),
    ('Haryana', 'Haryana'),
    ('Himachal Pradesh', 'Himachal Pradesh'),
    ('Jharkhand', 'Jharkhand'),
    ('Karnataka', 'Karnataka'),
    ('Kerala', 'Kerala'),
    ('Madhya Pradesh', 'Madhya Pradesh'),
    ('Maharashtra', 'Maharashtra'),
    ('Manipur', 'Manipur'),
    ('Meghalaya', 'Meghalaya'),
    ('Mizoram', 'Mizoram'),
    ('Nagaland', 'Nagaland'),
    ('Odisha', 'Odisha'),
    ('Punjab', 'Punjab'),
    ('Rajasthan', 'Rajasthan'),
    ('Sikkim', 'Sikkim'),
    ('Tamil Nadu', 'Tamil Nadu'),
    ('Telangana', 'Telangana'),
    ('Tripura', 'Tripura'),
    ('Uttar Pradesh', 'Uttar Pradesh'),
    ('Uttarakhand', 'Uttarakhand'),
    ('West Bengal', 'West Bengal'),
    # Union Territories
    ('Andaman and Nicobar Islands', 'Andaman and Nicobar Islands'),
    ('Chandigarh', 'Chandigarh'),
    ('Dadra and Nagar Haveli and Daman and Diu', 'Dadra and Nagar Haveli and Daman and Diu'),
    ('Delhi', 'Delhi'),
    ('Jammu and Kashmir', 'Jammu and Kashmir'),
    ('Ladakh', 'Ladakh'),
    ('Lakshadweep', 'Lakshadweep'),
    ('Puducherry', 'Puducherry'),
]

# Cities grouped by state — used in JS for dynamic filtering
CITIES_BY_STATE = {
    'Andhra Pradesh': ['Visakhapatnam', 'Vijayawada', 'Guntur', 'Nellore', 'Kurnool', 'Rajahmundry', 'Tirupati', 'Kakinada', 'Kadapa', 'Anantapur', 'Vizianagaram', 'Eluru', 'Ongole', 'Nandyal', 'Machilipatnam', 'Adoni', 'Tenali', 'Chittoor', 'Hindupur', 'Proddatur', 'Bhimavaram', 'Madanapalle', 'Guntakal', 'Dharmavaram', 'Gudivada', 'Narasaraopet', 'Tadipatri', 'Tadepalligudem', 'Chilakaluripet', 'Yemmiganur'],
    'Arunachal Pradesh': ['Itanagar', 'Naharlagun', 'Pasighat', 'Namsai', 'Bomdila', 'Ziro', 'Along', 'Tezu', 'Khonsa', 'Roing', 'Aalo', 'Daporijo', 'Anini', 'Changlang', 'Tawang'],
    'Assam': ['Guwahati', 'Silchar', 'Dibrugarh', 'Jorhat', 'Nagaon', 'Tinsukia', 'Tezpur', 'Bongaigaon', 'Dhubri', 'Diphu', 'North Lakhimpur', 'Sivasagar', 'Goalpara', 'Barpeta', 'Karimganj', 'Hailakandi', 'Haflong', 'Mangaldoi', 'Nalbari', 'Kokrajhar'],
    'Bihar': ['Patna', 'Gaya', 'Bhagalpur', 'Muzaffarpur', 'Purnia', 'Darbhanga', 'Bihar Sharif', 'Arrah', 'Begusarai', 'Katihar', 'Munger', 'Chhapra', 'Danapur', 'Bettiah', 'Saharsa', 'Sasaram', 'Hajipur', 'Dehri', 'Siwan', 'Motihari', 'Nawada', 'Bagaha', 'Buxar', 'Kishanganj', 'Sitamarhi', 'Jamalpur', 'Jehanabad', 'Aurangabad', 'Lakhisarai', 'Sheikhpura'],
    'Chhattisgarh': ['Raipur', 'Bhilai', 'Bilaspur', 'Korba', 'Durg', 'Rajnandgaon', 'Jagdalpur', 'Raigarh', 'Ambikapur', 'Mahasamund', 'Dhamtari', 'Chirmiri', 'Bhatapara', 'Naila Janjgir', 'Tilda Newra', 'Mungeli', 'Manendragarh', 'Sakti', 'Dongargarh', 'Kanker'],
    'Goa': ['Panaji', 'Margao', 'Vasco da Gama', 'Mapusa', 'Ponda', 'Bicholim', 'Curchorem', 'Sanquelim', 'Cuncolim', 'Quepem'],
    'Gujarat': ['Ahmedabad', 'Surat', 'Vadodara', 'Rajkot', 'Bhavnagar', 'Jamnagar', 'Junagadh', 'Gandhinagar', 'Anand', 'Navsari', 'Morbi', 'Nadiad', 'Surendranagar', 'Bharuch', 'Mehsana', 'Bhuj', 'Porbandar', 'Palanpur', 'Valsad', 'Vapi', 'Gondal', 'Veraval', 'Godhra', 'Patan', 'Kalol', 'Dahod', 'Botad', 'Amreli', 'Deesa', 'Jetpur'],
    'Haryana': ['Faridabad', 'Gurgaon', 'Panipat', 'Ambala', 'Yamunanagar', 'Rohtak', 'Hisar', 'Karnal', 'Sonipat', 'Panchkula', 'Bhiwani', 'Sirsa', 'Bahadurgarh', 'Jind', 'Thanesar', 'Kaithal', 'Rewari', 'Palwal', 'Narnaul', 'Fatehabad', 'Mewat', 'Jhajjar', 'Mahendragarh', 'Charkhi Dadri'],
    'Himachal Pradesh': ['Shimla', 'Mandi', 'Solan', 'Dharamsala', 'Kullu', 'Hamirpur', 'Una', 'Nahan', 'Palampur', 'Baddi', 'Sundarnagar', 'Chamba', 'Bilaspur', 'Kangra', 'Keylong'],
    'Jharkhand': ['Ranchi', 'Jamshedpur', 'Dhanbad', 'Bokaro', 'Deoghar', 'Phusro', 'Hazaribagh', 'Giridih', 'Ramgarh', 'Medininagar', 'Chirkunda', 'Chaibasa', 'Dumka', 'Sahibganj', 'Gumla', 'Lohardaga', 'Simdega', 'Pakur', 'Godda', 'Koderma'],
    'Karnataka': ['Bengaluru', 'Mysuru', 'Hubballi', 'Mangaluru', 'Belagavi', 'Kalaburagi', 'Ballari', 'Vijayapura', 'Shivamogga', 'Tumakuru', 'Davanagere', 'Bidar', 'Udupi', 'Hospet', 'Hassan', 'Gadag-Betageri', 'Dharwad', 'Chitradurga', 'Raichur', 'Bhadravati', 'Mandya', 'Chikkamagaluru', 'Kolar', 'Ramanagara', 'Bagalkot', 'Yadgir', 'Koppal', 'Haveri', 'Chamarajanagar', 'Kodagu'],
    'Kerala': ['Thiruvananthapuram', 'Kochi', 'Kozhikode', 'Thrissur', 'Kollam', 'Palakkad', 'Alappuzha', 'Malappuram', 'Kannur', 'Kasaragod', 'Kottayam', 'Idukki', 'Wayanad', 'Pathanamthitta', 'Ernakulam'],
    'Madhya Pradesh': ['Bhopal', 'Indore', 'Jabalpur', 'Gwalior', 'Ujjain', 'Sagar', 'Dewas', 'Satna', 'Ratlam', 'Rewa', 'Murwara', 'Singrauli', 'Burhanpur', 'Khandwa', 'Bhind', 'Chhindwara', 'Guna', 'Shivpuri', 'Vidisha', 'Chhatarpur', 'Damoh', 'Mandsaur', 'Khargone', 'Neemuch', 'Pithampur', 'Hoshangabad', 'Itarsi', 'Sehore', 'Betul', 'Seoni'],
    'Maharashtra': ['Mumbai', 'Pune', 'Nagpur', 'Thane', 'Nashik', 'Aurangabad', 'Solapur', 'Amravati', 'Kolhapur', 'Navi Mumbai', 'Sangli', 'Malegaon', 'Jalgaon', 'Akola', 'Latur', 'Dhule', 'Ahmednagar', 'Chandrapur', 'Parbhani', 'Ichalkaranji', 'Jalna', 'Ambarnath', 'Bhiwandi', 'Nanded', 'Ulhasnagar', 'Satara', 'Ratnagiri', 'Osmanabad', 'Beed', 'Yavatmal'],
    'Manipur': ['Imphal', 'Thoubal', 'Bishnupur', 'Churachandpur', 'Senapati', 'Ukhrul', 'Tamenglong', 'Chandel', 'Jiribam', 'Kakching'],
    'Meghalaya': ['Shillong', 'Tura', 'Nongstoin', 'Jowai', 'Baghmara', 'Resubelpara', 'Williamnagar', 'Nongpoh', 'Mairang', 'Cherrapunji'],
    'Mizoram': ['Aizawl', 'Lunglei', 'Saiha', 'Champhai', 'Kolasib', 'Serchhip', 'Lawngtlai', 'Mamit', 'Saitual', 'Khawzawl'],
    'Nagaland': ['Kohima', 'Dimapur', 'Mokokchung', 'Tuensang', 'Wokha', 'Zunheboto', 'Phek', 'Mon', 'Kiphire', 'Longleng'],
    'Odisha': ['Bhubaneswar', 'Cuttack', 'Rourkela', 'Brahmapur', 'Sambalpur', 'Puri', 'Balasore', 'Bhadrak', 'Baripada', 'Jharsuguda', 'Jeypore', 'Bargarh', 'Paradip', 'Kendujhar', 'Sundargarh', 'Phulbani', 'Rayagada', 'Koraput', 'Nabarangpur', 'Bolangir'],
    'Punjab': ['Ludhiana', 'Amritsar', 'Jalandhar', 'Patiala', 'Bathinda', 'Mohali', 'Hoshiarpur', 'Batala', 'Pathankot', 'Moga', 'Abohar', 'Malerkotla', 'Khanna', 'Phagwara', 'Muktsar', 'Barnala', 'Rajpura', 'Firozpur', 'Kapurthala', 'Sangrur'],
    'Rajasthan': ['Jaipur', 'Jodhpur', 'Kota', 'Bikaner', 'Ajmer', 'Udaipur', 'Bhilwara', 'Alwar', 'Bharatpur', 'Sikar', 'Pali', 'Sri Ganganagar', 'Tonk', 'Kishangarh', 'Beawar', 'Hanumangarh', 'Dhaulpur', 'Churu', 'Sawai Madhopur', 'Nagaur', 'Jhunjhunu', 'Banswara', 'Baran', 'Barmer', 'Jaisalmer', 'Jhalawar', 'Karauli', 'Pratapgarh', 'Rajsamand', 'Sirohi'],
    'Sikkim': ['Gangtok', 'Namchi', 'Gyalshing', 'Mangan', 'Rangpo', 'Singtam', 'Jorethang', 'Nayabazar', 'Ravangla', 'Yuksom'],
    'Tamil Nadu': ['Chennai', 'Coimbatore', 'Madurai', 'Tiruchirappalli', 'Salem', 'Tirunelveli', 'Tiruppur', 'Vellore', 'Erode', 'Thoothukkudi', 'Dindigul', 'Thanjavur', 'Ranipet', 'Sivakasi', 'Karur', 'Udhagamandalam', 'Hosur', 'Nagercoil', 'Kanchipuram', 'Kumarapalayam', 'Karaikkudi', 'Neyveli', 'Cuddalore', 'Kumbakonam', 'Tiruvannamalai', 'Pollachi', 'Rajapalayam', 'Gudiyatham', 'Pudukkottai', 'Vaniyambadi'],
    'Telangana': ['Hyderabad', 'Warangal', 'Nizamabad', 'Karimnagar', 'Ramagundam', 'Khammam', 'Mahbubnagar', 'Nalgonda', 'Adilabad', 'Suryapet', 'Miryalaguda', 'Siddipet', 'Jagtial', 'Mancherial', 'Nirmal', 'Kothagudem', 'Bodhan', 'Sangareddy', 'Medak', 'Bhongir'],
    'Tripura': ['Agartala', 'Dharmanagar', 'Udaipur', 'Kailasahar', 'Belonia', 'Khowai', 'Ambassa', 'Sabroom', 'Sonamura', 'Bishalgarh'],
    'Uttar Pradesh': ['Lucknow', 'Kanpur', 'Ghaziabad', 'Agra', 'Meerut', 'Varanasi', 'Prayagraj', 'Bareilly', 'Aligarh', 'Moradabad', 'Saharanpur', 'Gorakhpur', 'Noida', 'Firozabad', 'Jhansi', 'Muzaffarnagar', 'Mathura', 'Rampur', 'Shahjahanpur', 'Mau', 'Farrukhabad', 'Hapur', 'Etawah', 'Mirzapur', 'Bulandshahr', 'Sambhal', 'Amroha', 'Hardoi', 'Fatehpur', 'Raebareli', 'Orai', 'Sitapur', 'Bahraich', 'Modinagar', 'Unnao', 'Jaunpur', 'Lakhimpur', 'Hathras', 'Banda', 'Pilibhit'],
    'Uttarakhand': ['Dehradun', 'Haridwar', 'Roorkee', 'Haldwani', 'Rudrapur', 'Kashipur', 'Rishikesh', 'Kotdwar', 'Ramnagar', 'Pithoragarh', 'Almora', 'Nainital', 'Mussoorie', 'Tehri', 'Uttarkashi'],
    'West Bengal': ['Kolkata', 'Asansol', 'Siliguri', 'Durgapur', 'Bardhaman', 'Malda', 'Baharampur', 'Habra', 'Kharagpur', 'Shantipur', 'Dankuni', 'Dhulian', 'Ranaghat', 'Haldia', 'Raiganj', 'Krishnanagar', 'Nabadwip', 'Medinipur', 'Jalpaiguri', 'Balurghat', 'Basirhat', 'Bankura', 'Chakdaha', 'Darjeeling', 'Alipurduar', 'Purulia', 'Jangipur', 'Bolpur', 'Bangaon', 'Cooch Behar'],
    # Union Territories
    'Andaman and Nicobar Islands': ['Port Blair', 'Diglipur', 'Rangat', 'Mayabunder', 'Car Nicobar'],
    'Chandigarh': ['Chandigarh'],
    'Dadra and Nagar Haveli and Daman and Diu': ['Daman', 'Diu', 'Silvassa'],
    'Delhi': ['New Delhi', 'Delhi', 'Dwarka', 'Rohini', 'Janakpuri', 'Laxmi Nagar', 'Shahdara', 'Pitampura', 'Saket', 'Vasant Kunj', 'Karol Bagh', 'Connaught Place', 'Preet Vihar', 'Mayur Vihar', 'Narela'],
    'Jammu and Kashmir': ['Srinagar', 'Jammu', 'Anantnag', 'Sopore', 'Baramulla', 'Kathua', 'Udhampur', 'Punch', 'Rajouri', 'Kupwara'],
    'Ladakh': ['Leh', 'Kargil'],
    'Lakshadweep': ['Kavaratti', 'Agatti', 'Amini', 'Andrott', 'Minicoy'],
    'Puducherry': ['Puducherry', 'Karaikal', 'Mahe', 'Yanam'],
}

# Flat list of all cities for the dropdown (shown before state is selected)
ALL_CITIES = [('', 'Select City First Select State')] + sorted(
    [(city, city) for state_cities in CITIES_BY_STATE.values() for city in state_cities],
    key=lambda x: x[0]
)

class SignUpForm(UserCreationForm):
    role = forms.ChoiceField(
        choices=Profile.USER_ROLES, 
        required=True,
        widget=forms.RadioSelect(attrs={'class': 'role-radio'})
    )
    
    full_name = forms.CharField(
        max_length=200,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Enter your Full name Eg: Amit Singh', 'class': 'form-control'})
    )

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'placeholder': 'Enter your Email Eg: amit@gmail.com', 'class': 'form-control'})
    )

    mobile_number = forms.CharField(
        max_length=10,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Enter your Mobile Number', 'maxlength': '10', 'class': 'form-control'})
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
        self.fields['password1'].widget.attrs.update({'placeholder': 'Create a strong password', 'class': 'form-control'})
        self.fields['password2'].widget.attrs.update({'placeholder': 'Re-enter your password', 'class': 'form-control'})

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
            'autofocus': True,
            'class': 'form-control',
        })
    )
    password = forms.CharField(
        label='Password',
        strip=False,
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Enter Password',
            'class': 'form-control',
        })
    )
    
    error_messages = {
        'invalid_login': 'Please enter a valid email/mobile number and password.',
        'inactive': 'This account is inactive.',
    }


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['full_name', 'gender', 'location', 'city', 'state', 'pincode']
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your full name',
            }),
            'gender': forms.Select(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Patel Nagar, New Delhi',
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'City',
            }),
            'state': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'State',
            }),
            'pincode': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '6-digit pincode',
                'maxlength': '6',
            }),
        }

    def __init__(self, *args, **kwargs):
        role = kwargs.pop('role', None)
        super(ProfileForm, self).__init__(*args, **kwargs)

        if role == 'tutor':
            # Hide student-only fields for tutors
            for f in ['location', 'city', 'state', 'pincode']:
                self.fields[f].widget = forms.HiddenInput()
                self.fields[f].required = False


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
    
    state = forms.ChoiceField(
        choices=INDIAN_STATES,
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'id_state',
        })
    )

    city = forms.ChoiceField(
        choices=ALL_CITIES,
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'id_city',
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
                'placeholder': '₹/month',
                'class': 'form-control',
                'min': '0',
                'step': '50'
            }),
            'rate_student_home': forms.NumberInput(attrs={
                'placeholder': '₹/month',
                'class': 'form-control',
                'min': '0',
                'step': '50'
            }),
            'rate_my_home': forms.NumberInput(attrs={
                'placeholder': '₹/month',
                'class': 'form-control',
                'min': '0',
                'step': '50'
            }),
        }


class TutorReviewForm(forms.ModelForm):
    RATING_CHOICES = [(i, i) for i in range(1, 6)]
    rating = forms.ChoiceField(
        choices=RATING_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'star-radio'}),
        label='Your Rating'
    )

    class Meta:
        model = TutorReview
        fields = ['rating', 'comment']
        widgets = {
            'comment': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Share your experience with this tutor (optional)',
                'class': 'form-control',
            }),
        }
        labels = {
            'comment': 'Your Review (optional)',
        }
