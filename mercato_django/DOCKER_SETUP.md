# MercatoPro Docker Deployment Guide

Complete guide for deploying and managing MercatoPro using Docker and Docker Compose.

## 📋 Table of Contents

- [Requirements](#requirements)
- [Quick Start](#quick-start)
- [Container Architecture](#container-architecture)
- [Volumes Explained](#volumes-explained)
- [Accessing Services](#accessing-services)
- [Database Management](#database-management)
- [Seed Data](#seed-data)
- [Viewing Logs](#viewing-logs)
- [Backup & Restore](#backup--restore)
- [Testing Deployment](#testing-deployment)
- [Environment Configuration](#environment-configuration)
- [Troubleshooting](#troubleshooting)
- [Production Deployment](#production-deployment)

---

## Requirements

### Minimum Requirements

- **Docker**: Version 20.10 or higher
- **Docker Compose**: Version 2.0 or higher
- **System Resources**:
  - RAM: 4GB minimum (8GB recommended)
  - Disk Space: 10GB minimum
  - CPU: 2 cores minimum

### Check Your Installation

```bash
# Check Docker version
docker --version
# Expected: Docker version 20.10.x or higher

# Check Docker Compose version
docker-compose --version
# Expected: Docker Compose version 2.x.x or higher

# Verify Docker is running
docker ps
# Should show running containers or empty list (no errors)
```

---

## Quick Start

Get MercatoPro up and running in **3 commands**:

```bash
# 1. Navigate to project directory
cd mercato_django

# 2. Start all services
docker-compose up -d

# 3. Wait for services to be ready (about 30-60 seconds)
docker-compose ps
```

**That's it!** Your application is now running at:
- **Application**: http://localhost
- **Admin Panel**: http://localhost/admin
- **Default Credentials**: 
  - Username: `admin`
  - Password: `admin123`

### Optional: Populate with Test Data

```bash
# Add sample lotteries, users, and transactions
make seed
```

---

## Container Architecture

MercatoPro uses a microservices architecture with 6 containers:

```
┌─────────────────────────────────────────────────────────────┐
│                         Nginx (Port 80/443)                 │
│                    Reverse Proxy & Static Files             │
└────────────────────────────┬────────────────────────────────┘
                             │
                ┌────────────┴────────────┐
                │                         │
┌───────────────▼──────────┐   ┌─────────▼────────────┐
│   Django Web (Port 8000) │   │  Static/Media Files  │
│   Gunicorn/Runserver     │   │    (Nginx serves)    │
└──────────┬───────────────┘   └──────────────────────┘
           │
    ┌──────┴──────┬────────────────────┬─────────────┐
    │             │                    │             │
┌───▼────┐  ┌────▼─────┐  ┌───────────▼──┐  ┌──────▼─────┐
│   DB   │  │  Redis   │  │ Celery Worker│  │Celery Beat │
│Postgres│  │ (Cache)  │  │ (Background) │  │ (Scheduler)│
└────────┘  └──────────┘  └──────────────┘  └────────────┘
```

### Service Descriptions

| Container | Role | Port | Health Check |
|-----------|------|------|--------------|
| **nginx** | Reverse proxy, serves static/media files | 80, 443 | `/health` endpoint |
| **web** | Django application (Gunicorn) | 8000 | `/admin/` endpoint |
| **db** | PostgreSQL 15 database | 5432 | `pg_isready` |
| **redis** | Cache and Celery message broker | 6379 | `redis-cli ping` |
| **celery-worker** | Background task processing | - | Celery inspect |
| **celery-beat** | Scheduled task execution | - | Celery inspect |

---

## Volumes Explained

### Named Volumes (Docker-managed)

These volumes persist data even when containers are removed:

| Volume | Purpose | Data Stored |
|--------|---------|-------------|
| `postgres_data` | Database persistence | PostgreSQL database files |
| `redis_data` | Redis persistence | Redis RDB snapshots, AOF logs |
| `nginx_cache` | Nginx caching | Cached proxy responses |
| `nginx_logs` | Nginx logging | Access and error logs |

**Location**: `/var/lib/docker/volumes/` on the host machine

**Backup**: These volumes should be backed up regularly for production

### Bind Mounts (Host-mapped)

These directories on your host machine are mounted into containers:

| Host Path | Container Path | Purpose |
|-----------|----------------|---------|
| `./staticfiles` | `/app/staticfiles` (web)<br>`/var/www/static` (nginx) | Collected Django static files (CSS, JS, images) |
| `./media` | `/app/media` (web)<br>`/var/www/media` (nginx) | User-uploaded files (lottery images) |
| `./docker/nginx/nginx.conf` | `/etc/nginx/nginx.conf` | Nginx main configuration |
| `./docker/nginx/conf.d/` | `/etc/nginx/conf.d/` | Nginx server configuration |

**Advantage**: Easy to view, edit, and backup files directly from host

---

## Accessing Services

### Admin Panel

Access Django admin interface:

```bash
# URL
http://localhost/admin

# Default Superuser (created automatically)
Username: admin
Password: admin123

# Create additional superuser
docker-compose exec web python manage.py createsuperuser
```

### Database (PostgreSQL)

#### Using psql Command

```bash
# Connect to database directly
docker-compose exec db psql -U mercato_user -d mercato_db

# Or from host machine (if psql is installed)
psql -h localhost -U mercato_user -d mercato_db
# Password: mercato_password (from .env.docker)
```

#### Using Django shell

```bash
# Open Django shell with ORM access
docker-compose exec web python manage.py shell

# Example: Query users
from django.contrib.auth import get_user_model
User = get_user_model()
print(User.objects.count())
```

#### Using Database GUI Tools

Connect with tools like **pgAdmin**, **DBeaver**, or **TablePlus**:

```
Host: localhost
Port: 5432
Database: mercato_db
Username: mercato_user
Password: mercato_password
```

### Redis

```bash
# Connect to Redis CLI
docker-compose exec redis redis-cli -a redis_password

# Test connection
PING
# Expected response: PONG

# View all keys
KEYS *

# Get specific key
GET some_key
```

### Container Shell Access

```bash
# Access web container bash
docker-compose exec web bash

# Access database container
docker-compose exec db bash

# Access nginx container
docker-compose exec nginx sh  # (Alpine Linux uses sh)
```

---

## Database Management

### Migrations

```bash
# Apply all migrations
make migrate
# Or: docker-compose exec web python manage.py migrate

# Create new migration
docker-compose exec web python manage.py makemigrations

# Show migration status
docker-compose exec web python manage.py showmigrations

# Rollback to specific migration
docker-compose exec web python manage.py migrate app_name migration_name
```

### Database Reset

```bash
# ⚠️  WARNING: This deletes ALL data!

# Method 1: Using Makefile
make clean  # Prompts for confirmation

# Method 2: Manual
docker-compose down -v  # Removes containers AND volumes
docker-compose up -d    # Recreate fresh database
```

---

## Seed Data

Populate the database with test data for development:

### What Gets Created

The seed command creates:
- **1 superuser**: `admin` / `admin123`
- **5 buyer accounts**: `buyer1` through `buyer5` (password: `password123`)
- **3 seller accounts**: `seller1` through `seller3` (password: `password123`)
- **10 lotteries** with various statuses (draft, active, closed)
- **Sample lottery tickets** and payment transactions
- **Lottery images** (randomly generated)

### Running Seed Command

```bash
# Using Makefile
make seed

# Or directly
docker-compose exec web python manage.py seed_data

# Full development setup (build + migrate + seed)
make dev-setup
```

### Verify Seed Data

```bash
# Check user count
docker-compose exec web python -c "from django.contrib.auth import get_user_model; print(get_user_model().objects.count())"

# Check lottery count
docker-compose exec web python -c "from mercato_lotteries.models import Lottery; print(Lottery.objects.count())"
```

---

## Viewing Logs

### All Services

```bash
# Follow all logs (real-time)
make logs
# Or: docker-compose logs -f

# View last 100 lines
docker-compose logs --tail=100

# View logs since last 10 minutes
docker-compose logs --since 10m
```

### Specific Services

```bash
# Web application logs
make logs-web
# Or: docker-compose logs -f web

# Database logs
make logs-db
# Or: docker-compose logs -f db

# Nginx logs
make nginx-logs
# Or: docker-compose logs -f nginx

# Celery logs (worker + beat)
make celery-logs
# Or: docker-compose logs -f celery-worker celery-beat
```

### Nginx Access/Error Logs

```bash
# View nginx access log
docker-compose exec nginx tail -f /var/log/nginx/access.log

# View nginx error log
docker-compose exec nginx tail -f /var/log/nginx/error.log

# Copy logs to host machine
docker cp mercatopro_nginx:/var/log/nginx/access.log ./nginx_access.log
```

---

## Backup & Restore

### Database Backup

#### Method 1: Using pg_dump (Recommended)

```bash
# Create timestamped backup
docker-compose exec db pg_dump -U mercato_user mercato_db > backup_$(date +%Y%m%d_%H%M%S).sql

# Or use Makefile
make backup-db
```

#### Method 2: Backup Entire Volume

```bash
# Stop containers first
docker-compose stop

# Backup postgres_data volume
docker run --rm \
  -v mercato_django_postgres_data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/postgres_backup.tar.gz -C /data .

# Restart containers
docker-compose start
```

### Database Restore

#### From SQL Dump

```bash
# Restore from SQL file
docker-compose exec -T db psql -U mercato_user mercato_db < backup_20240101_120000.sql

# Or use Makefile
make restore-db FILE=backup_20240101_120000.sql
```

#### From Volume Backup

```bash
# Stop containers
docker-compose down

# Remove old volume
docker volume rm mercato_django_postgres_data

# Recreate volume
docker volume create mercato_django_postgres_data

# Restore data
docker run --rm \
  -v mercato_django_postgres_data:/data \
  -v $(pwd):/backup \
  alpine sh -c "cd /data && tar xzf /backup/postgres_backup.tar.gz"

# Start containers
docker-compose up -d
```

### Media Files Backup

```bash
# Media files are in ./media directory (bind mount)
# Simple backup with tar
tar czf media_backup_$(date +%Y%m%d).tar.gz ./media/

# Or use rsync
rsync -av ./media/ /path/to/backup/media/
```

---

## Testing Deployment

### Automated Test Script

Run comprehensive deployment tests:

```bash
# Execute test script
./test_docker.sh

# What it tests:
# ✓ All containers running
# ✓ Health checks passing
# ✓ Database connectivity
# ✓ Redis connectivity
# ✓ HTTP endpoints (/, /admin, /health)
# ✓ Static files serving
# ✓ Media files access
# ✓ Celery workers
# ✓ Docker volumes
# ✓ Network communication
# ✓ Security headers
# ✓ Logging
```

### Manual Health Checks

```bash
# Check container status
docker-compose ps

# Check health of all services
make health

# Test specific endpoints
curl http://localhost/              # Homepage
curl http://localhost/admin/        # Admin panel
curl http://localhost/health        # Health endpoint
curl -I http://localhost/static/admin/css/base.css  # Static files
```

### Django System Checks

```bash
# Run Django's built-in checks
docker-compose exec web python manage.py check

# Check deployment readiness
docker-compose exec web python manage.py check --deploy

# Check database
docker-compose exec web python manage.py check --database default
```

---

## Environment Configuration

### Environment Files

- **`.env.docker`**: Default Docker environment (already configured)
- **`.env`**: Override for local development (create from `.env.example`)

### Key Environment Variables

```bash
# Django Settings
DEBUG=False                          # Set to False for production
SECRET_KEY=your-secret-key-here     # Change in production!
ALLOWED_HOSTS=*                      # Restrict in production

# Database
DB_NAME=mercato_db
DB_USER=mercato_user
DB_PASSWORD=mercato_password        # Change in production!

# Redis
REDIS_PASSWORD=redis_password       # Change in production!

# Email (configure for production)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# PayPal (add your credentials)
PAYPAL_CLIENT_ID=your-paypal-client-id
PAYPAL_CLIENT_SECRET=your-paypal-secret
PAYPAL_SANDBOX_MODE=True            # False for production

# Ports (change if conflicts exist)
WEB_PORT=8000
NGINX_HTTP_PORT=80
NGINX_HTTPS_PORT=443
```

### Changing Ports

If port 80 is already in use:

```bash
# Edit .env.docker
NGINX_HTTP_PORT=8080

# Restart containers
docker-compose down
docker-compose up -d

# Access on new port
http://localhost:8080
```

---

## Troubleshooting

### Common Issues & Solutions

#### 1. Port Already in Use

**Error**: "Bind for 0.0.0.0:80 failed: port is already allocated"

**Solution**:
```bash
# Check what's using the port
sudo lsof -i :80
# Or on Linux: sudo netstat -tulpn | grep :80

# Option A: Stop the conflicting service
sudo systemctl stop apache2  # or nginx

# Option B: Change port in .env.docker
NGINX_HTTP_PORT=8080
docker-compose down && docker-compose up -d
```

#### 2. Containers Not Starting

**Error**: Container exits immediately

**Solution**:
```bash
# Check logs
docker-compose logs web

# Common causes:
# - Missing dependencies: Rebuild
docker-compose build --no-cache web

# - Database not ready: Check db logs
docker-compose logs db

# - Port conflicts: Change ports in .env.docker
```

#### 3. Database Connection Refused

**Error**: "django.db.utils.OperationalError: could not connect to server"

**Solution**:
```bash
# Check database health
docker-compose exec db pg_isready -U mercato_user

# Wait for database (automatic in entrypoint, but can force)
docker-compose restart web

# Check database container
docker-compose ps db
# Should show "healthy" status
```

#### 4. Static Files Not Loading (404)

**Error**: Static files return 404

**Solution**:
```bash
# Collect static files
docker-compose exec web python manage.py collectstatic --noinput

# Check staticfiles directory
ls -la ./staticfiles/

# Restart nginx
docker-compose restart nginx

# Check nginx logs
docker-compose logs nginx
```

#### 5. Permission Denied Errors

**Error**: "Permission denied" when accessing files

**Solution**:
```bash
# Fix ownership of media/staticfiles
sudo chown -R $USER:$USER ./media ./staticfiles

# Or inside container
docker-compose exec web chown -R mercato:mercato /app/media /app/staticfiles
```

#### 6. Celery Workers Not Processing Tasks

**Error**: Tasks stuck in pending state

**Solution**:
```bash
# Check worker status
docker-compose exec celery-worker celery -A mercatopro inspect active

# Check Redis connection
docker-compose exec redis redis-cli -a redis_password ping

# Restart workers
docker-compose restart celery-worker celery-beat

# Check worker logs
docker-compose logs celery-worker
```

#### 7. Out of Memory/Disk Space

**Error**: Container crashes, "No space left on device"

**Solution**:
```bash
# Check disk usage
df -h
docker system df

# Clean up unused Docker resources
docker system prune -a --volumes
# ⚠️  WARNING: This removes ALL unused containers, images, and volumes!

# Remove old images only
docker image prune -a

# Restart containers
docker-compose up -d
```

#### 8. Migrations Not Applied

**Error**: "Table doesn't exist" errors

**Solution**:
```bash
# Check migration status
docker-compose exec web python manage.py showmigrations

# Apply migrations
docker-compose exec web python manage.py migrate

# If migrations conflict, fake them (careful!)
docker-compose exec web python manage.py migrate --fake app_name migration_name
```

#### 9. Cannot Access Admin Panel

**Error**: Admin returns 404 or 500 error

**Solution**:
```bash
# Check URL patterns
docker-compose exec web python manage.py show_urls

# Collect static files (for admin CSS)
docker-compose exec web python manage.py collectstatic --noinput

# Create superuser if missing
docker-compose exec web python manage.py createsuperuser

# Check logs
docker-compose logs web
```

#### 10. Container Health Check Failing

**Error**: Container shows as "unhealthy"

**Solution**:
```bash
# Check health status
docker inspect mercatopro_web --format='{{json .State.Health}}' | jq

# View health check logs
docker inspect mercatopro_web --format='{{range .State.Health.Log}}{{.Output}}{{end}}'

# Manually test health endpoint
docker-compose exec web curl -f http://localhost:8000/admin/

# Restart container
docker-compose restart web
```

### Getting Help

If issues persist:

1. **Check logs**: `docker-compose logs -f`
2. **Run tests**: `./test_docker.sh`
3. **Verify health**: `make health`
4. **Clean restart**: `docker-compose down && docker-compose up -d`
5. **Full reset**: `make clean` (⚠️  deletes all data)

---

## Production Deployment

### Pre-Production Checklist

Before deploying to production:

- [ ] Change `SECRET_KEY` to a secure random value
- [ ] Set `DEBUG=False`
- [ ] Configure `ALLOWED_HOSTS` with your domain
- [ ] Change database passwords (`DB_PASSWORD`, `REDIS_PASSWORD`)
- [ ] Configure email settings (SMTP credentials)
- [ ] Add PayPal production credentials
- [ ] Set up SSL/TLS certificates (Let's Encrypt)
- [ ] Configure `CSRF_TRUSTED_ORIGINS` with your domain
- [ ] Enable security headers (`SESSION_COOKIE_SECURE=True`, `CSRF_COOKIE_SECURE=True`)
- [ ] Set up automated backups
- [ ] Configure monitoring and logging
- [ ] Review and restrict CORS settings

### Production Environment Variables

```bash
# Copy and edit for production
cp .env.docker .env.production

# Update these values:
DEBUG=False
SECRET_KEY=$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
ALLOWED_HOSTS=your-domain.com,www.your-domain.com
DB_PASSWORD=strong-random-password
REDIS_PASSWORD=another-strong-password
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_SSL_REDIRECT=True
CSRF_TRUSTED_ORIGINS=https://your-domain.com
```

### SSL/TLS Setup

```bash
# Place certificates in docker/nginx/ssl/
# - fullchain.pem (certificate + chain)
# - privkey.pem (private key)

# Update nginx configuration for HTTPS
# Edit docker/nginx/conf.d/default.conf

# Restart nginx
docker-compose restart nginx
```

### Automated Backups

```bash
# Create backup script (backup.sh)
#!/bin/bash
BACKUP_DIR=/backups/$(date +%Y%m%d)
mkdir -p $BACKUP_DIR

# Database backup
docker-compose exec -T db pg_dump -U mercato_user mercato_db > $BACKUP_DIR/database.sql

# Media backup
tar czf $BACKUP_DIR/media.tar.gz ./media/

# Upload to remote storage (S3, etc.)
# aws s3 sync $BACKUP_DIR s3://your-bucket/backups/

# Add to crontab
# 0 2 * * * /path/to/backup.sh
```

### Monitoring

```bash
# View resource usage
docker stats

# Check container health
docker-compose ps

# View logs
docker-compose logs --since 1h

# Set up external monitoring (recommended):
# - Sentry for error tracking
# - Prometheus + Grafana for metrics
# - ELK stack for log aggregation
```

---

## Quick Reference Commands

### Essential Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Restart services
docker-compose restart

# View logs
docker-compose logs -f

# Check status
docker-compose ps

# Execute command in container
docker-compose exec web python manage.py <command>

# Access shell
docker-compose exec web bash

# Run tests
./test_docker.sh
```

### Makefile Commands

All available make commands:

```bash
make help              # Show all available commands
make build             # Build images
make up                # Start services
make down              # Stop services
make restart           # Restart all services
make logs              # View all logs
make logs-web          # View web logs
make logs-db           # View database logs
make shell             # Open shell in web container
make migrate           # Run migrations
make seed              # Populate test data
make collectstatic     # Collect static files
make createsuperuser   # Create Django superuser
make backup-db         # Backup database
make restore-db        # Restore database
make health            # Check service health
make clean             # Remove all data (⚠️  dangerous)
```

---

## Additional Resources

- **Django Documentation**: https://docs.djangoproject.com/
- **Docker Documentation**: https://docs.docker.com/
- **PostgreSQL Documentation**: https://www.postgresql.org/docs/
- **Nginx Documentation**: https://nginx.org/en/docs/
- **Celery Documentation**: https://docs.celeryproject.org/

### Related Documentation Files

- `DOCKER_README.md` - Docker implementation overview
- `NGINX_README.md` - Nginx configuration details
- `EMAIL_SYSTEM_README.md` - Email system documentation
- `PAYMENT_INTEGRATION.md` - PayPal integration guide
- `README.md` - Main project documentation

---

## Support

For issues or questions:

1. Check logs: `docker-compose logs -f`
2. Run diagnostics: `./test_docker.sh`
3. Review troubleshooting section above
4. Check project README files

---

**Last Updated**: 2024
**Version**: 1.0
