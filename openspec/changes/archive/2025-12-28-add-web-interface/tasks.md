# Implementation Tasks: Web Interface

This document outlines the ordered tasks for implementing the web interface. Tasks should be completed sequentially, with testing after each major milestone.

## Phase 1: Configuration and Dependencies

### Task 1.1: Add web-specific settings

- [ ] Add `WebSettings` class to `gitbrag/conf/settings.py`
- [ ] Include fields: `session_secret_key`, `session_max_age`, `oauth_callback_url`, `require_https`
- [ ] Use `SecretStr` for `session_secret_key`
- [ ] Set appropriate defaults for development
- [ ] Update `.env.example` with new settings and documentation
- [ ] **Validation**: Settings load correctly and are accessible in tests

**Dependencies**: None

### Task 1.2: Verify FastAPI and session middleware dependencies

- [ ] Confirm `fastapi` is in `pyproject.toml` dependencies (already present)
- [ ] Confirm `jinja2` is in dependencies (already present)
- [ ] Confirm `redis` is in dependencies (already present)
- [ ] Add `cryptography` for token encryption if not already present
- [ ] Add `itsdangerous` for session signing if not already present (FastAPI dependency)
- [ ] **Validation**: Run `uv pip list` and verify all dependencies are installed

**Dependencies**: None (can run in parallel with 1.1)

## Phase 2: Session Management

### Task 2.1: Create session middleware configuration

- [ ] Create `gitbrag/services/session.py` module
- [ ] Implement function to configure `SessionMiddleware` with settings
- [ ] Use Redis as session backend via `aiocache`
- [ ] Configure secure cookie settings (httponly, secure in prod, samesite=lax)
- [ ] Set session TTL to 24 hours
- [ ] **Validation**: Unit tests for session configuration

**Dependencies**: Task 1.1

### Task 2.2: Create token encryption module

- [ ] Create `gitbrag/services/encryption.py` module
- [ ] Implement `encrypt_token()` function using cryptography.fernet.Fernet
- [ ] Implement `decrypt_token()` function
- [ ] Derive encryption key from `session_secret_key` using PBKDF2
- [ ] Handle decryption failures gracefully (return None or raise specific exception)
- [ ] Use SecretStr for all token handling
- [ ] **Validation**: Unit tests for encryption/decryption round-trip

**Dependencies**: Task 1.1, Task 1.2

### Task 2.3: Create session helper functions

- [ ] Add `get_session()` helper to retrieve session from request
- [ ] Add `set_session()` helper to store data in session
- [ ] Add `clear_session()` helper to delete session
- [ ] Add `get_session_token()` helper to retrieve and decrypt OAuth token from session
- [ ] Integrate encryption module for token storage/retrieval
- [ ] **Validation**: Unit tests for all helper functions

**Dependencies**: Task 2.1, Task 2.2

## Phase 3: Web OAuth Implementation

### Task 3.1: Create web OAuth flow service

- [ ] Create `gitbrag/services/github/web_oauth.py` module
- [ ] Implement `generate_state()` function for CSRF state parameter
- [ ] Implement `get_authorization_url()` function to build GitHub OAuth URL
- [ ] Configure OAuth to request only `read:user` scope (minimal permissions)
- [ ] Implement `exchange_code_for_token()` function to exchange code for access token
- [ ] Reuse existing GitHub API client logic where possible
- [ ] **Validation**: Unit tests with mocked GitHub responses

**Dependencies**: Task 1.1, Task 2.3

### Task 3.2: Create authentication dependency

- [ ] Create `gitbrag/services/auth.py` module
- [ ] Implement `get_authenticated_github_client()` dependency
- [ ] Check session for valid OAuth token
- [ ] Decrypt token from session using encryption module
- [ ] Return authenticated `GitHubClient` instance
- [ ] Raise `HTTPException(401)` if unauthenticated
- [ ] Store original URL for post-login redirect
- [ ] **Validation**: Unit tests for auth dependency with various scenarios

**Dependencies**: Task 2.3, Task 3.1

## Phase 4: Template Infrastructure

### Task 4.1: Create base templates

