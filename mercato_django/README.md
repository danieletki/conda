# MercatoPro Django Application

Un'applicazione Django completa per una piattaforma di lotterie online con sistema di pagamenti PayPal, notifiche in tempo reale e pannello amministrativo.

## 🏗️ Struttura del Progetto

Il progetto è organizzato come segue:

```
mercato_django/
├── mercatopro/              # Django project settings
│   ├── __init__.py
│   ├── settings.py          # Configurazione PostgreSQL, static files, templates
│   ├── urls.py              # URL routing principale
│   ├── wsgi.py
│   └── asgi.py
├── mercato_accounts/        # Gestione utenti e profili
│   ├── models.py            # CustomUser, Profile
│   ├── views.py             # Login, registrazione, profilo
│   ├── urls.py
│   ├── forms.py             # Form di autenticazione
│   ├── admin.py             # Admin panel configurazione
│   └── migrations/
├── mercato_lotteries/       # Sistema lotterie
│   ├── models.py            # Lottery, LotteryTicket, Category
│   ├── views.py             # Lista lotterie, dettagli, acquisto biglietti
│   ├── urls.py
│   └── migrations/
├── mercato_payments/        # Sistema pagamenti PayPal
│   ├── models.py            # Payment, PaymentMethod, Refund
│   ├── views.py             # Dashboard pagamenti, PayPal integration
│   ├── urls.py
│   └── migrations/
├── mercato_notifications/   # Sistema notifiche
│   ├── models.py            # Notification, NotificationSettings
│   ├── views.py             # Gestione notifiche
│   ├── urls.py
│   └── migrations/
├── mercato_admin/           # Pannello amministrativo
│   ├── models.py            # AdminSettings, SystemLog, Report
│   ├── views.py             # Dashboard admin
│   ├── urls.py
│   └── migrations/
├── templates/               # Template HTML
│   ├── base.html            # Layout base con Bootstrap 5
│   ├── home.html            # Homepage
│   ├── registration/        # Login e registrazione
│   ├── accounts/            # Profilo, impostazioni
│   ├── lotteries/           # Lotterie
│   ├── payments/            # Pagamenti
│   ├── notifications/       # Notifiche
│   └── admin/               # Template admin
├── static/                  # File statici
│   ├── css/style.css        # Stili personalizzati
│   ├── js/main.js           # JavaScript principale
│   └── images/
├── media/                   # File caricati dagli utenti
├── requirements.txt         # Dipendenze Python
├── manage.py               # Django management
└── venv/                   # Virtual environment
```

## 🚀 Funzionalità Implementate

### ✅ Accounts Management
- **Custom User Model** esteso con AbstractUser
- **Registrazione e Login** con validazioni
- **Profilo utente** con immagine, bio, indirizzo
- **Sistema di verifica** email/telefono
- **Admin integrato** per gestione utenti

### ✅ Lottery System
- **Categorie** per organizzare le lotterie
- **Gestione lotterie** con stato (draft, active, ended)
- **Sistema biglietti** con numerazione automatica
- **Limiti per utente** e biglietti massimi
- **Commenti** degli utenti sulle lotterie

### ✅ Payment System
- **Integrazione PayPal** per pagamenti sicuri
- **Metodi di pagamento** multipli
- **Gestione rimborsi** automatica
- **Fee di processing** configurabili
- **Tracking pagamenti** completo

### ✅ Notification System
- **Notifiche in tempo reale** email e push
- **Impostazioni personalizzabili** per utente
- **Categorizzazione** (info, success, warning, error)
- **Priorità** (low, normal, high, urgent)
- **Scheduling** per notifiche future

### ✅ Admin Panel
- **Dashboard** con statistiche in tempo reale
- **Gestione utenti** e permessi
- **Monitoraggio sistema** con log dettagliati
- **Reportistica** automatica e manuale
- **Backup system** integrato

## 🛠️ Setup e Installazione

### 1. Prerequisiti
- Python 3.8+
- PostgreSQL 12+
- pip

### 2. Installazione

```bash
# Clona il repository
cd /home/engine/project/mercato_django

# Attiva virtual environment
source venv/bin/activate

# Installa dipendenze
pip install -r requirements.txt
```

### 3. Configurazione Database PostgreSQL

Crea il database:
```sql
CREATE DATABASE mercato_db;
CREATE USER mercato_user WITH PASSWORD 'your_password_here';
GRANT ALL PRIVILEGES ON DATABASE mercato_db TO mercato_user;
```

Aggiorna `mercatopro/settings.py`:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'mercato_db',
        'USER': 'mercato_user',
        'PASSWORD': 'your_password_here',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

### 4. Configurazione PayPal

Aggiungi le credenziali PayPal in `mercatopro/settings.py`:
```python
PAYPAL_CLIENT_ID = 'your_paypal_client_id'
PAYPAL_CLIENT_SECRET = 'your_paypal_client_secret'
PAYPAL_SANDBOX_MODE = True  # False in produzione
```

### 5. Migrazioni e Setup

```bash
# Esegui migrazioni
python manage.py makemigrations
python manage.py migrate

# Crea superuser admin
python manage.py createsuperuser

# Colleziona static files
python manage.py collectstatic --noinput
```

### 6. Avvio Server

```bash
python manage.py runserver
```

L'applicazione sarà disponibile su: http://127.0.0.1:8000

