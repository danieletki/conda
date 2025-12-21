# Nginx Production Configuration Guide

This guide covers configuring Nginx for production deployment with HTTPS, optimized security, and performance.

## 🔒 SSL/TLS Setup (HTTPS)

### 1. Generate Self-Signed Certificate (Development/Testing)

```bash
cd docker/nginx/ssl/

# Generate self-signed certificate valid for 365 days
openssl req -x509 -newkey rsa:4096 \
  -keyout key.pem \
  -out cert.pem \
  -days 365 \
  -nodes \
  -subj "/C=IT/ST=State/L=City/O=Organization/CN=example.com"

# Verify certificate
openssl x509 -in cert.pem -text -noout
```

### 2. Let's Encrypt Certificate (Production)

```bash
# Using Certbot with Docker
docker run --rm -it \
  -v /home/user/mercato_django/docker/nginx/ssl:/etc/letsencrypt \
  certbot/certbot certonly --standalone \
    -d example.com \
    -d www.example.com \
    --email admin@example.com \
    --agree-tos

# Copy certificates
cp /etc/letsencrypt/live/example.com/fullchain.pem docker/nginx/ssl/cert.pem
cp /etc/letsencrypt/live/example.com/privkey.pem docker/nginx/ssl/key.pem

# Auto-renewal
# Add to crontab: 0 2 1 * * certbot renew --quiet
```

### 3. Enable HTTPS in Nginx

Uncomment and modify in `docker/nginx/conf.d/default.conf`:

```nginx
# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name example.com www.example.com;
    return 301 https://$host$request_uri;
}

# HTTPS Server Block
server {
    listen 443 ssl http2;
    server_name example.com www.example.com;

    # SSL Configuration
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    
    # SSL Security
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5:!3DES;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_session_tickets off;
    
    # HSTS - Uncomment in default.conf
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    
    # ... rest of configuration (copy from HTTP block)
}
```

## 🔐 Production Security Hardening

### 1. Enhanced Security Headers

Uncomment in `docker/nginx/conf.d/default.conf`:

```nginx
# HSTS - Force HTTPS for 1 year (include in CSP preload list)
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;

# Restrict what sources can load resources
add_header Content-Security-Policy "default-src 'self'; script-src 'self' trusted-cdn.com; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self';" always;

# Prevent MIME type sniffing
add_header X-Content-Type-Options "nosniff" always;

# Prevent clickjacking
add_header X-Frame-Options "DENY" always;

# Enable XSS protection
add_header X-XSS-Protection "1; mode=block" always;

# Control referrer information
add_header Referrer-Policy "strict-origin-when-cross-origin" always;

# Restrict browser features
add_header Permissions-Policy "accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()" always;
```

### 2. Firewall Configuration

```bash
# Example with UFW (Ubuntu)
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable

# With iptables (advanced)
iptables -A INPUT -p tcp --dport 80 -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -j ACCEPT
iptables -A INPUT -p tcp --dport 22 -j ACCEPT
iptables -P INPUT DROP   # Default deny
```

### 3. Hide Nginx Version (Already Configured)

```nginx
server_tokens off;  # Already in nginx.conf
```

## 📊 Performance Optimization for Production

### 1. Increase Worker Processes

In `docker/nginx/nginx.conf`:

```nginx
# For high-traffic sites, use more workers
worker_processes 8;        # Or 'auto' for automatic detection
worker_rlimit_nofile 65536; # Increase file descriptor limit
worker_connections 4096;    # Increase concurrent connections per worker
```

### 2. Enable Brotli Compression (Optional)

Requires Nginx built with Brotli support:

```nginx
# In docker/nginx/nginx.conf http block
brotli on;
brotli_comp_level 6;
brotli_min_length 1024;
brotli_types
    text/plain
    text/css
    text/xml
    text/javascript
    application/json
    application/javascript
    application/xml+rss
    application/atom+xml
    image/svg+xml;
```

### 3. Optimize Cache Settings

