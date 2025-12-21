# Nginx Reverse Proxy Configuration

Questo documento descrive la configurazione di Nginx come reverse proxy per l'applicazione Django in Docker.

## 📋 Sommario Configurazione

### 🏗️ Struttura Docker

#### Dockerfile (docker/nginx/Dockerfile)
- **Base Image**: `nginx:1.25-alpine` - Immagine leggera e sicura di Nginx
- **Utilità**: Installa `curl` per health checks
- **Configurazioni**: Copia nginx.conf e default.conf
- **Directories**: Crea directory necessarie per cache e log
- **Health Check**: Curl check su endpoint `/health`

#### Configurazione Nginx (docker/nginx/nginx.conf)
Configurazione principale di Nginx con:

1. **Worker Processes**
   - `worker_processes auto` - Numero di worker automatico (una per CPU)
   - `worker_rlimit_nofile 65535` - Limite file descriptor
   - `worker_connections 2048` - Connessioni simultanee per worker
   - Performance: `epoll` + `multi_accept` per throughput massimo

2. **Logging**
   - **Main log format**: Include request time, upstream response times
   - **Cache log format**: Separato per monitoraggio cache status
   - **Files**: `/var/log/nginx/access.log` e `/var/log/nginx/error.log`

3. **Gzip Compression**
   - **Compression**: Attivata per ridurre banda (~60% per assets)
   - **Level**: 6 (balance tra compressione e CPU)
   - **Min size**: 1024 bytes (non comprimere file troppo piccoli)
   - **Types**: CSS, JS, JSON, SVG, Fonts, XML, ecc.

4. **Rate Limiting (DDoS Protection)**
   - **API Zone**: 10 req/s per IP (burst 20)
   - **Login Zone**: 1 req/s per IP (burst 5) - Brute force protection
   - **General Zone**: 50 req/s per IP (burst 50)
   - **Connection Limit**: 10 connessioni simultanee per IP

5. **Timeouts**
   - Client body timeout: 12s
   - Client header timeout: 12s
   - Send timeout: 10s
   - Keepalive timeout: 15s (tra client e nginx)
   - Upstream keepalive: 60s (tra nginx e Django)

6. **Performance**
   - `sendfile on` - Zero-copy file transfer
   - `tcp_nopush on` - Invia header completo prima del corpo
   - `tcp_nodelay on` - Disabilita Nagle per bassa latenza
   - Upstream keepalive: 32 connessioni, 100 richieste per connessione

7. **Caching**
   - **Static Cache**: 1GB zone, 60 minuti inattività
   - **Content Cache**: 5GB zone, 30 minuti inattività
   - **Cache Lock**: Previene thundering herd problem

#### Virtual Host (docker/nginx/conf.d/default.conf)
Configurazione del server virtuale con:

##### 🔒 Security Headers
```nginx
X-Frame-Options: DENY               # Anti-clickjacking
X-Content-Type-Options: nosniff     # Anti-MIME sniffing
X-XSS-Protection: 1; mode=block     # Anti-XSS (browser legacy)
Referrer-Policy: strict-origin-when-cross-origin
Content-Security-Policy: ...        # Whitelist risorse
Permissions-Policy: ...             # Controlla feature browser
```

##### 📁 Static Files (/static/)
- **Serving**: Nginx serve direttamente da filesystem
- **Caching**: 30 giorni per CSS/JS, 1 anno per immagini/font
- **Gzip**: Attivato automaticamente via nginx.conf
- **CORS**: Headers per cross-origin requests
- **Security**: Nessun esecuzione script, cache immutable

##### 📸 Media Files (/media/)
- **Serving**: Nginx serve upload utenti
- **Caching**: 7 giorni
- **Security**: Blocca esecuzione di script (PHP, JSP, ecc.)
- **Protection**: Nega accesso a file eseguibili

##### 🔌 API Endpoints (/api/)
- **Rate Limiting**: 10 req/s per IP
- **Proxy**: Passa a Django app su porta 8000
- **Headers**: Inoltra X-Real-IP, X-Forwarded-For, ecc.
- **Buffering**: Abilitato con buffer 4k/8k
- **Timeouts**: 60s per connect, send, read
- **WebSocket**: Supporto per upgrade connection

