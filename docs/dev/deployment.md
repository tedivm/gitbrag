# Deployment Guide

This guide covers deploying GitBrag using Docker containers for production environments.

## Overview

GitBrag is designed to run in containers with the following components:

- **Web Application**: FastAPI application serving the web interface
- **Redis**: Cache layer for performance optimization
- **Persistent Storage**: Volume for Redis data persistence

## Prerequisites

- Docker Engine 20.10 or higher
- Docker Compose 2.0 or higher
- GitHub OAuth App credentials (for authentication)

## Production Deployment with Docker Compose

### 1. Create Project Directory

```bash
mkdir gitbrag-deployment
cd gitbrag-deployment
```

### 2. Create Docker Compose Configuration

Create a `compose.yaml` file:

```yaml
services:
  www:
    image: ghcr.io/tedivm/gitbrag:latest
    ports:
      - "80:80"
    environment:
      # Application settings
      PROJECT_NAME: gitbrag
      # Note: Boolean values must be quoted in YAML environment sections
      # YAML interprets unquoted true/false as boolean types, but environment
      # variables are always strings. Quoting ensures consistent behavior.
      DEBUG: "false"

      # Cache configuration
      CACHE_ENABLED: "true"
      CACHE_REDIS_HOST: redis
      CACHE_REDIS_PORT: 6379
      CACHE_DEFAULT_TTL: 300
      CACHE_PERSISTENT_TTL: 86400

      # GitHub OAuth (required for web interface)
      GITHUB_AUTH_TYPE: github_app
      GITHUB_APP_CLIENT_ID: ${GITHUB_APP_CLIENT_ID}
      GITHUB_APP_CLIENT_SECRET: ${GITHUB_APP_CLIENT_SECRET}

      # Web interface settings
      SESSION_SECRET_KEY: ${SESSION_SECRET_KEY}
      SESSION_MAX_AGE: 86400
      OAUTH_CALLBACK_URL: ${OAUTH_CALLBACK_URL}
      REQUIRE_HTTPS: "true"
      OAUTH_SCOPES: read:user

      # Cache staleness (24 hours)
      REPORT_CACHE_STALE_AGE: 86400
    depends_on:
      - redis
    restart: unless-stopped
    networks:
      - gitbrag

  redis:
    image: redis:7-alpine
    command: redis-server --save 60 1000 --save 300 100 --save 900 1
    volumes:
      - redis-data:/data
    restart: unless-stopped
    networks:
      - gitbrag
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3

volumes:
  redis-data:
    driver: local

networks:
  gitbrag:
    driver: bridge
```

### 3. Create Environment Configuration

Create a `.env` file with your production settings:

```bash
# GitHub OAuth App credentials
GITHUB_APP_CLIENT_ID=your_client_id_here
GITHUB_APP_CLIENT_SECRET=your_client_secret_here

# Session security (generate with: python -c "import secrets; print(secrets.token_urlsafe(32))")
SESSION_SECRET_KEY=your_secure_random_key_here

# OAuth callback URL (update with your domain)
OAUTH_CALLBACK_URL=https://yourdomain.com/auth/callback
```

**Important**: Never commit the `.env` file to version control. Keep your secrets secure.

### 4. Deploy the Application

```bash
# Start services in detached mode
docker compose up -d

# Check service status
docker compose ps

# View logs
docker compose logs -f www
```

### 5. Verify Deployment

```bash
# Check if services are running
docker compose ps

# Test Redis connection
docker compose exec redis redis-cli ping
# Should return: PONG

# Check application logs
docker compose logs www
```

## Data Persistence

The Redis container uses a named volume (`redis-data`) for persistence with RDB (snapshot) mode:

- **Snapshot Policy**: `--save 60 1000 --save 300 100 --save 900 1`
  - Save if 1 key changed in 900 seconds (15 minutes)
  - Save if 100 keys changed in 300 seconds (5 minutes)
  - Save if 1000 keys changed in 60 seconds (1 minute)
- **Data Directory**: `/data` inside the container, mapped to the `redis-data` volume
- **Trade-off**: Better disk space efficiency than AOF; potential data loss limited to last snapshot interval

**Why RDB?** For GitBrag's caching use case:

