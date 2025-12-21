# MercatoPro Testing Guide

Complete guide for testing the Docker deployment and application functionality.

## Quick Test Commands

```bash
# Comprehensive Docker deployment test
./test_docker.sh

# Or using Makefile
make test-docker

# Quick health check
make health

# Django unit tests
make test
```

---

## Test Script Overview

### What `test_docker.sh` Tests

The automated test script performs 15 comprehensive test categories:

1. **Container Status** - Verifies all 6 containers are running
2. **Health Checks** - Checks health status of each service
3. **Database Connection** - PostgreSQL connectivity and migrations
4. **Redis Connection** - Redis cache functionality
5. **Web Application Endpoints** - HTTP responses for /, /admin, /health
6. **Static Files** - Static file serving via Nginx
7. **Media Files** - Media directory permissions and accessibility
8. **Celery Workers** - Background task processing
9. **Docker Volumes** - Named volumes and bind mounts
10. **Network Communication** - Inter-container connectivity
11. **Email System** - Email backend configuration
12. **Security Headers** - Nginx security headers (X-Frame-Options, etc.)
13. **Application Endpoints** - Lottery and other app endpoints
14. **Logging System** - Container logs and Nginx logs
15. **Admin & Seed Data** - Admin access and test data verification

### Test Output

```
========================================
TEST 1: Container Status
========================================
✓ Docker Compose is accessible
✓ Container mercatopro_db is running
✓ Container mercatopro_redis is running
✓ Container mercatopro_web is running
✓ Container mercatopro_celery_worker is running
✓ Container mercatopro_celery_beat is running
✓ Container mercatopro_nginx is running

[... more tests ...]

========================================
TEST SUMMARY
========================================

Total Tests: 75
Passed: 75
Failed: 0

========================================
✓ ALL TESTS PASSED!
========================================
```

---

## Running Tests

### 1. Initial Setup Tests

After first deployment:

```bash
# Start containers
docker-compose up -d

# Wait 30-60 seconds for initialization

# Run tests
./test_docker.sh
```

### 2. After Code Changes

```bash
# Rebuild containers
docker-compose build

# Restart services
docker-compose up -d

# Run tests
./test_docker.sh
```

### 3. After Configuration Changes

```bash
# Restart affected services
docker-compose restart web nginx

# Test specific service
docker-compose ps web
docker-compose logs web

# Full test suite
./test_docker.sh
```

---

## Manual Testing

### Container Status

```bash
# List all containers
docker-compose ps

# Expected output:
#   mercatopro_db             running    healthy
#   mercatopro_redis          running    healthy
#   mercatopro_web            running    healthy
#   mercatopro_celery_worker  running    healthy
#   mercatopro_celery_beat    running    healthy
#   mercatopro_nginx          running    healthy
```

### Health Checks

```bash
# Check specific service health
docker inspect mercatopro_web --format='{{.State.Health.Status}}'
# Expected: healthy

# View health check logs
docker inspect mercatopro_web --format='{{range .State.Health.Log}}{{.Output}}{{end}}'

# Quick health check (Makefile)
make health
```

### Database Tests

```bash
# Test PostgreSQL connection
docker-compose exec db pg_isready -U mercato_user
# Expected: accepting connections

# List databases
docker-compose exec db psql -U mercato_user -l

# Connect to database
docker-compose exec db psql -U mercato_user -d mercato_db

# Check migrations
docker-compose exec web python manage.py showmigrations
```

### Redis Tests

```bash
# Test Redis connection
docker-compose exec redis redis-cli -a redis_password ping
# Expected: PONG

# View Redis info
docker-compose exec redis redis-cli -a redis_password info

# List keys
docker-compose exec redis redis-cli -a redis_password keys '*'
```

### Web Application Tests

```bash
# Test homepage
curl -I http://localhost/
# Expected: HTTP/1.1 200 OK or 302 Found

# Test admin panel
curl -I http://localhost/admin/
# Expected: HTTP/1.1 200 OK or 302 Found

# Test health endpoint
curl http://localhost/health
# Expected: HTTP 200 with health status

# Test static files
curl -I http://localhost/static/admin/css/base.css
# Expected: HTTP/1.1 200 OK
```

