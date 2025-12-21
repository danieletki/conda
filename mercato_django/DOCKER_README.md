# MercatoPro Docker Setup - README

Questo documento spiega come configurare e avviare MercatoPro utilizzando Docker e docker-compose.

## 📋 Prerequisiti

- Docker Engine 20.10+
- Docker Compose 2.0+
- Almeno 4GB di RAM disponibili
- Porte libere: 80, 443, 5432, 6379, 8000

## 🚀 Avvio Rapido

### 1. Clonazione e Setup Iniziale

```bash
# Vai alla directory del progetto
cd mercato_django

# Copia il file di configurazione ambiente
cp .env.example .env

# Modifica il file .env se necessario (password, chiavi, ecc.)
```

### 2. Avvio dei Servizi

```bash
# Avvia tutti i servizi
docker-compose up -d

# O con il Makefile (se disponibile)
make build # Per costruire le immagini
make up
make seed  # Per popolare il database con dati di test
```

### 3. Verifica dello Stato

```bash
# Visualizza lo stato dei container
docker-compose ps

# Visualizza i log
docker-compose logs -f

# Log di un servizio specifico
docker-compose logs -f web
```

### 4. Accesso all'Applicazione

- **Applicazione Web**: http://localhost
- **Admin Django**: http://localhost/admin
- **Database PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

**Credenziali Default Admin:**
- Username: `admin`
- Password: `admin123`

## 🏗️ Architettura dei Servizi

Il setup Docker include i seguenti servizi:

### Servizi Core
- **db**: PostgreSQL 15 (porta 5432)
- **redis**: Redis 7 (porta 6379)
- **web**: Django Application (porta 8000)
- **nginx**: Reverse Proxy (porte 80/443)

### Servizi Celery
- **celery-worker**: Worker per task asincroni
- **celery-beat**: Scheduler per task periodici

## 📁 Struttura File Docker

```
mercato_django/
├── Dockerfile                 # Image Django custom
├── docker-compose.yml         # Configurazione servizi
├── .dockerignore              # File esclusi dal build
├── docker/
│   ├── entrypoint.sh          # Script avvio container
│   ├── nginx/
│   │   ├── nginx.conf         # Configurazione Nginx
│   │   └── default.conf       # Site configuration
│   └── postgres/
│       └── init/
│           └── 01_init.sql    # Inizializzazione DB
├── .env.example               # Template configurazione
├── .env.docker                # Config per Docker
└── requirements.txt           # Dipendenze Python
```

## ⚙️ Configurazione Environment

### Variabili Principali

| Variabile | Default | Descrizione |
|-----------|---------|-------------|
| `DEBUG` | 1 | Modalità debug Django |
| `SECRET_KEY` | - | Chiave segreta Django |
| `DB_NAME` | mercato_db | Nome database PostgreSQL |
| `DB_USER` | mercato_user | Utente database |
| `DB_PASSWORD` | mercato_password | Password database |
| `REDIS_PASSWORD` | redis_password | Password Redis |
| `ALLOWED_HOSTS` | * | Host autorizzati |

### Configurazione Produzione

Per la produzione, modificare `.env`:

```bash
DEBUG=0
SECRET_KEY=your-very-secure-secret-key
ALLOWED_HOSTS=yourdomain.com
# Altri settings di sicurezza...
```

## 🔧 Comandi Utili

### Gestione Container

```bash
# Avvia tutti i servizi
docker-compose up -d

# Ferma tutti i servizi
docker-compose down

# Ferma e rimuovi volumi
docker-compose down -v

# Rebuild immagini
docker-compose build

# Riavvia servizio specifico
docker-compose restart web

# Aggiorna e riavvia
docker-compose pull && docker-compose up -d
```

### Gestione Database

```bash
# Accedi al database
docker-compose exec db psql -U mercato_user -d mercato_db

# Backup database
docker-compose exec db pg_dump -U mercato_user mercato_db > backup.sql

# Restore database
docker-compose exec -T db psql -U mercato_user mercato_db < backup.sql
```

### Gestione Django

```bash
# Esegui migrazioni
docker-compose exec web python manage.py migrate

# Popola dati di test
make seed

# Crea superuser
docker-compose exec web python manage.py createsuperuser

# Shell Django
docker-compose exec web python manage.py shell

# Collectstatic
docker-compose exec web python manage.py collectstatic

# Test
docker-compose exec web python manage.py test
```

