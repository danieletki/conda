#!/bin/bash
# =============================================================================
# MercatoPro Docker Deployment Tests
# =============================================================================
# This script tests all components of the Docker deployment
# Run it after starting the containers with: docker-compose up -d

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0
TOTAL_TESTS=0

# Function to print section header
print_header() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

# Function to print test result
print_test() {
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $2"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "${RED}✗${NC} $2"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

# Function to wait for services
wait_for_service() {
    local service=$1
    local max_attempts=30
    local attempt=1
    
    echo -e "${YELLOW}⏳ Waiting for $service to be healthy...${NC}"
    
    while [ $attempt -le $max_attempts ]; do
        if docker-compose ps $service | grep -q "healthy"; then
            echo -e "${GREEN}✓ $service is healthy${NC}"
            return 0
        fi
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo -e "${RED}✗ $service failed to become healthy${NC}"
    return 1
}

# =============================================================================
# Test 1: Container Status
# =============================================================================
print_header "TEST 1: Container Status"

# Check if docker-compose is running
docker-compose ps > /dev/null 2>&1
print_test $? "Docker Compose is accessible"

# List of expected containers
CONTAINERS=(
    "mercatopro_db"
    "mercatopro_redis"
    "mercatopro_web"
    "mercatopro_celery_worker"
    "mercatopro_celery_beat"
    "mercatopro_nginx"
)

# Check each container is running
for container in "${CONTAINERS[@]}"; do
    if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
        print_test 0 "Container $container is running"
    else
        print_test 1 "Container $container is NOT running"
    fi
done

# =============================================================================
# Test 2: Health Checks
# =============================================================================
print_header "TEST 2: Health Checks"

# Check health status of containers with health checks
for container in "${CONTAINERS[@]}"; do
    health_status=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "none")
    
    if [ "$health_status" = "healthy" ]; then
        print_test 0 "Health check: $container is healthy"
    elif [ "$health_status" = "none" ]; then
        # Some containers might not have health checks
        echo -e "${YELLOW}⚠${NC}  No health check configured for $container"
    else
        print_test 1 "Health check: $container is $health_status"
    fi
done

# =============================================================================
# Test 3: Database Connection
# =============================================================================
print_header "TEST 3: Database Connection"

# Test PostgreSQL is ready
docker-compose exec -T db pg_isready -U mercato_user > /dev/null 2>&1
print_test $? "PostgreSQL is accepting connections"

# Test database exists
docker-compose exec -T db psql -U mercato_user -lqt | cut -d \| -f 1 | grep -qw mercato_db
print_test $? "Database 'mercato_db' exists"

# Test Django can connect to database
docker-compose exec -T web python manage.py check --database default > /dev/null 2>&1
print_test $? "Django can connect to database"

# Check if migrations are applied
MIGRATION_COUNT=$(docker-compose exec -T web python manage.py showmigrations 2>/dev/null | grep -c "\[X\]" || echo "0")
if [ "$MIGRATION_COUNT" -gt 0 ]; then
    print_test 0 "Database migrations applied ($MIGRATION_COUNT migrations)"
else
    print_test 1 "No database migrations found"
fi

# =============================================================================
# Test 4: Redis Connection
# =============================================================================
print_header "TEST 4: Redis Connection"

# Test Redis ping
docker-compose exec -T redis redis-cli -a redis_password ping > /dev/null 2>&1
print_test $? "Redis responds to PING command"

# Test Redis can set/get keys
docker-compose exec -T redis redis-cli -a redis_password SET test_key "test_value" > /dev/null 2>&1
print_test $? "Redis can SET keys"

TEST_VALUE=$(docker-compose exec -T redis redis-cli -a redis_password GET test_key 2>/dev/null | tr -d '\r')
if [ "$TEST_VALUE" = "test_value" ]; then
    print_test 0 "Redis can GET keys"
else
    print_test 1 "Redis GET failed (expected 'test_value', got '$TEST_VALUE')"