### Celery Tests

```bash
# Check Celery worker
docker-compose exec celery-worker celery -A mercatopro inspect ping
# Expected: pong response

# View active tasks
docker-compose exec celery-worker celery -A mercatopro inspect active

# View worker stats
docker-compose exec celery-worker celery -A mercatopro inspect stats

# Check beat scheduler
docker-compose exec celery-beat ps aux | grep celery
```

### Network Tests

```bash
# Test web -> database
docker-compose exec web nc -zv db 5432
# Expected: succeeded

# Test web -> redis
docker-compose exec web nc -zv redis 6379
# Expected: succeeded

# Test nginx -> web
docker-compose exec nginx nc -zv web 8000
# Expected: succeeded

# Inspect network
docker network inspect mercato_django_mercato_network
```

### Volume Tests

```bash
# List volumes
docker volume ls | grep mercato

# Inspect specific volume
docker volume inspect mercato_django_postgres_data

# Check bind mounts
ls -la ./staticfiles
ls -la ./media

# Check volume contents
docker-compose exec web ls -la /app/staticfiles
docker-compose exec web ls -la /app/media
```

---

## Performance Testing

### Resource Usage

```bash
# View resource stats (real-time)
docker stats

# View container resource limits
docker-compose config

# Check disk usage
docker system df
```

### Load Testing

```bash
# Simple load test with curl
for i in {1..100}; do
  curl -s -o /dev/null -w "%{http_code}\n" http://localhost/
done

# Using Apache Bench (if installed)
ab -n 1000 -c 10 http://localhost/

# Using wrk (if installed)
wrk -t4 -c100 -d30s http://localhost/
```

---

## Integration Testing

### End-to-End User Flow

```bash
# 1. Create superuser
docker-compose exec web python manage.py createsuperuser

# 2. Populate test data
make seed

# 3. Test admin login (browser)
# Visit: http://localhost/admin
# Login with: admin / admin123

# 4. Verify lotteries exist
docker-compose exec web python -c "
from mercato_lotteries.models import Lottery
print(f'Lotteries: {Lottery.objects.count()}')
"

# 5. Test lottery creation via admin
# Create new lottery in admin panel

# 6. Verify static files
curl http://localhost/static/admin/css/base.css

# 7. Test file upload
# Upload lottery images via admin panel

# 8. Verify media files
ls -la ./media/lottery_images/
```

### Email Testing

```bash
# With console backend (development)
# Emails appear in logs:
docker-compose logs -f web | grep -A 20 "Subject:"

# With SMTP backend (production)
# Check email delivery logs
docker-compose logs web | grep "Email sent"

# Test email sending (Django shell)
docker-compose exec web python manage.py shell
>>> from django.core.mail import send_mail
>>> send_mail('Test', 'Message', 'from@example.com', ['to@example.com'])
```

### Celery Task Testing

```bash
# View registered tasks
docker-compose exec celery-worker celery -A mercatopro inspect registered

# Send test task (Django shell)
docker-compose exec web python manage.py shell
>>> from mercato_notifications.tasks import send_email_task
>>> result = send_email_task.delay('test@example.com', 'Subject', 'Message')
>>> result.id

# Check task result
>>> result.get()

# View task in logs
docker-compose logs celery-worker | grep "send_email_task"
```

---

## Troubleshooting Failed Tests

### Test Failure: Container Not Running

```bash
# View why container stopped
docker-compose ps
docker-compose logs [service-name]

# Restart container
docker-compose restart [service-name]

# Or rebuild if code changed
docker-compose up -d --build [service-name]
```

### Test Failure: Health Check Failing

```bash
# View health check logs
docker inspect [container-name] --format='{{json .State.Health}}' | jq

# Manually test health endpoint
docker-compose exec web curl -f http://localhost:8000/admin/

# Check container logs
docker-compose logs [service-name]
```

### Test Failure: Database Connection