```nginx
# Static cache - larger for high traffic
proxy_cache_path /var/cache/nginx/static levels=1:2 keys_zone=static_cache:50m max_size=10g inactive=60m;

# Content cache - very large for caching frequently accessed content
proxy_cache_path /var/cache/nginx/content levels=1:2 keys_zone=content_cache:100m max_size=50g inactive=30m;

# Cache lock to prevent stampede
proxy_cache_lock on;
proxy_cache_lock_timeout 5s;
proxy_cache_lock_age 10s;
```

### 4. Database Connection Pooling

For Django connections to Nginx:

```nginx
# Upstream configuration with keepalive
upstream django_app {
    server web:8000 weight=1 max_fails=3 fail_timeout=30s;
    # For multiple Django servers (load balancing):
    # server web1:8000 weight=1;
    # server web2:8000 weight=1;
    # server web3:8000 weight=1;
    
    keepalive 32;              # Connection pool size
    keepalive_timeout 60s;     # Keep connections alive for 60s
    keepalive_requests 100;    # Max requests per connection
}
```

### 5. Enable HTTP/2 and HTTP/3

```nginx
# In server block (with HTTPS)
listen 443 ssl http2;
# HTTP/3 requires special build
listen 443 quic reuseport;
add_header Alt-Svc 'h3=":443"; ma=86400';
```

## 🔄 Load Balancing (Multi-Server Setup)

```nginx
# In nginx.conf http block
upstream django_cluster {
    # IP hash for session persistence
    ip_hash;
    
    server web1.internal:8000 weight=2;
    server web2.internal:8000 weight=2;
    server web3.internal:8000 weight=1;  # Lower weight for smaller server
    
    # Health check endpoint
    check interval=3000 rise=2 fall=5 timeout=1000 type=http;
    check_http_send "GET /health HTTP/1.0\r\n\r\n";
    check_http_expect_alive http_2xx;
}
```

## 📈 Monitoring and Logging

### 1. Extended Logging for Analytics

```nginx
# In nginx.conf http block
log_format detailed '$remote_addr - $remote_user [$time_local] '
    '"$request" $status $body_bytes_sent '
    '"$http_referer" "$http_user_agent" '
    'rt=$request_time uct="$upstream_connect_time" '
    'uht="$upstream_header_time" urt="$upstream_response_time" '
    'gzip=$gzip_ratio';

access_log /var/log/nginx/access.log detailed buffer=32k flush=1m;
```

### 2. Separate Logs by Type

```nginx
# In server block
access_log /var/log/nginx/access.log main;
access_log /var/log/nginx/static.log static_log if=$static_request;
access_log /var/log/nginx/api.log api_log if=$api_request;

# Set request type variables
set $static_request 0;
set $api_request 0;

location /static/ {
    set $static_request 1;
    # ...
}

location /api/ {
    set $api_request 1;
    # ...
}
```

### 3. Log Rotation

```bash
# Create logrotate config: /etc/logrotate.d/nginx
/var/log/nginx/*.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    create 0640 nginx nginx
    sharedscripts
    postrotate
        [ ! -f /var/run/nginx.pid ] || kill -USR1 `cat /var/run/nginx.pid`
    endscript
}
```

### 4. Integration with Monitoring Tools

```nginx
# Expose metrics for Prometheus
location /metrics {
    stub_status on;
    access_log off;
    allow 127.0.0.1;  # Only local access
    allow 172.20.0.0/16;  # Docker network
    deny all;
}
```

## 🔧 Docker Deployment for Production

### 1. Update docker-compose.yml

