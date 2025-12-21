# MercatoPro - Quick Start Guide

## 🚀 Get Started in 3 Commands

```bash
cd mercato_django
docker-compose up -d
docker-compose ps  # Wait for "healthy" status
```

**That's it!** Your application is now running.

---

## 📍 Access Points

- **Application**: http://localhost
- **Admin Panel**: http://localhost/admin
- **Login**: admin / admin123

---

## ✅ Verify Deployment

```bash
# Run comprehensive tests (75+ checks)
./test_docker.sh

# Quick health check
make health

# View status
docker-compose ps
```

---

## 🌱 Add Test Data

```bash
make seed
```

This creates:
- 5 buyer accounts (buyer1-buyer5, password: password123)
- 3 seller accounts (seller1-seller3, password: password123)
- 10 sample lotteries with images
- Sample tickets and transactions

---

## 📖 Essential Commands

```bash
# View logs
make logs                  # All services
make logs-web             # Web only
docker-compose logs -f    # Real-time logs

# Access shell
make shell                # Bash in web container
make dj-shell             # Django shell

# Database
make backup-db            # Backup database
docker-compose exec db psql -U mercato_user -d mercato_db

# Management
make restart              # Restart all services
make down                 # Stop all services
make up                   # Start all services
```

---

## 📚 Complete Documentation

- **[DOCKER_SETUP.md](DOCKER_SETUP.md)** - Complete setup guide (22KB)
- **[TESTING_GUIDE.md](TESTING_GUIDE.md)** - Testing documentation (13KB)
- **[DOCKER_TESTING_SUMMARY.md](DOCKER_TESTING_SUMMARY.md)** - Implementation summary (12KB)
- **[README.md](README.md)** - Main project documentation

---

## 🐛 Troubleshooting

### Containers not starting?
```bash
docker-compose logs
docker-compose down && docker-compose up -d
```

### Port conflicts?
Edit `.env.docker`:
```bash
NGINX_HTTP_PORT=8080
docker-compose down && docker-compose up -d
```

### Database issues?
```bash
docker-compose restart db
docker-compose exec db pg_isready -U mercato_user
```

### Static files not loading?
```bash
make collectstatic
docker-compose restart nginx
```

**More help**: See [DOCKER_SETUP.md](DOCKER_SETUP.md) → Troubleshooting section

---

## 🎯 Development Workflow

### 1. Start Development
```bash
docker-compose up -d    # Uses docker-compose.override.yml automatically
```

### 2. Make Changes
- Edit Python files → **Auto-reloaded** (no rebuild needed)
- Edit templates → Refresh browser
- Edit static files → `make collectstatic` + refresh

### 3. View Changes
```bash
docker-compose logs -f web    # Monitor logs
make health                   # Quick check
```

### 4. Test Changes
```bash
./test_docker.sh              # Full test suite
make test                     # Django unit tests
```

---

## 🏭 Production Deployment

### Pre-deployment Checklist

```bash
# 1. Update environment
cp .env.docker .env.production
# Edit: DEBUG=False, SECRET_KEY, passwords, domain

# 2. Test everything
./test_docker.sh

# 3. Configure SSL (Let's Encrypt recommended)
# Place certificates in docker/nginx/ssl/

# 4. Deploy
docker-compose -f docker-compose.yml up -d

# 5. Verify
curl -I https://yourdomain.com/health
```

**Complete production guide**: [DOCKER_SETUP.md](DOCKER_SETUP.md) → Production Deployment

---

## 🔧 Common Tasks

### Create Superuser
```bash
docker-compose exec web python manage.py createsuperuser
```

### Run Migrations
```bash
make migrate
```

### Collect Static Files
```bash
make collectstatic
```

### Access Database
```bash
# CLI
docker-compose exec db psql -U mercato_user -d mercato_db

# GUI (connect to localhost:5432)
# User: mercato_user
# Pass: mercato_password
# DB: mercato_db
```

### View Celery Tasks
```bash
docker-compose exec celery-worker celery -A mercatopro inspect active
docker-compose logs -f celery-worker
```

---

## 📊 Service Ports

| Service | Internal Port | External Port | Access |
|---------|---------------|---------------|--------|
| Nginx | 80, 443 | 80, 443 | http://localhost |
| Web | 8000 | - | Internal only |
| PostgreSQL | 5432 | 5432* | localhost:5432 |
| Redis | 6379 | 6379* | localhost:6379 |

*Exposed in development mode only (docker-compose.override.yml)

---

## 💡 Tips

### Speed Up Development
- Use `docker-compose.override.yml` (automatic)
- Enable hot reload (already configured)
- Use console email backend (no SMTP setup needed)

### Monitor Resources
```bash
docker stats              # Real-time resource usage
docker system df          # Disk usage
```

### Clean Up
```bash
docker system prune       # Remove unused resources
make clean                # ⚠️ Deletes ALL data (careful!)
```

---

## 🆘 Need Help?

1. **Check logs**: `docker-compose logs -f`
2. **Run tests**: `./test_docker.sh`
3. **View status**: `docker-compose ps`
4. **Read docs**: [DOCKER_SETUP.md](DOCKER_SETUP.md)
5. **Troubleshooting**: [DOCKER_SETUP.md](DOCKER_SETUP.md#troubleshooting)

---

## ✨ What's Included

- ✅ **PostgreSQL 15** - Production database
- ✅ **Redis 7** - Caching & task queue
- ✅ **Django 5** - Web application
- ✅ **Celery** - Background tasks
- ✅ **Nginx** - Reverse proxy & static files
- ✅ **Gunicorn** - WSGI server
- ✅ **Health Checks** - All services monitored
- ✅ **Hot Reload** - Development friendly
- ✅ **Auto SSL** - Production ready

---

**Happy coding! 🎉**

For detailed information, see: **[DOCKER_SETUP.md](DOCKER_SETUP.md)**
