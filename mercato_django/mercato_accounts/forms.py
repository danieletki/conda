from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
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
            'bio': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Raccontaci qualcosa di te...'}),
            'address_line1': forms.TextInput(attrs={'placeholder': 'Via/Piazza, numero civico'}),
            'address_line2': forms.TextInput(attrs={'placeholder': 'Appartamento, interno, ecc. (opzionale)'}),
            'city': forms.TextInput(attrs={'placeholder': 'Città'}),
            'state': forms.TextInput(attrs={'placeholder': 'Provincia/Regione'}),
            'postal_code': forms.TextInput(attrs={'placeholder': 'CAP'}),
            'country': forms.TextInput(attrs={'placeholder': 'Paese'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name != 'bio':
                field.widget.attrs['class'] = 'form-control'


class UserSettingsForm(forms.ModelForm):
    """
    User settings form
    """
    class Meta:
        model = CustomUser
        fields = ('email', 'phone_number', 'date_of_birth')
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
            if field_name == 'phone_number':
                field.widget.attrs['placeholder'] = '+39 123 456 7890'