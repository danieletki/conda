from django import forms
from django.core.exceptions import ValidationError
from decimal import Decimal

from .models import Categoria, Lottery, Regione, Auction


class LotteryCreationForm(forms.ModelForm):
    """Form for creating new lotteries with image uploads"""

    regione = forms.ModelChoiceField(
        label='Regione',
        required=True,
        queryset=Regione.objects.none(),
        empty_label='Seleziona una regione',
        widget=forms.Select(attrs={'class': 'form-select'}),
        error_messages={'required': 'Seleziona una regione.'},
    )

    categoria = forms.ModelChoiceField(
        label='Categoria',
        required=True,
        queryset=Categoria.objects.none(),
        empty_label='Seleziona una categoria',
        widget=forms.Select(attrs={'class': 'form-select'}),
        error_messages={'required': 'Seleziona una categoria.'},
    )

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
            'title',
            'description',
            'regione',
            'categoria',
            'item_value',
            'items_count',
            'expiration_date',
            'image_1_file',
            'image_2_file',
            'image_3_file',
            'image_1_description',
            'image_2_description',
            'image_3_description',
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

        self.fields['regione'].queryset = Regione.objects.order_by('name')
        self.fields['categoria'].queryset = Categoria.objects.order_by('name')

        self.fields['item_value'].help_text = (
            'Il prezzo del biglietto verrà calcolato automaticamente: valore / numero biglietti'
        )
    
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


class AuctionCreationForm(forms.ModelForm):
    """Form for creating new auctions with image uploads"""

    regione = forms.ModelChoiceField(
        label='Regione',
        required=True,
        queryset=Regione.objects.none(),
        empty_label='Seleziona una regione',
        widget=forms.Select(attrs={'class': 'form-select'}),
        error_messages={'required': 'Seleziona una regione.'},
    )

    categoria = forms.ModelChoiceField(
        label='Categoria',
        required=True,
        queryset=Categoria.objects.none(),
        empty_label='Seleziona una categoria',
        widget=forms.Select(attrs={'class': 'form-select'}),
        error_messages={'required': 'Seleziona una categoria.'},
    )

    image_1_file = forms.ImageField(
        label='Immagine 1 (Principale)',
        required=True,
        help_text='Immagine principale dell\'asta',
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
    
    auction_end_time = forms.DateTimeField(
        label='Data di chiusura asta',
        required=False,
        widget=forms.DateTimeInput(
            attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }
        ),
        help_text='Data e ora di chiusura dell\'asta (opzionale, lascia vuoto per chiusura manuale)'
    )
    
    class Meta:
        model = Auction
        fields = (
            'title',
            'description',
            'regione',
            'categoria',
            'item_value',
            'starting_price',
            'reserve_price',
            'bid_increment',
            'auction_end_time',
            'auto_close_on_end_time',
            'image_1_file',
            'image_2_file',
            'image_3_file',
            'image_1_description',
            'image_2_description',
            'image_3_description',
        )
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Titolo dell\'asta'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Descrizione dettagliata dell\'oggetto in vendita'
            }),
            'item_value': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01',
                'placeholder': 'Valore stimato dell\'oggetto'
            }),
            'starting_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01',
                'placeholder': 'Prezzo di partenza'
            }),
            'reserve_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01',
                'placeholder': 'Prezzo di riserva (opzionale)'
            }),
            'bid_increment': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '1.00',
                'value': '10.00',
                'placeholder': 'Incremento minimo tra offerte'
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

        self.fields['regione'].queryset = Regione.objects.order_by('name')
        self.fields['categoria'].queryset = Categoria.objects.order_by('name')

        self.fields['item_value'].help_text = 'Valore stimato dell\'oggetto per riferimento'
        self.fields['starting_price'].help_text = 'Prezzo di partenza dell\'asta'
        self.fields['reserve_price'].help_text = 'Prezzo minimo per chiudere l\'asta con un vincitore'
        self.fields['bid_increment'].help_text = 'Incremento minimo richiesto tra due offerte consecutive'
        self.fields['auto_close_on_end_time'].label = 'Chiudi automaticamente al termine'
    
    def clean(self):
        cleaned_data = super().clean()
        
        starting_price = cleaned_data.get('starting_price')
        reserve_price = cleaned_data.get('reserve_price')
        
        # Validate at least one image is provided
        if not self.cleaned_data.get('image_1_file'):
            raise ValidationError("É necessario caricare almeno l'immagine principale.")
        
        # Validate reserve price is higher than starting price
        if reserve_price and starting_price and reserve_price <= starting_price:
            raise ValidationError(
                "Il prezzo di riserva deve essere superiore al prezzo di partenza"
            )
        
        return cleaned_data
    
    def save(self, commit=True):
        auction = super().save(commit=False)
        
        # Handle image uploads
        if self.cleaned_data.get('image_1_file'):
            auction.set_image_1(self.cleaned_data['image_1_file'])
        
        if self.cleaned_data.get('image_2_file'):
            auction.set_image_2(self.cleaned_data['image_2_file'])
        
        if self.cleaned_data.get('image_3_file'):
            auction.set_image_3(self.cleaned_data['image_3_file'])
        
        if commit:
            auction.save()
        
        return auction