- [ ] Create `gitbrag/templates/base.html` with header, footer, and content block
- [ ] Include navigation (Home, Login/Logout based on auth state)
- [ ] Add meta tags for responsive design
- [ ] Include placeholders for CSS and JS
- [ ] **Validation**: Render base template and verify structure

**Dependencies**: None

### Task 4.2: Create CSS stylesheets

- [ ] Create `gitbrag/static/css/styles.css` with base styles
- [ ] Define color scheme and typography
- [ ] Create responsive layout rules (mobile-first)
- [ ] Style for summary cards, repository sections, and PR tables
- [ ] Add print-friendly styles
- [ ] **Validation**: Visual review in browser at different viewport sizes

**Dependencies**: Task 4.1

### Task 4.3: Create component templates

- [ ] Create `gitbrag/templates/components/summary_card.html`
- [ ] Create `gitbrag/templates/components/repo_section.html`
- [ ] Create `gitbrag/templates/components/pr_table.html`
- [ ] Each component accepts data and renders appropriately
- [ ] **Validation**: Unit tests rendering each component with sample data

**Dependencies**: Task 4.1

## Phase 5: OAuth Routes

### Task 5.1: Implement login route

- [ ] Add `GET /auth/login` route to `gitbrag/www.py`
- [ ] Generate OAuth state parameter
- [ ] Store state in session
- [ ] Build authorization URL with state and scopes
- [ ] Redirect user to GitHub authorization page
- [ ] **Validation**: Manual test that clicking "Login" redirects to GitHub

**Dependencies**: Task 3.1, Task 2.2

### Task 5.2: Implement OAuth callback route

- [ ] Add `GET /auth/callback` route to `gitbrag/www.py`
- [ ] Validate state parameter against session
- [ ] Handle error parameter from GitHub (denial, etc.)
- [ ] Exchange authorization code for access token
- [ ] Encrypt token before storing in session
- [ ] Store encrypted token in session
- [ ] Redirect to originally requested URL or home
- [ ] **Validation**: Integration test with mocked GitHub OAuth flow

**Dependencies**: Task 5.1, Task 3.1, Task 2.2, Task 2.2

### Task 5.3: Implement logout route

- [ ] Add `GET /auth/logout` route to `gitbrag/www.py`
- [ ] Clear session data from Redis (including encrypted token)
- [ ] Clear session cookie
- [ ] Redirect to home page
- [ ] **Validation**: Manual test that logout clears session and requires re-auth

**Dependencies**: Task 2.3

## Phase 6: Report Generation Routes

### Task 6.1: Create report data service

- [ ] Create `gitbrag/services/reports.py` module
- [ ] Implement `generate_report_data()` function
- [ ] Reuse existing `PullRequestCollector` service
- [ ] Calculate summary statistics (total PRs, state breakdown, repo count)
- [ ] Group PRs by repository
- [ ] Include star increase data if requested
- [ ] Return structured data (not HTML)
- [ ] **Validation**: Unit tests with sample PR data

**Dependencies**: None (uses existing services)

### Task 6.2: Implement unified report caching with period-based keys

- [ ] Add single report cache with no expiration (permanent storage)
- [ ] Implement period normalization function: convert query params to period name
  - `period=1_year` or default (no period param): `1_year`
  - `period=2_years`: `2_years`
  - `period=all_time`: `all_time`
  - Custom date ranges: `custom_{hash_of_since_until}`
- [ ] Store report data with key: `report:{username}:{period}:{params_hash}`
- [ ] Store metadata separately with key: `report:meta:{username}:{period}:{params_hash}`
- [ ] Metadata includes: `created_at` timestamp, `created_by` (username or "system"), `since`, `until` (actual computed dates)
- [ ] Store as JSON in Redis
- [ ] Implement cache age check: calculate age from `created_at` timestamp
- [ ] Implement stale detection: cache is stale if age ≥ 24 hours
- [ ] Implement refresh logic: authenticated users auto-refresh stale caches
- [ ] On refresh: recalculate `since`/`until` from period (e.g., 1_year = today - 365 days to today)
- [ ] Implement manual refresh: `?refresh=true` forces regeneration regardless of age
- [ ] **Validation**: Test that same cache key used on Tuesday and Friday for `1_year` period

