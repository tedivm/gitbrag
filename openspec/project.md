# Project Context

## Purpose

Git Brag is a tool that utilizes the GitHub API to generate comprehensive reports of open source contributions made over a specified period of time. The primary goal is to help developers create professional contribution reports that can be used for:

- Performance reviews and promotions
- Professional portfolio building
- Self-promotion and personal branding
- Demonstrating open source impact to employers or clients

The project provides both a CLI tool and a web interface for generating and viewing contribution reports. The web interface features GitHub OAuth authentication, persistent caching of reports, and shareable URLs for public viewing of contribution data.

## Tech Stack

### Core Technologies

- **Python 3.10+** - Primary programming language
- **FastAPI** - Web framework for API and web interface
- **Uvicorn** - ASGI server with standard extras
- **Typer** - CLI framework for command-line interface
- **Pydantic 2.x** - Data validation and settings management
- **Pydantic Settings** - Configuration management

### Authentication & Security

- **cryptography** - Fernet symmetric encryption for token storage
- **itsdangerous** - Session management and signing
- **GitHub OAuth** - Web-based authentication flow
- **Personal Access Tokens (PAT)** - CLI authentication

### Template & Caching

- **Jinja2** - Template engine for HTML rendering
- **aiocache** - Asynchronous caching framework
- **Redis** - Cache backend for sessions and report caching

### Development Tools

- **pytest** - Testing framework
- **pytest-asyncio** - Async test support
- **pytest-cov** - Coverage reporting
- **pytest-pretty** - Better test output
- **mypy** - Static type checking
- **ruff** - Linting and formatting
- **httpx** - HTTP client for testing and API calls
- **uv** - Fast Python package installer and version management
- **rich** - Rich text and beautiful formatting in terminal
- **build** - Package building tool
- **dapperdata** - Data transformation utilities
- **glom** - Nested data access and transformation
- **ruamel.yaml** - YAML processing

### Infrastructure

- **Docker** - Containerization
- **Docker Compose** - Local development environment
- **Redis** - Caching layer

## Project Conventions

### Code Style

**Formatting & Linting:**

- Use `ruff` for linting and formatting (120 character line length)
- Use `mypy` for static type checking with strict settings
- Enforce production-ready code only - no stubs or placeholders

**Naming Conventions:**

- All filenames must be lowercase for cross-platform compatibility
- Use snake_case for functions, variables, and module names
- Standard files (README.md, LICENSE, etc.) may use uppercase

**Import Organization:**

- Imports at the top of files (not inside functions unless preventing circular imports)
- No wildcard imports

### Architecture Patterns

**Async-First:**

- Prefer async libraries and functions over synchronous alternatives
- Use async/await throughout the codebase

**Configuration:**

- All settings managed via `pydantic-settings`
- Sensitive data uses Pydantic `SecretStr` or `SecretBytes`
- Settings defined with `Field()` including descriptions
- Unset settings default to `None` (not empty strings)
- Primary settings file: `gitbrag/conf/settings.py`
- Environment variables in `.env` (gitignored), with `.env.example` as template

**API Design (FastAPI):**

- REST principles with appropriate HTTP verbs (GET/PUT/POST/DELETE)
- Separate Pydantic models for input/output (e.g., `PostCreate`, `PostRead`)
- Use `Field()` for validation and descriptions in user input models

**CLI Design (Typer):**

- All user-accessible commands exposed via Typer
- Main entrypoint: `gitbrag/cli.py`

**Dependency Management:**

- All dependencies and tool settings in `pyproject.toml`
- Never use `setup.py` or `setup.cfg`
- Prefer existing dependencies over adding new ones
- Consider third-party libraries for complex functionality

**Code Organization:**

- Main package: `gitbrag/`
- CLI entrypoint: `gitbrag/cli.py`
- Web application: `gitbrag/www.py`
- Configuration: `gitbrag/conf/`
- Services: `gitbrag/services/`
  - GitHub API client: `gitbrag/services/github/`
  - Authentication: `gitbrag/services/github/auth.py`, `gitbrag/services/github/oauth.py`, `gitbrag/services/github/web_oauth.py`
  - PR collection: `gitbrag/services/github/pullrequests.py`
  - Star tracking: `gitbrag/services/github/stargazers.py`
  - Caching: `gitbrag/services/cache.py`
  - Report generation: `gitbrag/services/reports.py`
  - Formatting: `gitbrag/services/formatter.py`
  - Session management: `gitbrag/services/session.py`
  - Token encryption: `gitbrag/services/encryption.py`
  - Templates: `gitbrag/services/jinja.py`
- Static files: `gitbrag/static/`
- HTML templates: `gitbrag/templates/`
- Container files: `docker/`
- Developer docs: `docs/dev/`
- Tests: `tests/` (mirrors main code structure)