### Nginx (Reverse Proxy)

```bash
# Verifica sintassi configurazione Nginx
docker-compose exec nginx nginx -t

# Reload configurazione Nginx (zero downtime)
docker-compose exec nginx nginx -s reload

# View Nginx logs
docker-compose logs -f nginx

# Access log real-time
docker-compose exec nginx tail -f /var/log/nginx/access.log

# Test health endpoint
curl http://localhost/health
```

### Logs e Debug

```bash
# Log in tempo reale
docker-compose logs -f

# Log servizio specifico
docker-compose logs -f web

# Log ultimi 100 righe
docker-compose logs --tail=100 web

# Statistiche risorse
docker stats
```

## 🚨 Risoluzione Problemi

### Problemi Comuni

#### 1. Container non si avvia
```bash
# Controlla i log
docker-compose logs [servizio]

# Verifica porte occupate
netstat -tulpn | grep :8000
```

#### 2. Errori di database
```bash
# Verifica stato PostgreSQL
docker-compose exec db pg_isready -U mercato_user

# Reset completo database
docker-compose down -v
docker-compose up -d db
```

#### 3. Problemi di permessi
```bash# Rimuovi e ricrea volumi
docker-compose down -v
docker system prune -f
docker-compose up -d
```

#### 4. Problemi di memoria
```bash
# Verifica uso memoria
docker stats --no-stream

# Aggiungi swap se necessario
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### Health Checks

Ogni servizio ha health check configurati. Per verificare:

```bash
# Status dettagliato
docker-compose ps

# Health check specifico
docker inspect --format='{{.State.Health.Status}}' mercatopro_web
```

## 🔒 Sicurezza

### Best Practices Implementate

- **Utente non-root** nei container
- **Secrets** tramite environment variables
- **Network isolati** tra servizi
- **Rate limiting** su API e login
- **Security headers** configurati in Nginx
- **SSL/TLS** supportato (configurare certificati)

### Configurazione SSL

Per abilitare HTTPS, aggiungere certificati in `docker/nginx/ssl/`:

```bash
# Crea directory SSL
mkdir -p docker/nginx/ssl

# Copia certificati
cp your-domain.crt docker/nginx/ssl/
cp your-domain.key docker/nginx/ssl/

# Aggiorna configurazione Nginx per HTTPS
```

## 📈 Monitoring

### Logs Strutturati

Tutti i servizi utilizzano logging JSON per migliore analisi:

```bash
# Log con formato JSON
docker-compose logs -f --no-color web | jq .
```

### Metriche

Per il monitoring avanzato, considerare integrazione con:
- Prometheus + Grafana
- ELK Stack
- Sentry per error tracking

## 🔄 Aggiornamenti

### Update Applicazione

```bash
# Pull nuove immagini
docker-compose pull

# Rebuild con nuove dipendenze
docker-compose build --no-cache

# Update con zero downtime
docker-compose up -d
```

## 🌐 Nginx Reverse Proxy

Per documentazione dettagliata della configurazione Nginx, inclusa sicurezza, rate limiting, caching, e performance tuning, vedi [NGINX_README.md](./NGINX_README.md).

### Verifica Reverse Proxy

```bash
# Verifica che Nginx passeggi correttamente le richieste a Django
curl -v http://localhost/admin/

# Verifica static files serviti da Nginx
curl -I http://localhost/static/admin/css/base.css

# Verifica media files
curl -I http://localhost/media/

# Verifica security headers
curl -I http://localhost/ | grep -E "X-Frame|X-Content-Type|CSP"

# Verifica gzip compression
curl -H "Accept-Encoding: gzip" -I http://localhost/static/admin/css/base.css | grep Content-Encoding
```

## 📚 Risorse Aggiuntive

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Django Deployment Guide](https://docs.djangoproject.com/en/4.2/howto/deployment/)
- [Celery Documentation](https://celery.readthedocs.io/)
- [Nginx Configuration](https://nginx.org/en/docs/)
- [Nginx Reverse Proxy README](./NGINX_README.md) - Configurazione dettagliata

## 🆘 Supporto

Per problemi o domande:
1. Controllare i log: `docker-compose logs`
2. Verificare risorse sistema
3. Consultare la documentazione ufficiale
4. Creare issue nel repository

---

**Nota**: Ricordarsi di cambiare le password default e la SECRET_KEY in produzione!