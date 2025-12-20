#!/bin/bash
set -e

# Script di entrypoint per MercatoPro Docker container

echo "🚀 Avvio MercatoPro Docker container..."

# Funzione per attendere che il database sia disponibile
wait_for_db() {
    echo "⏳ Attesa database PostgreSQL..."
    python -c "
import sys
import time
import psycopg2
from decouple import config

retries = 30
while retries > 0:
    try:
        conn = psycopg2.connect(
            host=config('DB_HOST', default='db'),
            database=config('DB_NAME', default='mercato_db'),
            user=config('DB_USER', default='mercato_user'),
            password=config('DB_PASSWORD', default='mercato_password'),
            port=config('DB_PORT', default='5432')
        )
        conn.close()
        print('✅ Database PostgreSQL disponibile!')
        break
    except psycopg2.OperationalError:
        print(f'⏳ Database non ancora disponibile. Tentativi rimanenti: {retries}')
        time.sleep(2)
        retries -= 1
        if retries == 0:
            print('❌ Database non disponibile dopo 30 tentativi')
            sys.exit(1)
    except Exception as e:
        print(f'❌ Errore di connessione database: {e}')
        sys.exit(1)
"
}

# Funzione per attendere Redis
wait_for_redis() {
    echo "⏳ Attesa Redis..."
    python -c "
import sys
import time
import redis
from decouple import config

retries = 15
while retries > 0:
    try:
        r = redis.Redis(
            host=config('REDIS_HOST', default='redis'),
            port=config('REDIS_PORT', default='6379'),
            db=0,
            socket_timeout=3
        )
        r.ping()
        print('✅ Redis disponibile!')
        break
    except redis.ConnectionError:
        print(f'⏳ Redis non ancora disponibile. Tentativi rimanenti: {retries}')
        time.sleep(2)
        retries -= 1
        if retries == 0:
            print('❌ Redis non disponibile dopo 15 tentativi')
            sys.exit(1)
    except Exception as e:
        print(f'❌ Errore di connessione Redis: {e}')
        sys.exit(1)
"
}

# Attendi servizi esterni
if [ "$SKIP_SERVICE_CHECKS" != "true" ]; then
    wait_for_db
    wait_for_redis
fi

echo "🔧 Esecuzione migrazioni Django..."
python manage.py migrate --noinput || {
    echo "❌ Errore durante le migrazioni"
    exit 1
}

echo "📦 Raccolta file statici..."
python manage.py collectstatic --noinput || {
    echo "❌ Errore durante collectstatic"
    exit 1
}

echo "🌱 Creazione superuser se non esiste..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser(
        username='admin',
        email='admin@mercato.pro',
        password='admin123'
    )
    print('✅ Superuser admin creato con password: admin123')
else:
    print('✅ Superuser admin già esistente')
" || echo "⚠️  Non è stato possibile creare il superuser"

# Controlla se è un worker Celery o il server web
if [ "$1" = "celery" ]; then
    echo "🐝 Avvio Celery worker..."
    exec celery -A mercatopro worker --loglevel=info
elif [ "$1" = "beat" ]; then
    echo "🕐 Avvio Celery beat scheduler..."
    exec celery -A mercatopro beat --loglevel=info
else
    echo "🚀 Avvio server Django..."
    exec python manage.py runserver 0.0.0.0:8000
fi