### Typing

**Strict Type Enforcement:**

- Type everything: function signatures, return values, variables
- Use union operator `|` for multiple types (e.g., `str | None`)
- Never use `Optional` - use union with `None` instead
- Use typing metaclasses: `Dict[str, str]`, `List[str]` (not `dict`, `list`)
- Avoid `Any` unless absolutely necessary
- Use dataclasses with typed parameters instead of `dict` when schema is known

### Testing Strategy

**Framework & Tools:**

- `pytest` for all testing
- `pytest-asyncio` for async tests
- `pytest-cov` for coverage tracking
- Coverage excludes: `_version.py`, `__init__.py`, `tests/`
- Concurrency: thread and greenlet support

**Test Structure:**

- Test file structure mirrors main code structure
- No class wrappers for test functions unless technically required
- All fixtures in `conftest.py` for availability across tests
- Avoid mocks for simple dataclasses/Pydantic models - create instances instead

**FastAPI Testing:**

- Use FastAPI Test Client via fixtures
- Never call router classes directly
- Include dependency overrides in app fixtures

**Test Requirements:**

- New code must include appropriate tests
- Tests must be production-ready

### Logging

**Standards:**

- Never use `print` - always use `getLogger` logger
- Each file gets its own logger using `__name__`
- Use logging levels for rich dev vs. production logging
- Most caught exceptions logged with `logger.exception`
- Never log sensitive data

### Error Handling

**Principles:**

- Do not suppress exceptions unless expected
- Log suppressed exceptions with `logger.exception`
- Handle exceptions properly when suppressing

### Security

**Requirements:**

- Always write secure code
- Never hardcode sensitive data
- Validate all user input
- Never roll custom cryptography

### Git Workflow

**Standards:**

- Use OpenSpec process for planning and proposals
- Follow best practices from `AGENTS.md`
- Standard gitignore includes `.venv` and `.env`

## Domain Context

### GitHub API Integration

The system integrates with the GitHub API to collect contribution data:

- **Authentication Methods**:
  - Personal Access Tokens (PAT) for CLI usage
  - GitHub OAuth flow for web-based authentication
  - Token encryption using Fernet (AES-128-CBC + HMAC-SHA256)

- **Data Collection**:
  - Pull requests (authored by user)
  - Repository information
  - Star counts and increases over time
  - Pagination handling for large result sets

- **API Considerations**:
  - Rate limit management and monitoring
  - Caching to minimize API calls
  - Public vs. private repository filtering
  - Time-based queries for contribution history

### Report Generation

The system provides multiple interfaces for generating and viewing contribution reports:

- **CLI Interface** (`gitbrag list`):
  - Terminal-based output with rich formatting
  - Configurable date ranges (1 year, 2 years, 5 years, all time)
  - Sorting options (repository, state, created, merged, title, stars)
  - Optional URL display and star increase tracking
  - Private repository inclusion support

- **Web Interface**:
  - HTML reports at `/user/github/{username}`
  - OAuth authentication flow
  - Session-based persistent authentication
  - Public caching for shareable reports
  - Responsive design for mobile and desktop
  - Date range selection via query parameters

- **Report Content**:
  - High-level summary (total PRs, merged count, etc.)
  - Repository-level breakdown
  - PR status categorization (open, merged, closed)
  - Time period analysis
  - Optional star increase tracking

### Caching Strategy

The system uses Redis for multiple caching purposes:

- **Session Storage**: Web session data with encrypted OAuth tokens
- **Profile Caching**: User profiles cached permanently with staleness checks (1 hour for authenticated refreshes)
- **Report Caching**: Generated reports cached to minimize GitHub API usage
- **Cache Keys**:
  - `profile:{username}` - User profile data
  - `profile:{username}:meta` - Profile metadata (cached_at timestamp)
  - Session data stored via itsdangerous session management

## Important Constraints

### Technical Constraints

- Python 3.10 minimum version requirement
- Production-ready code only - no development-specific logic branches in main package
- All code must be properly typed and pass mypy strict checks
- Must support async operations throughout
- Container-based deployment expected

### Code Quality Constraints

- No placeholder code or "for production" stubs
- All functions must have complete type signatures
- Comments must add value, not exist for sake of existing
- Test coverage required for new code

### Security Constraints

- No hardcoded credentials or sensitive data
- All sensitive configuration via SecretStr/SecretBytes
- OAuth tokens encrypted with Fernet (AES-128-CBC + HMAC-SHA256)
- PBKDF2 key derivation with 100,000 iterations
- Fixed salt for PBKDF2 (security from SESSION_SECRET_KEY, not salt)
- Session cookies with httponly, secure (production), and samesite=lax
- Input validation required
- No custom cryptography
- CSRF protection via state parameter in OAuth flow

