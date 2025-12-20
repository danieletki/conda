# Dockerfile per MercatoPro
FROM python:3.11-slim

# Imposta variabili di ambiente
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/app" \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Crea utente non-root per sicurezza
RUN groupadd --gid 1000 mercato && \
    useradd --uid 1000 --gid mercato --shell /bin/bash --create-home mercato

# Installa dipendenze di sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    libjpeg-dev \
    libpng-dev \
    libfreetype6-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Crea directory di lavoro
WORKDIR /app

# Copia requirements e installa dipendenze Python
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copia il codice dell'applicazione
COPY . .

# Crea directory necessarie
RUN mkdir -p /app/staticfiles /app/media

# Cambia proprietà dei file
RUN chown -R mercato:mercato /app

# Switch all'utente non-root
USER mercato

# Esponi porta 8000
EXPOSE 8000

# Script di entrypoint
COPY docker/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]