```bash
# Check database status
docker-compose exec db pg_isready -U mercato_user

# Check database logs
docker-compose logs db

# Verify environment variables
docker-compose exec web env | grep DB_

# Test connection manually
docker-compose exec web python manage.py check --database default
```

### Test Failure: Static Files

```bash
# Recollect static files
docker-compose exec web python manage.py collectstatic --noinput

# Check staticfiles directory
ls -la ./staticfiles/admin/

# Restart nginx
docker-compose restart nginx

# Check nginx logs
docker-compose logs nginx
```

### Test Failure: Network Communication

```bash
# Check network exists
docker network ls | grep mercato

# Inspect network
docker network inspect mercato_django_mercato_network

# Test DNS resolution
docker-compose exec web ping -c 2 db
docker-compose exec web ping -c 2 redis

# Restart all services
docker-compose restart
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Docker Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Start Docker services
        run: |
          cd mercato_django
          docker-compose up -d
      
      - name: Wait for services
        run: sleep 60
      
      - name: Run Docker tests
        run: |
          cd mercato_django
          ./test_docker.sh
      
      - name: Show logs on failure
        if: failure()
        run: docker-compose logs
      
      - name: Cleanup
        if: always()
        run: docker-compose down -v
```

### GitLab CI Example

```yaml
docker-test:
  stage: test
  image: docker:latest
  services:
    - docker:dind
  before_script:
    - apk add --no-cache docker-compose bash curl
  script:
    - cd mercato_django
    - docker-compose up -d
    - sleep 60
    - ./test_docker.sh
  after_script:
    - docker-compose down -v
```

---

## Test Coverage

### What's Tested

- ✅ All containers running
- ✅ Health checks passing
- ✅ Database connectivity
- ✅ Redis connectivity
- ✅ Web endpoints responding
- ✅ Static file serving
- ✅ Media file access
- ✅ Celery workers active
- ✅ Docker volumes mounted
- ✅ Network communication
- ✅ Security headers
- ✅ Logging functional
- ✅ Admin panel accessible
- ✅ Seed data present

### What's NOT Tested

- ❌ Browser rendering (use Selenium for UI tests)
- ❌ Payment gateway integration (requires sandbox/test mode)
- ❌ Email delivery (only configuration checked)
- ❌ SSL/TLS certificates (manual verification needed)
- ❌ Production-specific security (use security scanners)
- ❌ Performance under load (use dedicated load testing tools)

---

## Best Practices

### Before Deployment

1. ✅ Run `./test_docker.sh` and ensure all tests pass
2. ✅ Check `docker-compose ps` - all containers healthy
3. ✅ Verify `make health` - all services responding
4. ✅ Review logs: `docker-compose logs` - no errors
5. ✅ Test admin access: http://localhost/admin
6. ✅ Verify seed data: `make seed` and check in admin

### During Development

1. 🔄 Run tests after each significant change
2. 🔄 Check logs frequently: `docker-compose logs -f`
3. 🔄 Monitor resources: `docker stats`
4. 🔄 Test endpoints manually after API changes
5. 🔄 Rebuild containers after dependency changes

### Before Production

1. 🚀 Full test suite: `./test_docker.sh`
2. 🚀 Security scan: `docker scan mercato_django_web`
3. 🚀 Load test: Test with expected traffic
4. 🚀 Backup test: Test backup/restore procedures
5. 🚀 Monitoring: Set up external monitoring
6. 🚀 Verify `.env.production` settings

---

## Additional Resources

- **Docker Documentation**: https://docs.docker.com/
- **Docker Compose Testing**: https://docs.docker.com/compose/reference/
- **Django Testing**: https://docs.djangoproject.com/en/stable/topics/testing/
- **Celery Testing**: https://docs.celeryproject.org/en/stable/userguide/testing.html

### Related Files

- `test_docker.sh` - Automated test script
- `DOCKER_SETUP.md` - Complete Docker setup guide
- `DOCKER_README.md` - Docker implementation overview
- `Makefile` - Quick commands including `make test-docker`

---

**Last Updated**: 2024
**Version**: 1.0
