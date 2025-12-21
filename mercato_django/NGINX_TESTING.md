# Nginx Reverse Proxy Testing Guide

This document provides step-by-step instructions for testing the Nginx reverse proxy configuration.

## Prerequisites

- Docker and Docker Compose installed
- All services running: `docker-compose up -d`
- Nginx container healthy: `docker-compose ps nginx` shows "Up (healthy)"

## Test Procedures

### 1. Basic Connectivity

```bash
# Test that Nginx is responding
curl -I http://localhost/
# Expected: 200 OK with Django response

# Test health endpoint
curl http://localhost/health
# Expected: Response "healthy"

# Check Nginx logs for errors
docker-compose logs nginx
# Expected: No error logs
```

### 2. Reverse Proxy Verification

```bash
# Test Django app is being reached through Nginx
curl -v http://localhost/admin/
# Expected: 302 redirect to /admin/login/ (Django response)
# Verify X-Forwarded-For header in Nginx logs

# Check that request goes through Nginx
docker-compose logs nginx | tail -5
# Expected: Access log entries for /admin/
```

### 3. Static Files Test

```bash
# Verify static files are served by Nginx (not Django)
curl -I http://localhost/static/admin/css/base.css
# Expected: 200 OK with cache headers:
# Cache-Control: public, max-age=2592000
# Content-Encoding: gzip (if requesting with Accept-Encoding: gzip)

# Verify static files don't go through Django
# Check Nginx logs - should show direct serving
docker-compose logs nginx | grep "static/admin/css"
# Expected: Direct serving from /var/www/static/
```

### 4. Media Files Test

```bash
# Verify media directory is accessible
curl -I http://localhost/media/
# Expected: Either 403 Forbidden (directory listing denied) or 404 if no index

# Verify media files are served with proper headers
# First, you need to have a media file
# Expected Cache-Control: public, max-age=604800 (7 days)
```

### 5. Security Headers Verification

```bash
# Check all security headers are present
curl -I http://localhost/ | grep -E "X-Frame|X-Content-Type|X-XSS|Referrer|CSP|Permissions"

# Expected output:
# X-Frame-Options: DENY
# X-Content-Type-Options: nosniff
# X-XSS-Protection: 1; mode=block
# Referrer-Policy: strict-origin-when-cross-origin
# Content-Security-Policy: default-src 'self'; ...
# Permissions-Policy: accelerometer=(); ...
```

### 6. Gzip Compression Test

```bash
# Test gzip compression is working
curl -H "Accept-Encoding: gzip" -I http://localhost/static/admin/css/base.css
# Expected: Content-Encoding: gzip

# Test without compression
curl -I http://localhost/static/admin/css/base.css | grep "Content-Encoding"
# Expected: No Content-Encoding header

# Verify compression is reducing size
# With compression:
curl -H "Accept-Encoding: gzip" -s http://localhost/static/admin/css/base.css | wc -c
# Without compression:
curl -s http://localhost/static/admin/css/base.css | wc -c
# Expected: Compressed size is significantly smaller
```

### 7. Rate Limiting Test

```bash
# Test that rate limiting is applied
# API rate limiting (10 req/s)
for i in {1..15}; do curl -s -o /dev/null http://localhost/api/ & done
wait
# Expected: Some requests return 503 Service Unavailable

# Login rate limiting (1 req/s)
for i in {1..5}; do curl -s -o /dev/null http://localhost/login -X POST & done
wait
# Expected: Requests after 1st return 503
```

### 8. Caching Headers Test

```bash
# Static files should have long expiration
curl -I http://localhost/static/admin/js/admin/base.js
# Expected: Cache-Control: public, max-age=2592000 (30 days)
# Expected: Pragma: public

# Images/fonts should have even longer cache
curl -I http://localhost/static/admin/img/icon-yes.svg
# Expected: Cache-Control: public, max-age=31536000, immutable (1 year)

# Media files should cache for 7 days
# curl -I http://localhost/media/sample.jpg
# Expected: Cache-Control: public, max-age=604800
```

### 9. CORS Headers Test

```bash
# Test CORS headers for static files
curl -I -H "Origin: http://example.com" http://localhost/static/test.css
# Expected:
# Access-Control-Allow-Origin: *
# Access-Control-Allow-Methods: GET, HEAD, OPTIONS
# Access-Control-Allow-Headers: DNT,User-Agent,...

# Test OPTIONS request
curl -I -X OPTIONS http://localhost/static/test.css
# Expected: 204 No Content
```

### 10. Configuration Validation

```bash
# Validate Nginx configuration syntax
docker-compose exec nginx nginx -t
# Expected: nginx: configuration file /etc/nginx/nginx.conf syntax is ok

# Check active worker processes
docker-compose exec nginx ps aux | grep "[n]ginx"
# Expected: Multiple nginx worker processes running

# Verify listening ports
docker-compose exec nginx netstat -tlnp | grep nginx
# Expected: Listening on 0.0.0.0:80 and 0.0.0.0:443
```

### 11. Performance Testing