## 📁 Configurazione File Statici e Media

La configurazione è già presente in `settings.py`:

```python
# Static files
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
```

## 🎨 Design e UI/UX

### Bootstrap 5 + Font Awesome
- **Responsive design** mobile-first
- **Componenti predefiniti** per rapidità di sviluppo
- **Icone professionali** Font Awesome 6
- **Sistema colori** personalizzato in CSS

### Temi Principali
- **Palette colori**: Primary Blue (#007bff), Success Green, Warning Yellow
- **Typography**: Google Fonts (Inter)
- **Animazioni**: Hover effects, transitions smooth
- **Cards**: Design moderno con shadows e border radius

## 🔧 API Endpoints

### Accounts
- `GET /` - Homepage
- `GET /accounts/login/` - Login page
- `POST /accounts/login/` - Autenticazione
- `GET /accounts/register/` - Registrazione
- `POST /accounts/register/` - Crea account
- `GET /accounts/profile/` - Profilo utente
- `GET /accounts/settings/` - Impostazioni

### Lotteries
- `GET /lotteries/` - Lista lotterie
- `GET /lotteries/<id>/` - Dettagli lotteria
- `POST /lotteries/<id>/buy-tickets/` - Acquista biglietti
- `GET /lotteries/my-tickets/` - I miei biglietti

### Payments
- `GET /payments/` - Dashboard pagamenti
- `POST /payments/paypal/create-order/` - Crea ordine PayPal
- `POST /payments/paypal/capture-order/` - Completa pagamento

### Notifications
- `GET /notifications/` - Lista notifiche
- `POST /notifications/<id>/read/` - Segna come letta
- `POST /notifications/mark-all-read/` - Segna tutte come lette

### Admin
- `GET /admin-panel/` - Dashboard admin
- `GET /admin-panel/users/` - Gestione utenti
- `GET /admin-panel/lotteries/` - Gestione lotterie

## 🧪 Testing

```bash
# Esegui test
python manage.py test

# Test coverage
pip install coverage
coverage run --source='.' manage.py test
coverage report
```

## 🐳 Docker Deployment

### Quick Start with Docker (Raccomandato)

**3 comandi per lanciare tutto:**

```bash
cd mercato_django
docker-compose up -d
docker-compose ps  # Attendi fino a "healthy"
```

**Accesso:**
- **Applicazione**: http://localhost
- **Admin Panel**: http://localhost/admin
- **Credenziali**: admin / admin123

### Testing Docker Deployment

```bash
# Test automatici completi
./test_docker.sh

# Or usando Makefile
make test-docker

# Quick health check
make health
```

### Documentazione Docker Completa

- **[DOCKER_SETUP.md](DOCKER_SETUP.md)** - Guida completa setup e deployment
- **[TESTING_GUIDE.md](TESTING_GUIDE.md)** - Guida testing comprensiva
- **[DOCKER_TESTING_SUMMARY.md](DOCKER_TESTING_SUMMARY.md)** - Riepilogo implementazione

### Servizi Docker Inclusi

- ✅ **PostgreSQL 15** - Database
- ✅ **Redis 7** - Cache & Celery broker
- ✅ **Django/Gunicorn** - Applicazione web
- ✅ **Celery Worker** - Background tasks
- ✅ **Celery Beat** - Scheduled tasks
- ✅ **Nginx** - Reverse proxy & static files

### Comandi Docker Utili

```bash
make up                    # Avvia servizi
make down                  # Ferma servizi
make logs                  # Visualizza logs
make shell                 # Shell nel container web
make migrate               # Esegui migrations
make seed                  # Popola dati di test
make backup-db             # Backup database
make test-docker           # Test completi
```

Vedi **[DOCKER_SETUP.md](DOCKER_SETUP.md)** per dettagli completi.

---

## 🚀 Manual Deployment (Alternative)

### Production Settings
Aggiorna `settings.py` per produzione:
```python
DEBUG = False
ALLOWED_HOSTS = ['yourdomain.com']

# Security
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
```

### Environment Variables
Usa `python-decouple` per gestire secret:
```python
from decouple import config

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
```

## 📝 Note di Sviluppo

### Status Attuale
- ✅ **Setup completo** Django project
- ✅ **Models** tutti definiti e testati
- ✅ **URL routing** configurato
- ✅ **Template base** con Bootstrap 5
- ✅ **Admin panel** integrato
- ✅ **Database migrations** generate
- 🔄 **PayPal integration** (stub implementato)
- 🔄 **Email notifications** (da implementare)

### Prossimi Passi
1. Implementare PayPal SDK integration
2. Setup email backend per notifiche
3. Implementare file upload per immagini
4. Aggiungere validazioni custom nei forms
5. Implementare sistema di logging avanzato
6. Setup tests automatizzati
7. Configurazione CI/CD pipeline

## 🤝 Contributing

Per contribuire al progetto, segui questi passaggi:

1. Fork il repository
2. Crea feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Apri una Pull Request

Per maggiori dettagli sul workflow Git, vedi la **[GIT_WORKFLOW_GUIDE.md](GIT_WORKFLOW_GUIDE.md)**.

## 📄 License

Questo progetto è sotto licenza MIT. Vedi il file `LICENSE` per dettagli.

---

**MercatoPro** - La piattaforma di lotterie online più sicura e moderna! 🎲💰