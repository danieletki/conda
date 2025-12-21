#!/bin/bash

# Nginx Reverse Proxy Testing Script
# Tests key functionality of the Nginx configuration

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🧪 Testing Nginx Reverse Proxy Configuration${NC}"
echo "=============================================="
echo ""

PASSED=0
FAILED=0

test_result() {
    local test_name=$1
    local result=$2
    
    if [ $result -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $test_name"
        ((PASSED++))
    else
        echo -e "${RED}✗${NC} $test_name"
        ((FAILED++))
    fi
}

# Test 1: Nginx container is running
echo "Testing Nginx container..."
if docker-compose ps nginx | grep -q "Up"; then
    test_result "Nginx container is running" 0
else
    test_result "Nginx container is running" 1
fi

# Test 2: Health endpoint
echo "Testing health endpoint..."
if curl -sf http://localhost/health > /dev/null 2>&1; then
    test_result "Health endpoint responding" 0
else
    test_result "Health endpoint responding" 1
fi

# Test 3: Django reverse proxy
echo "Testing Django reverse proxy..."
if curl -s http://localhost/admin/ | grep -q "Django\|admin"; then
    test_result "Django reverse proxy working" 0
else
    test_result "Django reverse proxy working" 1
fi

# Test 4: X-Frame-Options header
echo "Testing security headers..."
if curl -sI http://localhost/ | grep -q "X-Frame-Options"; then
    test_result "X-Frame-Options header present" 0
else
    test_result "X-Frame-Options header present" 1
fi

# Test 5: X-Content-Type-Options header
if curl -sI http://localhost/ | grep -q "X-Content-Type-Options"; then
    test_result "X-Content-Type-Options header present" 0
else
    test_result "X-Content-Type-Options header present" 1
fi

# Test 6: CSP header
if curl -sI http://localhost/ | grep -q "Content-Security-Policy"; then
    test_result "Content-Security-Policy header present" 0
else
    test_result "Content-Security-Policy header present" 1
fi

# Test 7: Permissions-Policy header
if curl -sI http://localhost/ | grep -q "Permissions-Policy"; then
    test_result "Permissions-Policy header present" 0
else
    test_result "Permissions-Policy header present" 1
fi

# Test 8: Gzip compression
echo "Testing Gzip compression..."
GZIP_TEST=$(curl -sH "Accept-Encoding: gzip" -I http://localhost/static/admin/css/base.css 2>/dev/null | grep -i "Content-Encoding: gzip" || echo "")
if [ -n "$GZIP_TEST" ]; then
    test_result "Gzip compression enabled" 0
else
    test_result "Gzip compression enabled" 1
fi

# Test 9: Static files caching headers
echo "Testing static files..."
if curl -sI http://localhost/static/admin/css/base.css 2>/dev/null | grep -q "Cache-Control.*max-age"; then
    test_result "Static files have cache headers" 0
else
    test_result "Static files have cache headers" 1
fi

# Test 10: Nginx configuration validation
echo "Testing Nginx configuration..."
if docker-compose exec nginx nginx -t > /dev/null 2>&1; then
    test_result "Nginx configuration syntax valid" 0
else
    test_result "Nginx configuration syntax valid" 1
fi

# Test 11: Nginx worker processes
echo "Testing Nginx workers..."
WORKER_COUNT=$(docker-compose exec nginx ps aux | grep "[n]ginx: worker" | wc -l)
if [ $WORKER_COUNT -gt 0 ]; then
    test_result "Nginx worker processes running ($WORKER_COUNT)" 0
else
    test_result "Nginx worker processes running" 1
fi

# Test 12: Rate limiting zones configured
echo "Testing rate limiting..."
if docker-compose exec nginx grep -q "limit_req_zone" /etc/nginx/nginx.conf; then
    test_result "Rate limiting zones configured" 0
else
    test_result "Rate limiting zones configured" 1
fi

echo ""
echo "=============================================="
echo -e "Summary: ${GREEN}${PASSED} passed${NC}, ${RED}${FAILED} failed${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ Some tests failed!${NC}"
    exit 1
fi