**Dependencies**: Task 6.1

### Task 6.3: Create user report template

- [ ] Create `gitbrag/templates/user_report.html`
- [ ] Extend `base.html`
- [ ] Use `summary_card.html` component
- [ ] Use `repo_section.html` component for each repository
- [ ] Display date range prominently
- [ ] Show username and link to GitHub profile
- [ ] Display cache age: "Last updated: X hours/days ago"
- [ ] Show "Refresh" button (visible to all users, redirects unauth to login)
- [ ] Style refresh button prominently when cache is stale (>24 hours)
- [ ] **Validation**: Render template with sample data and verify layout

**Dependencies**: Task 4.3

### Task 6.4: Implement user report route

- [ ] Add `GET /user/github/{username}` route to `gitbrag/www.py`
- [ ] Make authentication optional (not required via dependency)
- [ ] Parse query parameters: `period`, `show_star_increase`, `refresh`
- [ ] Support period values: `1_year` (default), `2_years`, `all_time`
- [ ] Normalize period parameter to standardized name (e.g., `period=1_year` or no param → `1_year`)
- [ ] Generate cache key using period: `report:{username}:{period}:{params_hash}`
- [ ] Validate username format and period values
- [ ] Check for cached report and metadata using period-based key
- [ ] If no cache exists and user is unauthenticated: Show "Login to generate" prompt
- [ ] If cache exists: Check age from metadata
- [ ] If cache is fresh (<24 hours) or user is unauthenticated: Serve from cache
- [ ] If cache is stale (≥24 hours) and user is authenticated: Regenerate and update cache
- [ ] On regeneration: Compute actual `since`/`until` dates from period (e.g., 1_year = today - 365 days to today)
- [ ] If `?refresh=true` and user is unauthenticated: Redirect to login with return URL
- [ ] If `?refresh=true` and user is authenticated: Force regeneration regardless of cache age
- [ ] On regeneration: Update both report data and metadata (created_at, created_by, since, until)
- [ ] Pass cache metadata to template (for "Last updated" display)
- [ ] Render `user_report.html` with report data and cache info
- [ ] Handle errors with appropriate error pages
- [ ] **Validation**: Test that report generated Tuesday is served from same cache on Friday for same period

**Dependencies**: Task 6.2, Task 6.3, Task 3.2

## Phase 7: Home Page and Navigation

### Task 7.1: Create home page template

- [ ] Create `gitbrag/templates/home.html`
- [ ] Show welcome message and project description
- [ ] Show "Login with GitHub" button if unauthenticated
- [ ] Show "View My Report" link if authenticated
- [ ] Include form to view any user's report by username
- [ ] **Validation**: Render and verify content for both auth states

**Dependencies**: Task 4.1

### Task 7.2: Implement home page route

- [ ] Modify `GET /` route in `gitbrag/www.py` (currently redirects to /docs)
- [ ] Check auth state from session
- [ ] Render `home.html` with appropriate context
- [ ] **Validation**: Manual test navigating to home as authenticated and unauthenticated user

**Dependencies**: Task 7.1

### Task 7.3: Update navigation in base template

- [ ] Add conditional navigation based on auth state
- [ ] Show "Home" and "Logout" for authenticated users
- [ ] Show "Home" and "Login" for unauthenticated users
- [ ] Make GitBrag title/logo clickable to home
- [ ] **Validation**: Verify navigation changes appropriately after login/logout

**Dependencies**: Task 4.1, Task 5.3

## Phase 8: Error Handling

### Task 8.1: Create error page templates

- [ ] Create `gitbrag/templates/error.html` (generic error template)
- [ ] Create specific templates: `404.html`, `401.html`, `429.html`, `500.html`
- [ ] Each includes error message, explanation, and actionable next steps
- [ ] Extend `base.html` for consistency
- [ ] **Validation**: Render each error template and verify messaging

**Dependencies**: Task 4.1

### Task 8.2: Implement error handlers

- [ ] Add exception handlers to `gitbrag/www.py` using `@app.exception_handler()`
- [ ] Handle `HTTPException` with appropriate error pages
- [ ] Handle `404` (user not found) with specific messaging
- [ ] Handle `429` (rate limit) with reset time display
- [ ] Handle generic exceptions with 500 page
- [ ] Log errors appropriately (using logger, not print)
- [ ] **Validation**: Integration tests triggering various errors

