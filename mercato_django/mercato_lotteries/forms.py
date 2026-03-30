from django import forms
from django.core.exceptions import ValidationError
from .models import Categoria, Auction, Regione


class AuctionCreationForm(forms.ModelForm):
    """Form for creating new auctions"""

    regione = forms.ModelChoiceField(
        label='Regione', required=True, queryset=Regione.objects.none(),
        empty_label='Seleziona una regione', widget=forms.Select(attrs={'class': 'form-select'}),
        error_messages={'required': 'Seleziona una regione.'},
    )

    categoria = forms.ModelChoiceField(
        label='Categoria', required=True, queryset=Categoria.objects.none(),
        empty_label='Seleziona una categoria', widget=forms.Select(attrs={'class': 'form-select'}),
        error_messages={'required': 'Seleziona una categoria.'},
    )

    image_1_file = forms.ImageField(
        label='Immagine 1 (Principale)', required=True,
        help_text='Immagine principale dell\'asta',
        widget=forms.FileInput(attrs={'accept': 'image/*', 'class': 'form-control'})
    )
    
    image_2_file = forms.ImageField(
        label='Immagine 2', required=False,
        help_text='Seconda immagine (opzionale)',
        widget=forms.FileInput(attrs={'accept': 'image/*', 'class': 'form-control'})
    )
    
    image_3_file = forms.ImageField(
        label='Immagine 3', required=False,
        help_text='Terza immagine (opzionale)',
        widget=forms.FileInput(attrs={'accept': 'image/*', 'class': 'form-control'})
    )
    
    auction_end_time = forms.DateTimeField(
        label='Data di chiusura', required=True,
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
        help_text='Data e ora di chiusura dell\'asta'
    )
    
    class Meta:
        model = Auction
        fields = (
            'title', 'description', 'regione', 'categoria', 'item_value',
            'starting_price', 'reserve_price', 'bid_increment', 'auction_end_time',
            'image_1_file', 'image_2_file', 'image_3_file',
            'image_1_description', 'image_2_description', 'image_3_description',
        )
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Titolo dell\'asta'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Descrizione dettagliata dell\'oggetto'}),
            'item_value': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01', 'placeholder': 'Valore stimato dell\'oggetto'}),
            'starting_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01', 'placeholder': 'Prezzo di partenza'}),
            'reserve_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01', 'placeholder': 'Prezzo riserva (opzionale)'}),
            'bid_increment': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01', 'value': '1.00', 'placeholder': 'Incremento minimo'}),
            'image_1_description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Descrizione immagine principale'}),
            'image_2_description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Descrizione seconda immagine'}),
            'image_3_description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Descrizione terza immagine'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['regione'].queryset = Regione.objects.order_by('name')
        self.fields['categoria'].queryset = Categoria.objects.order_by('name')
        self.fields['starting_price'].help_text = 'Prezzo iniziale dell\'asta'
        self.fields['reserve_price'].help_text = 'Prezzo minimo per vincere (opzionale)'
        self.fields['bid_increment'].help_text = 'Incremento minimo per ogni nuova offerta'
    
    def clean(self):
        cleaned_data = super().clean()
        if not self.cleaned_data.get('image_1_file'):
            raise ValidationError("È necessario caricare almeno l'immagine principale.")
        return cleaned_data
    
    def save(self, commit=True):
        auction = super().save(commit=False)
        
        if self.cleaned_data.get('image_1_file'):
            auction.set_image_1(self.cleaned_data['image_1_file'])
        if self.cleaned_data.get('image_2_file'):
            auction.set_image_2(self.cleaned_data['image_2_file'])
        if self.cleaned_data.get('image_3_file'):
            auction.set_image_3(self.cleaned_data['image_3_file'])
        
        if commit:
            auction.save()
        return auction


# Backwards compatibility alias
LotteryCreationForm = AuctionCreationForm
