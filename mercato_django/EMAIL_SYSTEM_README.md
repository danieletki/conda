# Sistema Notifiche Email - MercatoPro

## Panoramica

Il sistema di notifiche email per MercatoPro fornisce un'infrastruttura completa per l'invio automatizzato di email transazionali con template responsive HTML, retry logic e tracking completo.

## Template Email Implementati

### 1. **Registrazione Utente** (`registration.html`)
- **Trigger**: Nuovo utente registrato
- **Destinatario**: Nuovo utente
- **Priorità**: Normale
- **Contenuto**: Benvenuto, dati accesso, spiegazione piattaforma, promemoria KYC

### 2. **KYC Approvato** (`kyc_approved.html`)
- **Trigger**: Verifica KYC completata con successo
- **Destinatario**: Utente approvato
- **Priorità**: Alta
- **Contenuto**: Conferma approvazione, nuove funzionalità disponibili, call-to-action

### 3. **KYC Rifiutato** (`kyc_rejected.html`)
- **Trigger**: Verifica KYC fallita
- **Destinatario**: Utente rifiutato
- **Priorità**: Alta
- **Contenuto**: Motivo rifiuto, istruzioni per nuovo invio, documenti accettati

### 4. **Lotteria Attivata** (`lottery_activated.html`)
- **Trigger**: Lotteria passa a status 'active'
- **Destinatario**: Venditore della lotteria
- **Priorità**: Normale
- **Contenuto**: Conferma attivazione, dettagli lotteria, suggerimenti successo

### 5. **Biglietto Acquistato** (`ticket_purchased.html`)
- **Trigger**: Pagamento biglietto completato
- **Destinatario**: Acquirente
- **Priorità**: Normale
- **Contenuto**: Conferma acquisto, numero biglietto, dettagli lotteria, spiegazione processo

### 6. **Vincita Lotteria** (`lottery_won.html`)
- **Trigger**: Estrazione completata - utente vincente
- **Destinatario**: Vincitore
- **Priorità**: Urgente
- **Contenuto**: Congratulazioni, dettagli premio, procedure ritiro, contatti venditore

### 7. **Notifica Venditore** (`seller_winner_notification.html`)
- **Trigger**: Estrazione completata - notifica al venditore
- **Destinatario**: Venditore
- **Priorità**: Alta
- **Contenuto**: Dettagli vincitore, azioni richieste, template contatto

### 8. **Perdita Lotteria** (`lottery_lost.html`) [Opzionale]
- **Trigger**: Estrazione completata - non vincente
- **Destinatario**: Acquirenti non vincenti
- **Priorità**: Bassa
- **Contenuto**: Risultato estrazione, incoraggiamento, prossime lotterie

### 9. **Promemoria Scadenza** (`expiration_reminder.html`)
- **Trigger**: Task cron - lotterie in scadenza
- **Destinatario**: Utenti interessati
- **Priorità**: Normale
- **Contenuto**: Scadenza imminente, countdown, call-to-action

## Configurazione SMTP

### Settings Requiti in `settings.py`:

```python
# Email Configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'  # o altro provider SMTP
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-app-password'
DEFAULT_FROM_EMAIL = 'noreply@mercato.pro'
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# Email retry configuration
EMAIL_RETRY_ATTEMPTS = 3
EMAIL_RETRY_DELAY = 60  # seconds

# Site URL for templates
SITE_URL = 'https://your-domain.com'
```

### Provider SMTP Consigliati:

1. **Gmail**: 
   - Host: `smtp.gmail.com`
   - Porta: `587`
   - Richiede App Password per sicurezza

2. **SendGrid**:
   - Host: `smtp.sendgrid.net`
   - Porta: `587`
   - API Key come password

3. **Mailgun**:
   - Host: `smtp.mailgun.org`
   - Porta: `587`
   - Credenziali specifiche Mailgun

## Testing del Sistema

### 1. **Configurazione Ambiente di Test**

```python
# settings.py - Modalità test
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Per logging in console
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'mercato_notifications': {
            'handlers': ['console'],
            'level': 'INFO',
        },
    },
}
```

### 2. **Test Manuale Email**

```python
from mercato_notifications.email_service import send_registration_email
from mercato_accounts.models import CustomUser

# Crea utente di test
user = CustomUser.objects.create_user(
    username='testuser',
    email='test@example.com',
    password='testpass123'
)

# Invia email test
send_registration_email(user)
```

### 3. **Test Signal Automatici**

```python
# Test registrazione utente
from django.contrib.auth import get_user_model
User = get_user_model()
new_user = User.objects.create_user('testuser2', 'test2@example.com')

# Test creazione lotteria
from mercato_lotteries.models import Lottery
lottery = Lottery.objects.create(
    title="Test Lottery",
    description="Test Description", 
    item_value=100.00,
    items_count=10,
    seller=new_user
)
lottery.status = 'active'
lottery.save()

# Test acquisto biglietto
ticket = LotteryTicket.objects.create(
    lottery=lottery,
    buyer=new_user,
    payment_status='completed'
)
```

### 4. **Monitoraggio Email Log**

Accedere all'admin Django per monitorare:
- `/admin/mercato_notifications/emaillog/`
- Filtrare per status, template, data
- Visualizzare retry di email fallite
- Eseguire retry manuale

## Admin Interface

### Email Log Management

L'admin interface fornisce:

1. **Lista Email**: 
   - Filtro per status (pending, sent, failed, etc.)
   - Filtro per template utilizzato
   - Ricerca per email utente o subject

2. **Azioni Batch**:
   - Retry email fallite
   - Marca come consegnate
   - Marca come fallite

3. **Dettagli Email**:
   - Subject e contenuto
   - Template context (JSON)
   - Errori di invio
   - Retry count

### Management Commands

```bash
# Invia promemoria scadenza
python manage.py send_expiration_reminders

# Retry email fallite
python manage.py retry_failed_emails
```

## Retry Logic

Il sistema implementa retry automatico per email fallite:

- **Tentativi massimi**: 3 (configurabile)
- **Delay**: 60 secondi tra tentativi (configurabile)
- **Backoff**: Esponenziale (60s, 120s, 180s)
- **Status tracking**: pending → retry → failed/sent

## Ottimizzazioni Implementate

1. **Template Rendering**: Cache dei template per performance
2. **Database Indexes**: Query ottimizzate per log email
3. **Priority Queue**: Email urgenti inviate per prime
4. **Error Handling**: Logging completo errori
5. **User Preferences**: Rispetto preferenze notifiche utente

## Sicurezza

1. **Input Validation**: Sanitizzazione template context
2. **Rate Limiting**: Prevenzione spam
3. **Email Verification**: Verifica indirizzi email
4. **Secure Headers**: Security headers email HTML

## Monitoraggio

Metriche importanti da monitorare:
- Tasso di successo invio email
- Tempo medio di consegna  
- Errori più comuni
- Utilizzo template
- Retry effectiveness

## Troubleshooting

### Email non inviate:
1. Controllare configurazione SMTP
2. Verificare log Django
3. Controllare EmailLog in admin
4. Testare connettività SMTP

### Template errori:
1. Verificare sintassi HTML template
2. Controllare variabili template
3. Testare rendering manuale

### Performance:
1. Monitorare tempo rendering template
2. Controllare query database
3. Verificare sizing queue email

## Prossimi Miglioramenti

1. **Email Analytics**: Tracking aperture e click
2. **A/B Testing**: Test diverse versioni template
3. **Localization**: Supporto multiple lingue
4. **Advanced Scheduling**: Email programmate
5. **Integration**: Webhook per servizi esterni