## External Dependencies

### Required External Services

- **GitHub API** - Primary data source for contribution information
  - Authentication: Personal Access Tokens (CLI) and OAuth (Web)
  - Rate limiting considerations (both authenticated and unauthenticated)
  - REST API v3 for PR collection and user data
  - Supports both public and private repository access (with appropriate scopes)

- **Redis** - Required for caching and session management
  - Used via aiocache for caching framework
  - Session storage with encrypted token persistence
  - Profile caching with metadata tracking
  - Configured in docker-compose for development
  - Host/port/password configurable via settings
  - RDB persistence enabled for data durability

### Development Dependencies

- **Docker & Docker Compose** - Required for local development
  - Must support `docker compose up` for full environment
  - Services: web application (www) and Redis cache
  - Development environment configuration in `compose.yaml`
  - Dockerfile at `dockerfile.www` for web service
  - Pre-start script at `docker/www/prestart.sh`

### Build & Package Management

- **uv** - Fast Python package manager (replaces pip)
  - Automatic Python version handling
  - Significantly faster than traditional tools

## Current Implementation Status

### Implemented Features

**CLI Interface (gitbrag list command)**:

- ✅ Pull request collection by username and date range
- ✅ Flexible date range options (1 year, 2 years, 5 years, all time)
- ✅ Repository breakdown and statistics
- ✅ Multiple sort options (repository, state, created, merged, title, stars)
- ✅ Star increase tracking with `--show-star-increase` flag
- ✅ URL display toggle with `--show-urls` flag
- ✅ Private repository support with `--include-private` flag
- ✅ Rich terminal formatting and output
- ✅ Personal Access Token authentication

**Web Interface**:

- ✅ User report pages at `/user/github/{username}`
- ✅ GitHub OAuth authentication flow
- ✅ Session management with Redis storage
- ✅ Token encryption using Fernet
- ✅ Public caching of generated reports
- ✅ Profile caching with staleness checks (1 hour)
- ✅ Responsive HTML templates (base, home, user_report, error)
- ✅ Date range selection via query parameters
- ✅ Shareable URLs for public viewing
- ✅ Home page with feature showcase and example user
- ✅ Error handling and user-friendly error pages

**GitHub API Integration**:

- ✅ Pull request collection across all repositories
- ✅ Star count tracking and increase calculation
- ✅ Pagination handling for large result sets
- ✅ Rate limit monitoring and management
- ✅ Public and private repository filtering
- ✅ Authentication via PAT and OAuth
- ✅ Async HTTP client (httpx)

**Caching & Performance**:

- ✅ Redis-backed caching for all environments
- ✅ Profile caching (permanent with staleness checks)
- ✅ Session storage with encrypted tokens
- ✅ Graceful degradation (serve stale cache on API failures)

**Security**:

- ✅ Token encryption with Fernet (AES-128-CBC + HMAC-SHA256)
- ✅ PBKDF2 key derivation (100k iterations)
- ✅ Secure session cookies (httponly, secure, samesite)
- ✅ CSRF protection in OAuth flow
- ✅ No credential logging or exposure

**Configuration**:

- ✅ Pydantic settings with environment variable support
- ✅ Separate settings for GitHub auth, web, and cache
- ✅ Example username configuration
- ✅ `.env.example` template for developers

**Testing**:

- ✅ Comprehensive test suite (251 tests passing)
- ✅ 65% code coverage
- ✅ Integration tests for GitHub API
- ✅ Unit tests for services and utilities
- ✅ Async test support

### Architecture Overview

**Service Layer**:

- `github/client.py` - Async HTTP client for GitHub API
- `github/auth.py` - PAT authentication
- `github/oauth.py` - CLI OAuth flow
- `github/web_oauth.py` - Web OAuth flow
- `github/pullrequests.py` - PR collection logic
- `github/stargazers.py` - Star count tracking
- `reports.py` - Report generation and caching
- `formatter.py` - Output formatting for CLI
- `cache.py` - Cache configuration
- `encryption.py` - Token encryption utilities
- `session.py` - Web session management
- `jinja.py` - Template rendering

**Configuration Layer**:

- `conf/settings.py` - Main settings classes
- `conf/github.py` - GitHub-specific settings
- `conf/cache.py` - Cache configuration

**Interfaces**:

- `cli.py` - Typer-based CLI application
- `www.py` - FastAPI web application

### Known Limitations

- Only tracks pull requests (not commits, issues, or code reviews individually)
- Reports are generated on-demand (no scheduled generation)
- No database persistence (Redis cache only)
- No user accounts or profiles (OAuth session-based only)
- No PDF export or report customization UI
- Web interface requires authentication to generate new reports (though cached reports are publicly accessible)