##### 🔐 Authentication (/login, /register, /password-reset, etc.)
- **Rate Limiting**: Rigida (1 req/s) - Brute force protection
- **Connection Limit**: 5 connessioni simultanee
- **Security Headers**: Addizionali per proteggere credenziali
- **Proxy**: Forward a Django con protezioni extra

##### 🛡️ Admin Panel (/admin/)
- **Rate Limiting**: Rigida come authentication
- **Access Control**: Limitato a IP fiduciosi (opzionale)
- **Proxy**: Forward a Django

##### 🏠 Main Application (/)
- **Rate Limiting**: Moderata (50 req/s)
- **Cache Bypass**: POST requests, utenti autenticati
- **WebSocket Support**: Per Django Channels (se usato)
- **Connection Limit**: 20 simultanee per IP

##### 💚 Health Check
- **/health**: Endpoint semplice che ritorna 200 "healthy"
- **/health-full**: Connessione a Django per full healthcheck
- **Logging**: Disabilitato per ridurre noise

##### 🚫 Security Blocks
- **Hidden files**: Nega accesso a .git, .env, .htaccess, ecc.
- **Backup files**: Nega ~$ files
- **Sensitive files**: Blocca .git, .svn, env.php, etc.
- **Log files**: Nega accesso a cartelle .logs/

### 📊 Performance Optimizations

1. **Buffer Tuning**
   ```
   proxy_buffer_size: 4k
   proxy_buffers: 8x4k = 32k totale
   proxy_busy_buffers_size: 8k
   proxy_max_temp_file_size: 2m
   ```

2. **Keepalive Connections**
   - Django: 32 keepalive per 100 requests
   - Clients: 65 sec timeout, 100 requests
   - Upstream: 60 sec timeout, 100 requests

3. **Cache Strategy**
   - Static assets: Long TTL (30d - 1y)
   - Media: Medium TTL (7d)
   - API: No cache (bypass per POST/auth users)

4. **Compression**
   - Gzip con livello 6 (default efficiente)
   - Min 1KB size (non comprimere file piccoli)
   - Applicato a ~15 MIME types

## 🐳 Docker Integration

### Build & Run
```bash
# Build con Dockerfile
docker-compose build nginx

# Start container
docker-compose up -d nginx

# View logs
docker-compose logs -f nginx

# Test configuration
docker-compose exec nginx nginx -t
```

### Volumes
- **Config RO**: nginx.conf, default.conf (read-only)
- **Static RO**: /var/www/static da Django
- **Media RO**: /var/www/media da Django
- **Cache RW**: /var/cache/nginx per caching
- **Logs RW**: /var/log/nginx per log rotation

### Healthcheck
```yaml
test: ["CMD", "curl", "-f", "http://localhost/health"]
interval: 30s
timeout: 10s
retries: 3
start_period: 10s
```

## 🔧 Configurazione Avanzata

### SSL/TLS (HTTPS) - Produzione
Per abilitare HTTPS in produzione:

1. **Copia certificati** in `docker/nginx/ssl/`:
   - `docker/nginx/ssl/cert.pem` (certificate chain)
   - `docker/nginx/ssl/key.pem` (private key)

2. **Abilita in default.conf**:
```nginx
# Uncomment e modifica:
server {
    listen 80;
    server_name example.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    # HSTS header (uncomment in default.conf)
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    
    # ... rest of configuration
}
```

### Rate Limiting Personalizzato
Modificare le zone in nginx.conf:
```nginx
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;    # Default 10r/s
limit_req_zone $binary_remote_addr zone=login:10m rate=1r/s;   # Default 1r/s
limit_req_zone $binary_remote_addr zone=general:10m rate=50r/s; # Default 50r/s
```

Whitelist IP trusted (opzionale):
```nginx
geo $limit_api {
    default 1;
    127.0.0.1 0;           # localhost no limit
    10.0.0.0/8 0;          # private network no limit
    203.0.113.0/24 0;      # trusted IPs
}

map $limit_api $api_limit {
    0 "";
    1 $binary_remote_addr;
}

limit_req_zone $api_limit zone=api:10m rate=10r/s;
```

