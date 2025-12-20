from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordChangeForm
from .models import CustomUser, Profile


class CustomUserCreationForm(UserCreationForm):
    """
    Custom user creation form
    """
    email = forms.EmailField(required=True)
    first_name = forms.CharField(required=True)
    last_name = forms.CharField(required=True)
    phone_number = forms.CharField(required=False, max_length=17)
    date_of_birth = forms.DateField(
        required=False, 
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 'phone_number', 'date_of_birth', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add CSS classes
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
            if field_name in ['first_name', 'last_name']:
                field.widget.attrs['placeholder'] = f'Inserisci {field_name}'
            elif field_name == 'email':
                field.widget.attrs['placeholder'] = 'Inserisci la tua email'
            elif field_name == 'username':
                field.widget.attrs['placeholder'] = 'Scegli un username'
            elif field_name == 'phone_number':
                field.widget.attrs['placeholder'] = '+39 123 456 7890'
            elif field_name == 'date_of_birth':
                field.widget.attrs['class'] = 'form-control'
    
    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError("Questa email è già registrata.")
        return email


class CustomUserLoginForm(AuthenticationForm):
    """
    Custom login form
    """
    remember_me = forms.BooleanField(required=False, initial=True)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
            field.widget.attrs['placeholder'] = field_name.title()
        
        # Remove the default remember_me field and add our custom one
        if 'remember_me' in self.fields:
            del self.fields['remember_me']
        
        self.fields['remember_me'] = forms.BooleanField(required=False, initial=True)


class ProfileForm(forms.ModelForm):
    """
    User profile form
    """
    class Meta:
        model = Profile
        fields = ('profile_image', 'bio', 'address_line1', 'address_line2', 'city', 'state', 'postal_code', 'country')
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Raccontaci qualcosa di te...', 'class': 'form-control'}),
            'address_line1': forms.TextInput(attrs={'placeholder': 'Via/Piazza, numero civico', 'class': 'form-control'}),
            'address_line2': forms.TextInput(attrs={'placeholder': 'Appartamento, interno, ecc. (opzionale)', 'class': 'form-control'}),
            'city': forms.TextInput(attrs={'placeholder': 'Città', 'class': 'form-control'}),
            'state': forms.TextInput(attrs={'placeholder': 'Provincia/Regione', 'class': 'form-control'}),
            'postal_code': forms.TextInput(attrs={'placeholder': 'CAP', 'class': 'form-control'}),
            'country': forms.TextInput(attrs={'placeholder': 'Paese', 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name not in ['bio', 'profile_image']:
                if 'class' not in field.widget.attrs:
                    field.widget.attrs['class'] = 'form-control'
                    
            if field_name == 'profile_image':
                field.widget.attrs['accept'] = 'image/*'


class UserSettingsForm(forms.ModelForm):
    """
    User settings form
    """
    class Meta:
        model = CustomUser
        fields = ('email', 'phone_number', 'date_of_birth')
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+39 123 456 7890'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-control'
            if field_name == 'phone_number' and 'placeholder' not in field.widget.attrs:
                field.widget.attrs['placeholder'] = '+39 123 456 7890'


class CustomPasswordChangeForm(PasswordChangeForm):
    """
    Custom password change form with Bootstrap styling
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'