# Project Context

## Purpose

GitBrag is a tool that utilizes the GitHub API to generate comprehensive reports of open source contributions made over a specified period of time. The primary goal is to help developers create professional contribution reports that can be used for:

- Performance reviews and promotions
- Professional portfolio building
- Self-promotion and personal branding
- Demonstrating open source impact to employers or clients

This is a greenfield project currently in the template/planning phase, with no production code yet implemented.

## Tech Stack

### Core Technologies

- **Python 3.10+** - Primary programming language
- **FastAPI** - Web framework for API and web interface
- **Uvicorn** - ASGI server with standard extras
- **Typer** - CLI framework for command-line interface
- **Pydantic 2.x** - Data validation and settings management
- **Pydantic Settings** - Configuration management

### Template & Caching

- **Jinja2** - Template engine for HTML rendering
- **aiocache** - Asynchronous caching framework
- **Redis** - Cache backend

### Development Tools

- **pytest** - Testing framework
- **pytest-asyncio** - Async test support
- **pytest-cov** - Coverage reporting
- **pytest-pretty** - Better test output
- **mypy** - Static type checking
- **ruff** - Linting and formatting
- **httpx** - HTTP client for testing and API calls
- **uv** - Fast Python package installer and version management

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

- Database models: `gitbrag/models/`
- Configuration: `gitbrag/conf/`
- Services: `gitbrag/services/`
- Container files: `docker/`
- Developer docs: `docs/dev/`

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

- Primary external data source is the GitHub API
- Need to track various contribution types:
  - Commits
  - Pull requests
  - Issues
  - Code reviews
  - Repository contributions
- Time-based queries for contribution history
- Must handle API rate limiting and authentication

### Report Generation

- Generate human-readable contribution summaries
- Support various time periods (weekly, monthly, quarterly, annual)
- Format suitable for professional contexts (promotions, reviews)
- Web interface for viewing reports
- CLI for generating reports

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
- Input validation required
- No custom cryptography

## External Dependencies

### Required External Services

- **GitHub API** - Primary data source for contribution information
  - Authentication required (personal access tokens or OAuth)
  - Rate limiting considerations
  - REST API v3 or GraphQL API v4

- **Redis** - Required for caching layer
  - Used via aiocache
  - Configured in docker-compose for development
  - Host/port configurable via settings

### Development Dependencies

- **Docker & Docker Compose** - Required for local development
  - Must support `docker compose up` for full environment
  - Development environment pre-populated with test data

### Build & Package Management

- **uv** - Fast Python package manager (replaces pip)
  - Automatic Python version handling
  - Significantly faster than traditional tools
