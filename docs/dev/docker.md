# Docker

This project includes Docker containerization for all services, making it easy to develop, test, and deploy in consistent environments across different platforms.

## Docker Images

The project uses specialized base images from the Multi-Py project, optimized for different Python workloads:

### FastAPI (Web Server)

**Base Image**: [ghcr.io/multi-py/python-uvicorn](https://github.com/multi-py/python-uvicorn)

The FastAPI image is built on the Multi-Py Uvicorn base, providing:

- Pre-configured Uvicorn ASGI server
- Automatic hot-reload in development mode
- Production-ready performance optimizations
- Health check endpoints
- Graceful shutdown handling

**Dockerfile**: `dockerfile.www`

```dockerfile
ARG PYTHON_VERSION=3.14
FROM ghcr.io/multi-py/python-uvicorn:py${PYTHON_VERSION}-slim-LATEST

ENV APP_MODULE=gitbrag.www:app

# Install uv for fast package installation
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY pyproject.toml uv.lock /app/
WORKDIR /app

# Install dependencies from lockfile (no dev dependencies)
RUN uv sync --frozen --no-dev

# Copy application code
COPY ./docker/www/prestart.sh /app/prestart.sh
COPY . /app/
```

**Key Features**:

- Automatically runs `prestart.sh` before starting Uvicorn
- Supports hot-reload via `RELOAD=true` environment variable
- Runs on port 80 by default
- Includes health check support

## Docker Compose

The project includes a `compose.yaml` file for orchestrating all services in development and testing.

### Services Overview

**www**: FastAPI web server

- Port: 80 (host) → 80 (container)
- Hot-reload enabled in development
- Volume-mounted source code for live updates

**redis**: Redis cache and message broker

- Used for Celery task queue
- Used for distributed caching
- Persists data to disk by default

### Running with Docker Compose

```bash
# Start all services
docker-compose up

# Start in detached mode (background)
docker-compose up -d

# Start specific service
docker-compose up www

# View logs
docker-compose logs -f

# View logs for specific service
docker-compose logs -f www

# Stop all services
docker-compose down

# Stop and remove volumes (deletes database data!)
docker-compose down -v
```

### Scaling Services

## Environment Variables in Docker

Environment variables are configured in `compose.yaml` for development:

### Common Variables

- **IS_DEV**: Set to `true` to enable development features
- **RELOAD**: Set to `true` to enable hot-reload in Uvicorn

### Cache Configuration

- **CACHE_REDIS_HOST**: `redis`
- **CACHE_REDIS_PORT**: `6379`

### Override Environment Variables

Create a `.env` file in the project root to override default values:

```bash
# .env file
DATABASE_URL=postgresql://custom_user:custom_pass@db/custom_db
DEBUG=True
CACHE_ENABLED=True
```

Docker Compose automatically loads `.env` files.

## Volume Mounts for Development

The compose file mounts source code as volumes for live development:

```yaml
volumes:
  - "./gitbrag:/app/gitbrag"  # Source code
  - "./db:/app/db"                                                             # Migration scripts
  - "./docker/www/prestart.sh:/app/prestart.sh"                               # Startup script
```

**Benefits**:

- Code changes are immediately reflected in the container
- No need to rebuild images during development
- Fast iteration cycle

**Note**: Volume mounts should NOT be used in production. Production images should have code baked in during build.

## Building Images

### Build All Images

```bash
# Build all services
docker-compose build

# Build with no cache (clean build)
docker-compose build --no-cache

# Build specific service
docker-compose build www
```

### Build for Production

Production images should not use volume mounts:

```bash
# Build production image
docker build -f dockerfile.www -t gitbrag-www:latest .

# Tag for registry
docker tag gitbrag-www:latest ghcr.io/your-org/gitbrag-www:latest

# Push to registry
docker push ghcr.io/your-org/gitbrag-www:latest
```

## Docker Ignore File

The project includes a `.dockerignore` file that controls which files are copied into Docker images during the build process.

### Default Ignore Strategy

The `.dockerignore` file uses a **deny-by-default** approach for maximum security and minimal image size:

```
# Ignore everything by default
*

# Explicitly allow only what's needed
!/gitbrag
!/.python-version
!/db
!/docker
!/alembic.ini
!/LICENSE
!/makefile
!/pyproject.toml
!/README.md
!/setup.*
!/requirements*
```

**Why deny-by-default?**

- **Security**: Prevents accidentally including sensitive files (`.env`, credentials, SSH keys)
- **Image Size**: Keeps images small by excluding unnecessary files
- **Build Speed**: Reduces build context size for faster builds
- **Explicit Control**: You must consciously decide what goes into the image

### Adding New Files to Docker Images

When you add new files or directories that need to be in the Docker image, you **must update `.dockerignore`**:

```bash
# Example: Adding a new static assets directory
!/static

# Example: Adding a configuration directory
!/config

# Example: Adding documentation that should be in the image
!/docs
```

**Important**: The `!` prefix means "don't ignore this" (include it).

### Common Files to Keep Excluded

These should remain excluded from Docker images:

```
.git/              # Git repository data
.venv/             # Virtual environments
__pycache__/       # Python bytecode cache
*.pyc              # Compiled Python files
.pytest_cache/     # Test cache
.env               # Environment variables file
.env.*             # Environment variable variants
node_modules/      # Node.js dependencies (if applicable)
.DS_Store          # macOS metadata
*.log              # Log files
.coverage          # Coverage reports
htmlcov/           # Coverage HTML reports
dist/              # Distribution builds
*.egg-info/        # Python package metadata
```

### Troubleshooting Missing Files

If your Docker container is missing files you expect:

1. **Check `.dockerignore`**: Ensure the file/directory is explicitly allowed

   ```bash
   # View what's being excluded
   cat .dockerignore
   ```

2. **Test the build context**:

   ```bash
   # See what files Docker will copy
   docker build --no-cache -f dockerfile.www --progress=plain . 2>&1 | grep "COPY"
   ```

3. **Add the missing path**:

   ```
   # In .dockerignore, add:
   !/path/to/your/file
   ```

4. **Rebuild the image**:

   ```bash
   docker-compose build --no-cache
   ```

### Example: Adding Custom Templates

If you add custom templates outside the main package:

```
gitbrag/
templates/           # Custom templates directory (new)
gitbrag/
```

Update `.dockerignore`:

```
# ... existing entries ...
!/templates
```

## Multi-Stage Builds

The base images from Multi-Py already use multi-stage builds for optimization. You can extend them for additional optimization:

```dockerfile
# Example: Multi-stage build with build dependencies
FROM ghcr.io/multi-py/python-uvicorn:py3.14-slim-LATEST AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y gcc g++ make

# Install uv and Python packages
RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock /app/
WORKDIR /app
RUN uv sync --frozen --no-dev

# Final stage - copy only what's needed
FROM ghcr.io/multi-py/python-uvicorn:py3.14-slim-LATEST

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.14/site-packages/ /usr/local/lib/python3.14/site-packages/

# Copy application
COPY ./ /app
```

## Prestart Scripts

Each service includes a prestart script that runs before the main application:

### FastAPI Prestart (`docker/www/prestart.sh`)

The FastAPI prestart script:

1. **Waits for database**: Uses `netcat` to check PostgreSQL availability
2. **Runs migrations**: Executes `alembic upgrade head` automatically
3. **Creates test data**: If `CREATE_TEST_DATA` is set, populates the database

```bash
#!/usr/bin/env bash


```

## Development vs Production

### Development Configuration

**docker-compose.yaml** is optimized for development:

- Volume mounts for live code updates
- Hot-reload enabled
- Debug logging enabled
- Exposed ports for direct access
- Simple passwords and credentials

```bash
# Start development environment
docker-compose up

# Your code changes are immediately reflected
# No need to rebuild images
```

### Production Configuration

For production, create a separate `docker-compose.prod.yaml`:

```yaml
services:
  www:
    image: ghcr.io/your-org/gitbrag-www:latest
    restart: always
    # NO volume mounts - code is in image
    ports:
      - "8000:80"  # Don't expose on port 80 directly
    environment:
      IS_DEV: false
      RELOAD: false
      DATABASE_URL: ${DATABASE_URL}  # Load from secure secrets
      SECRET_KEY: ${SECRET_KEY}
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '1'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
```

**Production Best Practices**:

1. Use tagged image versions (not `latest`)
2. Load secrets from secure stores (not .env files)
3. Don't expose internal ports
4. Configure resource limits
5. Enable restart policies
6. Use health checks
7. Run behind a reverse proxy (nginx, Traefik)

## Debugging in Docker

### View Container Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f www

# Last 100 lines
docker-compose logs --tail=100 www
```

### Execute Commands in Running Containers

```bash
# Open shell in container
docker-compose exec www bash

# Run a command
docker-compose exec www python -m gitbrag.cli version

# Check database connection
docker-compose exec www python -c "from gitbrag.services.db import engine; print(engine)"
```

### Debug Application Code

Add this to your FastAPI code for interactive debugging:

```python
import debugpy

# Enable remote debugging on port 5678
debugpy.listen(("0.0.0.0", 5678))
print("Waiting for debugger to attach...")
debugpy.wait_for_client()
```

Then expose the port in compose:

```yaml
services:
  www:
    ports:
      - "80:80"
      - "5678:5678"  # Debugger port
```

## Health Checks

Add health checks to ensure containers are running properly:

```yaml
services:
  www:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost/docs"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

## Resource Limits

Configure resource limits to prevent containers from consuming excessive resources:

```yaml
services:
  www:
    deploy:
      resources:
        limits:
          cpus: '2'      # Maximum 2 CPU cores
          memory: 1G     # Maximum 1GB RAM
        reservations:
          cpus: '0.5'    # Guaranteed 0.5 CPU cores
          memory: 512M   # Guaranteed 512MB RAM
```

## Container Registry

Images are automatically built and published to the GitHub Container Registry (ghcr.io) using GitHub Actions:

### Automated Image Building

On every push to main:

1. GitHub Actions builds Docker images
2. Images are tagged with:
   - `latest` for the main branch
   - Git commit SHA for traceability
   - Version tags from releases
3. Images are pushed to `ghcr.io/tedivm/gitbrag`

### Pull Images from Registry

```bash
# Pull latest image
docker pull ghcr.io/tedivm/gitbrag-www:latest

# Pull specific version
docker pull ghcr.io/tedivm/gitbrag-www:v1.2.3

# Use in docker-compose
services:
  www:
    image: ghcr.io/tedivm/gitbrag-www:latest
```

See [GitHub Actions Documentation](./github.md) for more details on CI/CD workflows.

## Networking

Docker Compose automatically creates a network for service communication:

- Services can reference each other by service name
- Example: `postgresql://user:pass@db/dbname` (where `db` is the service name)
- Internal communication doesn't require port exposure

### Custom Networks

For complex setups, define custom networks:

```yaml
services:
  www:
    networks:
      - frontend
      - backend

  db:
    networks:
      - backend

networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
    internal: true  # No external access
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs for errors
docker-compose logs www

# Check container status
docker-compose ps

# Rebuild without cache
docker-compose build --no-cache www
docker-compose up www
```

### Port Already in Use

If port 80 is already in use, modify the port mapping in `compose.yaml`:

```yaml
services:
  www:
    ports:
      - "8080:80"  # Use port 8080 on host instead
```

### Out of Disk Space

```bash
# Remove unused images and containers
docker system prune

# Remove all stopped containers, unused images, and volumes
docker system prune -a --volumes
```

## Best Practices

1. **Use .dockerignore**: This project uses a deny-by-default `.dockerignore` strategy. When adding new files/directories to your project that need to be in Docker images, you must explicitly allow them in `.dockerignore`. See the [Docker Ignore File](#docker-ignore-file) section for details.

2. **Layer caching**: Order Dockerfile commands from least to most frequently changed

   ```dockerfile
   # Install uv first (changes rarely)
   RUN pip install --no-cache-dir uv
   # Install dependencies (changes when pyproject.toml or lockfile changes)
   COPY pyproject.toml uv.lock /app/
   WORKDIR /app
   RUN uv sync --frozen --no-dev
   # Copy code (changes frequently)
   COPY . /app/
   ```

3. **Don't run as root**: Use non-root users in production (Multi-Py images handle this)

4. **Keep images small**: Use slim base images and multi-stage builds

5. **Use specific tags**: Never use `latest` in production

6. **Health checks**: Always define health checks for production containers

7. **Logs to stdout**: All application logs should go to stdout/stderr (already configured)

8. **Secrets management**: Never hardcode secrets, use environment variables or secrets managers

## References

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Multi-Py Uvicorn Images](https://github.com/multi-py/python-uvicorn)
- [Multi-Py Celery Images](https://github.com/multi-py/python-celery)
- [Best Practices for Writing Dockerfiles](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)