### Caching Avanzato
Aumentare cache per ambienti con molto traffic:

```nginx
# Nella sezione http di nginx.conf
proxy_cache_path /var/cache/nginx/static levels=1:2 keys_zone=static_cache:50m max_size=5g inactive=60m;
proxy_cache_path /var/cache/nginx/content levels=1:2 keys_zone=content_cache:100m max_size=10g inactive=30m;
```

### Monitoring & Logging

#### Accesso ai log
```bash
# Container logs in tempo reale
docker-compose logs -f nginx

# Log file access
docker-compose exec nginx tail -f /var/log/nginx/access.log

# Log file errors
docker-compose exec nginx tail -f /var/log/nginx/error.log

# Log file static
docker-compose exec nginx tail -f /var/log/nginx/static.log
```

#### Analisi log
```bash
# Top 10 indirizzi IP
docker-compose exec nginx awk '{print $1}' /var/log/nginx/access.log | sort | uniq -c | sort -rn | head -10

# Top 10 URL richiesti
docker-compose exec nginx awk '{print $7}' /var/log/nginx/access.log | sort | uniq -c | sort -rn | head -10

# Request time distribution
docker-compose exec nginx grep 'rt=' /var/log/nginx/access.log | awk -F'rt=' '{print $2}' | awk '{print $1}' | sort -n | tail -20
```

## ✅ Acceptance Criteria Verification

### 1. ✓ Nginx container avvia correttamente
```bash
docker-compose up -d nginx
docker-compose ps nginx
# Status: Up
```

### 2. ✓ Django requests passate a Django container
```bash
curl -v http://localhost/admin/
# Dovrebbe ricevere Django response, non errore Nginx
```

### 3. ✓ Static files serviti da Nginx (no Django)
```bash
curl -I http://localhost/static/css/style.css
# Header Cache-Control, X-Frame-Options, ecc. presenti
# Nginx serve direttamente da /var/www/static/
```

### 4. ✓ Media files accessibili
```bash
curl -I http://localhost/media/uploads/image.jpg
# Header Cache-Control presenti
# Nginx serve direttamente da /var/www/media/
```

### 5. ✓ Security headers presenti
```bash
curl -I http://localhost/
# Verificare presence di:
# X-Frame-Options: DENY
# X-Content-Type-Options: nosniff
# X-XSS-Protection: 1; mode=block
# Content-Security-Policy: ...
# Permissions-Policy: ...
```

### 6. ✓ Gzip compression attivo
```bash
curl -H "Accept-Encoding: gzip" -I http://localhost/static/css/style.css
# Header: Content-Encoding: gzip
```

### 7. ✓ Health check funzionante
```bash
docker-compose ps nginx
# Status: Up (healthy)

curl http://localhost/health
# Response: healthy
```

## 🐛 Troubleshooting

### Container non avvia
```bash
# Check build errors
docker-compose build --no-cache nginx

# Check container logs
docker-compose logs nginx

# Test nginx config
docker-compose exec nginx nginx -t
```

### Static files 404
```bash
# Verify volume mount
docker-compose exec nginx ls -la /var/www/static/

# Check Django collectstatic ran
docker-compose exec web python manage.py collectstatic --noinput

# Verify permissions
docker-compose exec nginx ls -la /var/www/
```

### Rate limiting bloccando traffic legittimo
```bash
# Verificare client IP è passato correttamente
curl -H "X-Forwarded-For: 1.2.3.4" http://localhost/
# Oppure controllare logs per X-Real-IP
```

### Performance lento
```bash
# Check nginx worker status
docker-compose exec nginx ps aux | grep nginx

# Check cache hit rate nei logs
docker-compose exec nginx grep 'cache=' /var/log/nginx/access.log | tail -20

# Monitor memory/CPU
docker stats nginx
```

## 📚 Risorse

- [Nginx Documentation](https://nginx.org/en/docs/)
- [Nginx Rate Limiting](https://nginx.org/en/docs/http/ngx_http_limit_req_module.html)
- [Nginx Caching](https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_cache)
- [HTTP Security Headers](https://owasp.org/www-project-secure-headers/)
- [CSP Reference](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP)