```yaml
nginx:
    build:
        context: ./docker/nginx
        dockerfile: Dockerfile
    container_name: mercatopro_nginx
    restart: on-failure:5
    ports:
        - "80:80"
        - "443:443"
    volumes:
        - ./docker/nginx/nginx.conf:/etc/nginx/nginx.conf:ro
        - ./docker/nginx/conf.d/default.conf:/etc/nginx/conf.d/default.conf:ro
        - ./staticfiles:/var/www/static:ro
        - ./media:/var/www/media:ro
        - ./docker/nginx/ssl:/etc/nginx/ssl:ro
        - nginx_cache:/var/cache/nginx
        - nginx_logs:/var/log/nginx
        - /etc/letsencrypt:/etc/letsencrypt:ro  # For Let's Encrypt
    environment:
        - TZ=Europe/Rome
    networks:
        - mercato_network
    depends_on:
        web:
            condition: service_healthy
    healthcheck:
        test: ["CMD", "curl", "-f", "https://localhost/health"]
        interval: 30s
        timeout: 10s
        retries: 3
        start_period: 30s
    logging:
        driver: "json-file"
        options:
            max-size: "50m"
            max-file: "10"
    deploy:
        resources:
            limits:
                cpus: '2'
                memory: 1G
            reservations:
                cpus: '1'
                memory: 512M
```

### 2. Environment Variables for Production

```bash
# .env.production
DEBUG=0
SECRET_KEY=your-very-long-random-secret-key-generated-securely
ALLOWED_HOSTS=example.com,www.example.com
DB_HOST=db
DB_PASSWORD=your-secure-db-password
REDIS_PASSWORD=your-secure-redis-password
NGINX_HTTP_PORT=80
NGINX_HTTPS_PORT=443
```

## ✅ Production Checklist

- [ ] SSL certificate installed (Let's Encrypt or CA-signed)
- [ ] HTTPS enabled and HTTP redirects to HTTPS
- [ ] HSTS header enabled
- [ ] All security headers configured
- [ ] Rate limiting appropriate for traffic levels
- [ ] Cache settings optimized for your content
- [ ] Logging enabled and rotated
- [ ] Monitoring and alerting set up
- [ ] Firewall configured to only allow necessary ports
- [ ] Django DEBUG=False
- [ ] Django SECRET_KEY is strong and unique
- [ ] ALLOWED_HOSTS set to your domain
- [ ] Database backups automated
- [ ] SSL certificate renewal automated
- [ ] Nginx configuration tested in staging first
- [ ] Rollback plan documented
- [ ] Regular security updates scheduled
- [ ] DDoS protection enabled (CloudFlare, AWS Shield, etc.)
- [ ] CDN configured for static assets (optional)
- [ ] Backup and disaster recovery plan

## 🚀 Deployment Commands

```bash
# Pull latest code
git pull origin main

# Build new images
docker-compose -f docker-compose.yml build --no-cache

# Stop old containers
docker-compose down

# Start new containers
docker-compose up -d

# Run migrations
docker-compose exec web python manage.py migrate

# Collect static files
docker-compose exec web python manage.py collectstatic --noinput

# Check health
docker-compose ps
curl https://example.com/health

# View logs
docker-compose logs -f nginx
```

## 📞 Troubleshooting Production Issues

### High CPU Usage
```bash
# Check for slow queries
docker-compose logs web | grep "slow"

# Monitor in real-time
docker stats nginx web
```

### Memory Leaks
```bash
# Check memory growth over time
watch -n 60 'docker stats --no-stream'

# Restart container to reset
docker-compose restart web
```

### SSL Certificate Errors
```bash
# Check certificate validity
openssl x509 -in docker/nginx/ssl/cert.pem -text -noout

# Verify it matches private key
openssl x509 -noout -modulus -in docker/nginx/ssl/cert.pem | openssl md5
openssl rsa -noout -modulus -in docker/nginx/ssl/key.pem | openssl md5
# Both should output the same hash
```

### Rate Limiting Issues
```bash
# Check current rate limit status
curl -v http://example.com/api/
# Should see rate limiting headers in response

# Adjust limits if needed
# Edit docker/nginx/nginx.conf and redeploy
```

## 📚 Additional Resources

- [NGINX SSL Configuration](https://nginx.org/en/docs/http/ngx_http_ssl_module.html)
- [OWASP Secure Headers](https://owasp.org/www-project-secure-headers/)
- [Let's Encrypt](https://letsencrypt.org/)
- [Certbot Documentation](https://certbot.eff.org/)
- [Mozilla SSL Configuration](https://wiki.mozilla.org/Security/Server_Side_TLS)
- [Django Deployment](https://docs.djangoproject.com/en/4.2/howto/deployment/)