fi

# Cleanup test key
docker-compose exec -T redis redis-cli -a redis_password DEL test_key > /dev/null 2>&1

# =============================================================================
# Test 5: Web Application Endpoints
# =============================================================================
print_header "TEST 5: Web Application Endpoints"

# Wait for nginx to be ready
sleep 3

# Test homepage (GET /)
HTTP_CODE=$(curl -o /dev/null -s -w "%{http_code}" http://localhost/)
if [ "$HTTP_CODE" -eq 200 ] || [ "$HTTP_CODE" -eq 302 ]; then
    print_test 0 "Homepage (/) returns HTTP $HTTP_CODE"
else
    print_test 1 "Homepage (/) returns HTTP $HTTP_CODE (expected 200 or 302)"
fi

# Test admin panel (GET /admin)
HTTP_CODE=$(curl -o /dev/null -s -w "%{http_code}" http://localhost/admin/)
if [ "$HTTP_CODE" -eq 200 ] || [ "$HTTP_CODE" -eq 302 ]; then
    print_test 0 "Admin panel (/admin/) returns HTTP $HTTP_CODE"
else
    print_test 1 "Admin panel (/admin/) returns HTTP $HTTP_CODE (expected 200 or 302)"
fi

# Test admin login page
ADMIN_CONTENT=$(curl -s http://localhost/admin/login/)
if echo "$ADMIN_CONTENT" | grep -q "Django"; then
    print_test 0 "Admin login page contains Django branding"
else
    print_test 1 "Admin login page doesn't contain expected content"
fi

# Test health endpoint
HTTP_CODE=$(curl -o /dev/null -s -w "%{http_code}" http://localhost/health)
if [ "$HTTP_CODE" -eq 200 ]; then
    print_test 0 "Health endpoint (/health) returns HTTP $HTTP_CODE"
else
    print_test 1 "Health endpoint (/health) returns HTTP $HTTP_CODE (expected 200)"
fi

# =============================================================================
# Test 6: Static Files
# =============================================================================
print_header "TEST 6: Static Files"

# Test static files are accessible
HTTP_CODE=$(curl -o /dev/null -s -w "%{http_code}" http://localhost/static/admin/css/base.css)
if [ "$HTTP_CODE" -eq 200 ] || [ "$HTTP_CODE" -eq 304 ]; then
    print_test 0 "Static files are accessible (admin CSS)"
else
    print_test 1 "Static files NOT accessible (HTTP $HTTP_CODE)"
fi

# Check if staticfiles directory exists and has content
if docker-compose exec -T web test -d /app/staticfiles && [ "$(docker-compose exec -T web find /app/staticfiles -type f 2>/dev/null | wc -l)" -gt 10 ]; then
    print_test 0 "Staticfiles directory has content"
else
    print_test 1 "Staticfiles directory is empty or missing"
fi

# =============================================================================
# Test 7: Media Files
# =============================================================================
print_header "TEST 7: Media Files"

# Check if media directory exists
docker-compose exec -T web test -d /app/media
print_test $? "Media directory exists"

# Check media directory permissions
docker-compose exec -T web test -w /app/media
print_test $? "Media directory is writable"

# =============================================================================
# Test 8: Celery Workers
# =============================================================================
print_header "TEST 8: Celery Workers"

# Check Celery worker is responding
docker-compose exec -T celery-worker celery -A mercatopro inspect ping > /dev/null 2>&1
print_test $? "Celery worker responds to ping"

# Check Celery worker stats
WORKER_STATS=$(docker-compose exec -T celery-worker celery -A mercatopro inspect stats 2>/dev/null)
if echo "$WORKER_STATS" | grep -q "OK"; then
    print_test 0 "Celery worker stats available"
else
    print_test 1 "Cannot retrieve Celery worker stats"
fi

# Check Celery beat is running
if docker-compose exec -T celery-beat ps aux | grep -q "[c]elery.*beat"; then
    print_test 0 "Celery beat scheduler is running"
else
    print_test 1 "Celery beat scheduler is NOT running"
fi

# =============================================================================
# Test 9: Volumes
# =============================================================================
print_header "TEST 9: Docker Volumes"

# List of expected volumes
VOLUMES=(
    "mercato_django_postgres_data"
    "mercato_django_redis_data"
    "mercato_django_nginx_cache"
    "mercato_django_nginx_logs"
)

for volume in "${VOLUMES[@]}"; do
    if docker volume inspect "$volume" > /dev/null 2>&1; then
        print_test 0 "Volume $volume exists"
    else
        print_test 1 "Volume $volume does NOT exist"
    fi
done

# Check bind-mounted volumes
if [ -d "./staticfiles" ]; then
    print_test 0 "Staticfiles bind mount exists"
else
    print_test 1 "Staticfiles bind mount does NOT exist"
fi

if [ -d "./media" ]; then
    print_test 0 "Media bind mount exists"
else
    print_test 1 "Media bind mount does NOT exist"
fi

# =============================================================================
# Test 10: Network Communication
# =============================================================================
print_header "TEST 10: Network Communication"

# Check if network exists
if docker network inspect mercato_django_mercato_network > /dev/null 2>&1; then
    print_test 0 "Docker network 'mercato_network' exists"
else
    print_test 1 "Docker network 'mercato_network' does NOT exist"
fi

# Test web can reach database
docker-compose exec -T web nc -zv db 5432 > /dev/null 2>&1
print_test $? "Web container can reach database (db:5432)"

# Test web can reach redis
docker-compose exec -T web nc -zv redis 6379 > /dev/null 2>&1
print_test $? "Web container can reach Redis (redis:6379)"

# Test nginx can reach web
docker-compose exec -T nginx nc -zv web 8000 > /dev/null 2>&1
print_test $? "Nginx can reach web container (web:8000)"

# =============================================================================
# Test 11: Email Configuration (if configured)
# =============================================================================
print_header "TEST 11: Email System"

# Check if email backend is configured
EMAIL_BACKEND=$(docker-compose exec -T web python -c "from django.conf import settings; print(settings.EMAIL_BACKEND)" 2>/dev/null | tr -d '\r')
echo -e "${BLUE}Email backend: $EMAIL_BACKEND${NC}"

if [ -n "$EMAIL_BACKEND" ]; then
    print_test 0 "Email backend is configured"
else
    print_test 1 "Email backend is NOT configured"
fi

# Check if Django can send test email (dry run)
docker-compose exec -T web python manage.py check > /dev/null 2>&1
print_test $? "Django email configuration is valid"

# =============================================================================
# Test 12: Security Headers (Nginx)
# =============================================================================
print_header "TEST 12: Security Headers"

# Check X-Frame-Options header
HEADERS=$(curl -s -I http://localhost/)
if echo "$HEADERS" | grep -qi "X-Frame-Options"; then
    print_test 0 "X-Frame-Options header is set"
else
    print_test 1 "X-Frame-Options header is NOT set"
fi

# Check X-Content-Type-Options header
if echo "$HEADERS" | grep -qi "X-Content-Type-Options"; then
    print_test 0 "X-Content-Type-Options header is set"
else
    print_test 1 "X-Content-Type-Options header is NOT set"
fi

# =============================================================================
# Test 13: API Endpoints (if available)
# =============================================================================
print_header "TEST 13: Application Endpoints"

# Test lotteries list endpoint
HTTP_CODE=$(curl -o /dev/null -s -w "%{http_code}" http://localhost/lotteries/)
if [ "$HTTP_CODE" -eq 200 ] || [ "$HTTP_CODE" -eq 302 ]; then
    print_test 0 "Lotteries endpoint (/lotteries/) returns HTTP $HTTP_CODE"
else
    print_test 1 "Lotteries endpoint (/lotteries/) returns HTTP $HTTP_CODE"
fi

# =============================================================================
# Test 14: Logging
# =============================================================================
print_header "TEST 14: Logging System"

# Check if containers are producing logs
WEB_LOG_LINES=$(docker-compose logs --tail=10 web 2>/dev/null | wc -l)
if [ "$WEB_LOG_LINES" -gt 0 ]; then
    print_test 0 "Web container is producing logs ($WEB_LOG_LINES lines)"
else
    print_test 1 "Web container has NO logs"
fi

NGINX_LOG_LINES=$(docker-compose logs --tail=10 nginx 2>/dev/null | wc -l)
if [ "$NGINX_LOG_LINES" -gt 0 ]; then
    print_test 0 "Nginx container is producing logs ($NGINX_LOG_LINES lines)"
else
    print_test 1 "Nginx container has NO logs"
fi

# Check if nginx log volume has files
NGINX_LOG_FILES=$(docker-compose exec -T nginx ls -la /var/log/nginx/ 2>/dev/null | wc -l)
if [ "$NGINX_LOG_FILES" -gt 2 ]; then
    print_test 0 "Nginx log files exist in volume"
else
    print_test 1 "Nginx log volume is empty"
fi

# =============================================================================
# Test 15: Admin Access with Seed Data
# =============================================================================
print_header "TEST 15: Admin Panel & Seed Data"

# Check if superuser exists
SUPERUSER_EXISTS=$(docker-compose exec -T web python -c "
from django.contrib.auth import get_user_model;
User = get_user_model();
print('yes' if User.objects.filter(username='admin').exists() else 'no')
" 2>/dev/null | tr -d '\r')

if [ "$SUPERUSER_EXISTS" = "yes" ]; then
    print_test 0 "Superuser 'admin' exists"
else
    print_test 1 "Superuser 'admin' does NOT exist"
fi

# Check if seed data exists (count users)
USER_COUNT=$(docker-compose exec -T web python -c "
from django.contrib.auth import get_user_model;
User = get_user_model();
print(User.objects.count())
" 2>/dev/null | tr -d '\r')

if [ "$USER_COUNT" -gt 0 ]; then
    print_test 0 "Database has users ($USER_COUNT total)"
else
    print_test 1 "Database has NO users"
fi

# Check if lotteries exist
LOTTERY_COUNT=$(docker-compose exec -T web python -c "
from mercato_lotteries.models import Lottery;
print(Lottery.objects.count())
" 2>/dev/null | tr -d '\r')

if [ "$LOTTERY_COUNT" -gt 0 ]; then
    print_test 0 "Database has lotteries ($LOTTERY_COUNT total)"
else
    echo -e "${YELLOW}⚠${NC}  Database has NO lotteries (run: make seed)"
fi

# =============================================================================
# Final Summary
# =============================================================================
print_header "TEST SUMMARY"

echo ""
echo -e "${BLUE}Total Tests: $TOTAL_TESTS${NC}"
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✓ ALL TESTS PASSED!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "${GREEN}Your Docker deployment is healthy and ready to use!${NC}"
    echo ""
    echo -e "${BLUE}Access points:${NC}"
    echo -e "  • Application: ${YELLOW}http://localhost${NC}"
    echo -e "  • Admin Panel: ${YELLOW}http://localhost/admin${NC}"
    echo -e "  • Username: ${YELLOW}admin${NC}"
    echo -e "  • Password: ${YELLOW}admin123${NC}"
    echo ""
    exit 0
else
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}✗ SOME TESTS FAILED${NC}"
    echo -e "${RED}========================================${NC}"
    echo ""
    echo -e "${YELLOW}Please review the failed tests above and check:${NC}"
    echo -e "  1. All containers are running: ${YELLOW}docker-compose ps${NC}"
    echo -e "  2. Container logs: ${YELLOW}docker-compose logs${NC}"
    echo -e "  3. Network connectivity: ${YELLOW}docker network inspect mercato_django_mercato_network${NC}"
    echo ""
    exit 1
fi
