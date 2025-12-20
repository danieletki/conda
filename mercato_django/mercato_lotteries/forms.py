from django import forms
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.core.exceptions import ValidationError

from .models import Lottery


class LotteryCreationForm(forms.ModelForm):
    """Form for creating new lotteries with image uploads"""
    
    image_1_file = forms.ImageField(
        label='Immagine 1 (Principale)',
        required=True,
        help_text='Immagine principale della lotteria',
        widget=forms.FileInput(attrs={'accept': 'image/*', 'class': 'form-control'})
    )
    
    image_2_file = forms.ImageField(
        label='Immagine 2',
        required=False,
        help_text='Seconda immagine (opzionale)',
        widget=forms.FileInput(attrs={'accept': 'image/*', 'class': 'form-control'})
    )
    
    image_3_file = forms.ImageField(
        label='Immagine 3',
        required=False,
        help_text='Terza immagine (opzionale)',
        widget=forms.FileInput(attrs={'accept': 'image/*', 'class': 'form-control'})
    )
    
    expiration_date = forms.DateTimeField(
        label='Data di scadenza',
        required=False,
        widget=forms.DateTimeInput(
            attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }
        ),
        help_text='Data di scadenza della lotteria (opzionale)'
    )
    
    class Meta:
        model = Lottery
        fields = (
            'title', 'description', 'item_value', 'items_count',
            'expiration_date',
            'image_1_file', 'image_2_file', 'image_3_file',
            'image_1_description', 'image_2_description', 'image_3_description'
        )
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Titolo della lotteria'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Descrizione dettagliata dell\'oggetto in palio'
            }),
            'item_value': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01',
                'placeholder': 'Valore dell\'oggetto'
            }),
            'items_count': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'placeholder': 'Numero di biglietti da vendere'
            }),
            'image_1_description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Descrizione immagine principale'
            }),
            'image_2_description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Descrizione seconda immagine'
            }),
            'image_3_description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Descrizione terza immagine'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add help text for computed fields
        self.fields['item_value'].help_text = 'Il prezzo del biglietto verrà calcolato automaticamente: valore / numero biglietti'
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validate at least one image is provided
        if not self.cleaned_data.get('image_1_file'):
            raise ValidationError("É necessario caricare almeno l'immagine principale.")
        
        return cleaned_data
    
    def save(self, commit=True):
        lottery = super().save(commit=False)
        
        # Calculate ticket price automatically
        if lottery.item_value and lottery.items_count:
            lottery.ticket_price = lottery.calculate_ticket_price()
        
        # Handle image uploads
        if self.cleaned_data.get('image_1_file'):
            lottery.set_image_1(self.cleaned_data['image_1_file'])
        
        if self.cleaned_data.get('image_2_file'):
            lottery.set_image_2(self.cleaned_data['image_2_file'])
        
        if self.cleaned_data.get('image_3_file'):
            lottery.set_image_3(self.cleaned_data['image_3_file'])
        
        if commit:
            lottery.save()
        
        return lottery