- Cache data can be regenerated from GitHub API if lost
- Smaller disk footprint - avoids AOF log growth
- Faster performance compared to AOF
- Acceptable trade-off: losing up to 15 minutes of cached reports just means slower responses, not data loss

### Backup Redis Data

```bash
# Create a backup
docker compose exec redis redis-cli BGSAVE

# Copy the backup file from the container
docker compose cp redis:/data/dump.rdb ./backup-$(date +%Y%m%d).rdb
```

### Restore Redis Data

```bash
# Stop the services
docker compose down

# Copy backup file to volume (requires starting a temporary container)
docker run --rm -v gitbrag-deployment_redis-data:/data -v $(pwd):/backup \
  alpine cp /backup/backup-YYYYMMDD.rdb /data/dump.rdb

# Start services
docker compose up -d
```

## Scaling and Performance

### Resource Limits

Add resource limits to your `compose.yaml`:

```yaml
services:
  www:
    # ... other settings ...
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M

  redis:
    # ... other settings ...
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 128M
```

### Horizontal Scaling

To run multiple web instances behind a load balancer:

```yaml
services:
  www:
    # ... other settings ...
    deploy:
      replicas: 3
    ports: []  # Remove direct port binding

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - www
```

## Monitoring and Maintenance

### Health Checks

View health status:

```bash
docker compose ps
```

### Log Management

```bash
# View recent logs
docker compose logs --tail=100 www

# Follow logs in real-time
docker compose logs -f www redis

# View logs for specific time period
docker compose logs --since 1h www
```

### Cache Management

```bash
# Clear all cached data
docker compose exec redis redis-cli FLUSHALL

# View cache statistics
docker compose exec redis redis-cli INFO stats

# Check memory usage
docker compose exec redis redis-cli INFO memory
```

### Updates

```bash
# Pull latest image
docker compose pull

# Recreate containers with new image
docker compose up -d

# Remove old images
docker image prune -f
```

## Security Considerations

### Environment Variables

- Generate strong random keys for `SESSION_SECRET_KEY`
- Never expose `.env` files publicly
- Use Docker secrets for sensitive data in production orchestrators

### Network Security

- Use HTTPS in production (set `REQUIRE_HTTPS=true`)
- Configure firewall rules to restrict access
- Use Docker networks to isolate services

### Container Security

```yaml
services:
  www:
    # ... other settings ...
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
    cap_drop:
      - ALL
```

## Reverse Proxy Configuration

### Nginx Example

```nginx
upstream gitbrag {
    server localhost:8080;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    location / {
        proxy_pass http://gitbrag;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Update your `compose.yaml` to bind to localhost only:

```yaml
services:
  www:
    ports:
      - "127.0.0.1:8080:80"
```

## Troubleshooting

### Application Won't Start

```bash
# Check logs for errors
docker compose logs www

# Verify environment variables
docker compose config

# Check if ports are available
netstat -tuln | grep 80
```

### Redis Connection Issues

```bash
# Test Redis connectivity
docker compose exec redis redis-cli ping

# Check network connectivity
docker compose exec www ping redis

# Verify Redis is accepting connections
docker compose exec redis redis-cli INFO server
```

### Performance Issues

```bash
# Check container resource usage
docker stats

# Monitor Redis performance
docker compose exec redis redis-cli --latency

# Check for slow queries
docker compose exec redis redis-cli SLOWLOG GET 10
```

## Alternative Deployment: Single Container

For simpler deployments without external Redis:

```bash
docker run -d \
  --name gitbrag \
  -p 80:80 \
  -e CACHE_ENABLED="false" \
  -e GITHUB_APP_CLIENT_ID=your_client_id \
  -e GITHUB_APP_CLIENT_SECRET=your_secret \
  -e SESSION_SECRET_KEY=your_session_key \
  -e OAUTH_CALLBACK_URL=https://yourdomain.com/auth/callback \
  -e REQUIRE_HTTPS="true" \
  ghcr.io/tedivm/gitbrag:latest
```

**Note**: Without Redis, performance will be reduced as reports won't be cached.

## Next Steps

- Configure a reverse proxy with SSL/TLS certificates
- Set up automated backups for Redis data
- Implement monitoring with Prometheus/Grafana
- Configure log aggregation (ELK stack, Loki, etc.)
- Review and adjust cache TTL settings based on usage patterns

For development deployment, see [Docker](./docker.md).