**Dependencies**: Task 8.1

## Phase 9: Testing

### Task 9.1: Write unit tests for new services

- [ ] Test web OAuth flow functions
- [ ] Test session management functions
- [ ] Test report data generation
- [ ] Test authentication dependency
- [ ] Achieve >80% coverage for new code
- [ ] **Validation**: `pytest tests/ -v --cov=gitbrag`

**Dependencies**: All implementation tasks in phases 1-6

### Task 9.2: Write integration tests for routes

- [ ] Test OAuth flow end-to-end with mock GitHub
- [ ] Test user report route with various parameters
- [ ] Test error scenarios (invalid username, rate limit, etc.)
- [ ] Test session expiration and renewal
- [ ] Use FastAPI `TestClient` for all route tests
- [ ] **Validation**: All integration tests pass

**Dependencies**: All implementation tasks in phases 1-8

### Task 9.3: Manual testing in browser

- [ ] Test OAuth flow with real GitHub (development mode)
- [ ] Test report generation for various users and date ranges
- [ ] Test responsive design on mobile and desktop
- [ ] Test error pages
- [ ] Test logout and re-authentication
- [ ] Test across browsers (Chrome, Firefox, Safari)
- [ ] **Validation**: Checklist of manual test scenarios completed

**Dependencies**: All implementation tasks

## Phase 10: Documentation

### Task 10.1: Create web interface user guide

- [ ] Create `docs/dev/web.md` documenting web interface
- [ ] Explain OAuth setup and configuration
- [ ] Document available routes and query parameters
- [ ] Provide examples of URLs for common use cases
- [ ] Add troubleshooting section
- [ ] **Validation**: Review documentation for completeness

**Dependencies**: All implementation tasks

### Task 10.2: Update README

- [ ] Add "Web Interface" section to `README.md`
- [ ] Include quick start instructions
- [ ] Link to web interface documentation
- [ ] Add screenshot or example report URL
- [ ] **Validation**: Review README changes

**Dependencies**: Task 10.1

### Task 10.3: Update development documentation

- [ ] Add web interface entry to `docs/dev/README.md` table of contents
- [ ] Update `docs/dev/docker.md` if needed (web service already in compose.yaml)
- [ ] Update `docs/dev/settings.md` with new web settings
- [ ] **Validation**: Review all documentation updates

**Dependencies**: Task 10.1

## Phase 11: Docker and Deployment

### Task 11.1: Verify Docker Compose configuration

- [ ] Confirm `compose.yaml` includes Redis service (already present)
- [ ] Confirm web service has Redis environment variables (already present)
- [ ] Test `docker compose up` starts all services correctly
- [ ] Test web interface accessible at `http://localhost`
- [ ] **Validation**: Docker environment fully functional

**Dependencies**: All implementation tasks

### Task 11.2: Update production deployment guidance

- [ ] Document required environment variables for production
- [ ] Document HTTPS and secure cookie requirements
- [ ] Document Redis configuration for production
- [ ] Document session secret key generation
- [ ] Add deployment checklist
- [ ] **Validation**: Deployment documentation reviewed

**Dependencies**: Task 11.1

## Success Criteria

All tasks must be completed and validated. The implementation is successful when:

1. ✅ Users can authenticate with GitHub OAuth from the web interface
2. ✅ Users can view contribution reports at `/user/github/{username}`
3. ✅ Reports default to past year and support custom date ranges via query parameters
4. ✅ Reports display high-level summary and repository breakdown
5. ✅ All API calls are properly cached in Redis
6. ✅ Development environment works with `docker compose up`
7. ✅ All tests pass with >80% coverage
8. ✅ Documentation is complete and accurate
9. ✅ Manual testing checklist is completed

## Notes

- Tasks within each phase can be parallelized where dependencies allow
- Run tests after each task to catch issues early
- Keep CLI functionality untouched - no breaking changes to existing commands
- Use existing services (`PullRequestCollector`, `GitHubClient`, caching) wherever possible
- Follow project conventions (async-first, typed, secure)