```bash
# Simple load test
# Using Apache Bench (if installed)
ab -n 100 -c 10 http://localhost/

# Check response times
curl -w "Total time: %{time_total}s\n" http://localhost/
# Expected: Response time < 1 second

# Monitor resource usage during load
docker stats nginx
# Expected: CPU and memory usage within reasonable limits
```

### 12. Logging Verification

```bash
# Check access logs format
docker-compose exec nginx tail -10 /var/log/nginx/access.log
# Expected: Log entries include IP, timestamp, request, status, response time

# Check error logs
docker-compose exec nginx tail -10 /var/log/nginx/error.log
# Expected: No critical errors

# Check cache status in logs
docker-compose exec nginx grep 'cache=' /var/log/nginx/access.log | head -5
# Expected: Entries with cache=HIT or cache=MISS
```

## Docker Container Health Check

```bash
# View Nginx container status
docker-compose ps nginx
# Expected status: Up (healthy)

# Check health check details
docker inspect mercatopro_nginx | grep -A 10 "Health"
# Expected: Status is "healthy"
```

## Troubleshooting Test Failures

### 502 Bad Gateway
```bash
# Check if Django container is running
docker-compose ps web
# Should be Up and healthy

# Check Nginx error logs
docker-compose logs nginx | grep "502\|upstream"

# Test Django directly (without Nginx)
curl http://web:8000/health
```

### 403 Forbidden on Static Files
```bash
# Check volume mounts
docker-compose exec nginx ls -la /var/www/static/
# Should list static files

# Check permissions
docker-compose exec nginx ls -la /var/www/ | grep static
# Should be readable by nginx user

# Verify Django collectstatic was run
docker-compose exec web ls -la /app/staticfiles/
```

### Rate Limiting Not Working
```bash
# Check rate limiting zones are configured
docker-compose exec nginx grep "limit_req_zone" /etc/nginx/nginx.conf

# Check access logs for rate limiting responses
docker-compose exec nginx grep "429\|503" /var/log/nginx/access.log
```

### Compression Not Working
```bash
# Verify gzip is enabled
docker-compose exec nginx grep "gzip on" /etc/nginx/nginx.conf

# Check which MIME types are being compressed
docker-compose exec nginx grep -A 20 "gzip_types" /etc/nginx/nginx.conf
```

## Automated Test Script

Create a test script `test_nginx.sh`:

```bash
#!/bin/bash

set -e

echo "🧪 Testing Nginx Reverse Proxy Configuration"
echo "=============================================="

# Test 1: Health check
echo "1. Testing health endpoint..."
curl -f http://localhost/health > /dev/null
echo "   ✓ Health endpoint working"

# Test 2: Django reverse proxy
echo "2. Testing Django reverse proxy..."
curl -s -o /dev/null -w "   ✓ Response status: %{http_code}\n" http://localhost/admin/ | grep -q "302\|200"

# Test 3: Security headers
echo "3. Checking security headers..."
curl -s -I http://localhost/ | grep -q "X-Frame-Options"
echo "   ✓ X-Frame-Options present"
curl -s -I http://localhost/ | grep -q "X-Content-Type-Options"
echo "   ✓ X-Content-Type-Options present"
curl -s -I http://localhost/ | grep -q "Content-Security-Policy"
echo "   ✓ Content-Security-Policy present"

# Test 4: Gzip compression
echo "4. Testing Gzip compression..."
curl -s -H "Accept-Encoding: gzip" -I http://localhost/static/admin/css/base.css | grep -q "Content-Encoding: gzip"
echo "   ✓ Gzip compression working"

# Test 5: Nginx configuration
echo "5. Validating Nginx configuration..."
docker-compose exec nginx nginx -t > /dev/null 2>&1
echo "   ✓ Configuration syntax valid"

echo ""
echo "✅ All tests passed!"
```

Run with: `bash test_nginx.sh`

## Performance Benchmarks

Expected performance metrics:

- **Response Time**: < 100ms for static files, < 200ms for dynamic content
- **Throughput**: > 1000 requests/sec for static files
- **Compression Ratio**: ~60% reduction for text-based assets
- **Cache Hit Rate**: > 95% for static files after initial load
- **Memory Usage**: < 50MB for Nginx process
- **CPU Usage**: < 5% at normal load

## Security Validation

Checklist for security validation:

- [ ] X-Frame-Options header set to DENY
- [ ] X-Content-Type-Options header set to nosniff
- [ ] X-XSS-Protection header enabled
- [ ] Content-Security-Policy header configured
- [ ] Referrer-Policy header set
- [ ] Permissions-Policy header configured
- [ ] No server version disclosure (Server header hidden)
- [ ] HTTPS ready (SSL directory present, config available)
- [ ] Rate limiting active on sensitive endpoints
- [ ] Script execution blocked in media folder
- [ ] Hidden files and backup files blocked
- [ ] Proper cache headers on static files

## Conclusion

If all tests pass, the Nginx reverse proxy is properly configured and ready for:
- Development use (current setup)
- Production deployment (after enabling HTTPS and production optimizations)
