# Design: Web Interface Architecture

## Overview

This document outlines the technical architecture for adding a web interface to GitBrag, including OAuth session management, request handling, caching strategy, and integration with existing services.

## Key Architectural Decisions

### 1. OAuth Flow Adaptation

**Decision**: Adapt existing OAuth infrastructure for web-based authentication

**Current State**:

- `GitHubOAuthFlow` in `gitbrag/services/github/oauth.py` implements OAuth for CLI
- Opens browser and runs local callback server on port 8080
- Single-use flow: completes once and returns token

**Required Changes**:

- Web application needs persistent OAuth callback endpoint (not temporary server)
- Sessions must persist across multiple requests
- Tokens must be stored per-user session (not globally)

**Implementation Approach**:

- Create new `WebOAuthFlow` class that uses FastAPI routes instead of local server
- Store user tokens in session cookies (server-side session data)
- Keep CLI `GitHubOAuthFlow` unchanged for backward compatibility

**Trade-offs**:

- **Chosen**: Separate web OAuth implementation
  - Pros: No breaking changes to CLI, cleaner separation of concerns
  - Cons: Some code duplication
- **Rejected**: Modify existing OAuth for both CLI and web
  - Pros: Single implementation
  - Cons: Risk of breaking CLI, more complex conditional logic

### 2. Session Management

**Decision**: Use server-side session storage with secure cookies

**Requirements**:

- Store user OAuth tokens securely
- Associate tokens with user sessions
- Automatic session expiration
- CSRF protection

**Implementation**:

- Use `starlette.middleware.sessions.SessionMiddleware` (included with FastAPI)
- Store session data in Redis (already configured)
- Session cookie configuration:
  - `httponly=True` (prevent XSS)
  - `secure=True` in production (HTTPS only)
  - `samesite='lax'` (CSRF protection)
  - Max age: 24 hours

**Session Data Structure**:

```python
{
    "access_token": "encrypted_blob",  # Encrypted GitHub OAuth token (using cryptography library)
    "token_type": "bearer",
    "scope": "read:user",  # Minimal read-only scope for public data
    "authenticated": True,
    "expires_at": 1234567890,  # Unix timestamp
}
```

**Token Encryption**:

- All OAuth tokens stored in Redis are encrypted using the `cryptography` library (Fernet symmetric encryption)
- Encryption key derived from `session_secret_key` setting
- Tokens are encrypted before storage and decrypted when retrieved
- This protects tokens even if Redis database is compromised

### 3. Route Structure

**Decision**: RESTful route hierarchy with authentication middleware

**Routes**:

```text
/                           → Home page (landing/info)
/auth/login                 → Initiate GitHub OAuth flow
/auth/callback              → OAuth callback endpoint
/auth/logout                → Clear session and log out
/user/github/{username}     → User contribution report (public cache if available, auth optional)
/static/*                   → Static assets (CSS, JS, images)
/docs                       → API documentation (existing FastAPI docs)
```

**OAuth Scopes**:

- Request only `read:user` scope (minimal read-only access to public data)
- Never request `public_repo` or `repo` scopes (more permissive than needed)
- This minimizes risk if tokens are exposed despite encryption

**Authentication Strategy**:

- Use FastAPI dependency injection for auth checks
- Create `get_current_user()` dependency that:
  - Checks session for valid token
  - Validates token hasn't expired
  - Returns GitHub client authenticated with user's token
  - Raises 401 if unauthenticated → redirects to `/auth/login`

**Example**:

```python
@app.get("/user/github/{username}")
async def user_report(
    username: str,
    github: GitHubClient = Depends(get_authenticated_github_client),
    since: str | None = None,
    until: str | None = None,
) -> HTMLResponse:
    # Use github client with user's OAuth token
    ...
```

### 4. Template Structure

**Decision**: Jinja2 templates with template inheritance

**Template Hierarchy**:

```text
templates/
  base.html              → Base layout (header, footer, nav)
  home.html              → Landing page
  user_report.html       → Contribution report display
  auth/
    login.html           → Login page
    error.html           → OAuth error page
  components/
    summary_card.html    → High-level stats component
    repo_section.html    → Per-repository breakdown
    pr_table.html        → PR list table
```

**Template Features**:

- Responsive design (mobile-first)
- Minimal external dependencies (prefer vanilla CSS/JS)
- Use Rich-like styling (maintain CLI aesthetic)
- Include share/print-friendly styles

### 5. Caching Strategy

**Decision**: Single unified cache with age-based automatic refresh and manual refresh option

**Cache Layers**:

1. **GitHub API Response Cache** (already implemented):
   - Cache raw GitHub responses
   - TTL: 1 hour for authenticated requests
   - Key pattern: `github:api:{endpoint}:{params_hash}`

2. **Star Count Cache** (already implemented):
   - Cache star increase calculations
   - TTL: 24 hours
   - Key pattern: `stargazers:{owner}:{repo}:{since}:{until}`

3. **Report Cache** (new - unified public cache):
   - Single cache for all report data (public and shareable)
   - TTL: **No expiration** (permanent cache)
   - Key pattern: `report:{username}:{period}:{params_hash}`
   - Period values: `1_year`, `2_years`, `all_time`, `custom_{hash}` (for non-standard ranges)
   - Default period: `1_year` (current year from today)
   - Metadata stored separately: `report:meta:{username}:{period}:{params_hash}`
   - Metadata includes: `created_at` timestamp, `created_by` (authenticated user or "system"), `since`, `until` (actual dates computed at generation time)
   - Store as JSON (not HTML - allows template changes without cache bust)
   - Allows sharing report URLs without requiring viewers to authenticate
   - Same cache key used regardless of generation day (e.g., Tuesday vs Friday)

**Caching Behavior**:

- **Unauthenticated Access**:
  - Serve from cache if available (instant load)
  - If cache miss, show "Login to generate report" prompt
  - If cache is stale (>24 hours old), show "Refresh" button with login prompt
  - Cache is populated by authenticated users generating reports

- **Authenticated Access**:
  - Check cache age from metadata
  - If cache is fresh (<24 hours old): Serve from cache
  - If cache is stale (≥24 hours old): Automatically regenerate and update cache
  - Manual refresh: `?refresh=true` query parameter forces regeneration regardless of age
  - All regeneration updates the shared cache for everyone

- **Cache Refresh Strategy**:
  - Authenticated users viewing stale reports trigger automatic refresh
  - Any user (auth or unauth) can click "Refresh" button to trigger regeneration
  - "Refresh" button redirects to login if unauthenticated, then regenerates
  - Cache metadata updated with new `created_at` timestamp on refresh
  - Authenticated users effectively maintain fresh public data for everyone

**Example Scenarios**:

1. User A generates their 1-year report on Tuesday while logged in
   - URL: `/user/github/octocat?period=1_year` (or default)
   - Report cached with key `report:octocat:1_year:{hash}` and metadata timestamp
   - User A shares URL with colleagues
   - Colleagues load instantly from cache (no auth required)

2. User B visits same URL on Friday (3 days later, same cache)
   - Same cache key `report:octocat:1_year:{hash}` used (period-based, not date-based)
   - Cache is still fresh (<24 hours), served instantly
   - No regeneration needed - same data for everyone accessing the 1-year report

3. User C views User A's report while logged in (2 weeks later, cache is stale)
   - Cache key `report:octocat:1_year:{hash}` exists but timestamp is old
   - User C's login + stale cache triggers automatic fresh generation
   - Cache updated with latest data and new timestamp
   - Date range automatically recalculated: `since` = today - 1 year, `until` = today
   - Colleagues clicking User A's shared link now see updated data with new date range

4. Unauthenticated visitor clicks report link with stale cache (>24 hours)
   - Sees cached report (still useful, just older)
   - Sees "Last updated: 3 days ago" with "Refresh" button
   - Clicking "Refresh" prompts login, then regenerates and updates cache

5. Any user adds `?refresh=true` to URL
   - If authenticated: Immediately regenerates regardless of cache age
   - If unauthenticated: Redirects to login, then regenerates
   - Useful for "I just merged a PR, show me updated stats" use case

### 6. Error Handling

**Decision**: User-friendly error pages with actionable guidance

**Error Categories**:

1. **Authentication Errors** (401/403):
   - Missing/invalid session → Redirect to `/auth/login`
   - Insufficient OAuth scopes → Show permission explanation page
   - OAuth denial → Show "Why we need access" page

2. **User Not Found** (404):
   - GitHub username doesn't exist
   - Show friendly message with suggestions

3. **Rate Limit** (429):
   - Show rate limit status and reset time
   - Explain benefits of OAuth (higher limits)
   - Link to GitHub rate limit docs

4. **Server Errors** (500):
   - Generic error page
   - Log detailed error server-side
   - Don't expose internal details to users

**Error Page Template**:

```html
<div class="error-container">
  <h1>{{ error_title }}</h1>
  <p>{{ error_message }}</p>
  <div class="actions">
    {{ error_actions }}  <!-- Buttons/links for next steps -->
  </div>
</div>
```

### 7. Date Range Handling

**Decision**: Query parameters for custom date ranges

**Parameters**:

- `since`: ISO 8601 date string (default: 365 days ago)
- `until`: ISO 8601 date string (default: today)

**Examples**:

```text
/user/github/octocat
  → Past year

/user/github/octocat?since=2024-01-01&until=2024-12-31
  → Specific year

/user/github/octocat?since=2024-01-01
  → From date to today
```

**Validation**:

- Reuse CLI date parsing logic
- Show error page for invalid formats
- Limit max range to prevent abuse (e.g., 5 years max)

### 8. Report Structure

**Decision**: Two-section layout matching user requirements

**Report Sections**:

1. **High-Level Summary** (top of page):
   - Total PR count
   - Breakdown by state (open, merged, closed)
   - Total repositories contributed to
   - Date range displayed
   - Star increases (if enabled)

2. **Repository Breakdown** (below summary):
   - Grouped by repository
   - Sorted by PR count (descending)
   - Each repository shows:
     - Repository name and link
     - PR count for this repo
     - Star increase (if enabled)
     - List of PRs with details
   - Expandable/collapsible sections for readability

**Visual Hierarchy**:

```text
┌─────────────────────────────────────────┐
│ [Header: GitBrag]                       │
├─────────────────────────────────────────┤
│ User: octocat                           │
│ Period: Jan 1, 2024 - Dec 31, 2024     │
│                                         │
│ ╔═══════════════════════════════════╗  │
│ ║ SUMMARY                           ║  │
│ ║ • 42 PRs (35 merged, 5 open, 2    ║  │
│ ║   closed)                         ║  │
│ ║ • 12 repositories                 ║  │
│ ╚═══════════════════════════════════╝  │
│                                         │
│ ┌───────────────────────────────────┐  │
│ │ Repository: owner/repo1           │  │
│ │ PRs: 15 | Stars: +234             │  │
│ │                                   │  │
│ │ ▼ Pull Requests                   │  │
│ │   • #123 Feature X (merged)       │  │
│ │   • #124 Bug fix Y (merged)       │  │
│ │   ...                             │  │
│ └───────────────────────────────────┘  │
│                                         │
│ ┌───────────────────────────────────┐  │
│ │ Repository: owner/repo2           │  │
│ │ ...                               │  │
└─────────────────────────────────────────┘
```

## Security Considerations

1. **Token Encryption**:
   - All OAuth tokens encrypted using `cryptography.fernet.Fernet` (symmetric encryption)
   - Encryption key derived from `session_secret_key` using PBKDF2
   - Tokens encrypted before storing in Redis, decrypted when retrieved
   - Protects tokens even if Redis database is compromised
   - Never use custom encryption - rely on vetted cryptography library

2. **Token Storage**:
   - OAuth tokens stored in Redis (server-side session storage)
   - Never expose tokens in HTML or JavaScript
   - Use `SecretStr` for in-memory token handling
   - Session cookies contain only session ID (not tokens)

3. **Minimal OAuth Scopes**:
   - Request only `read:user` scope (read-only access to public data)
   - Never request `public_repo`, `repo`, or write scopes
   - Minimizes damage if token is exposed despite encryption
   - Sufficient for reading public pull requests and user information

4. **CSRF Protection**:
   - Session middleware provides CSRF tokens
   - OAuth state parameter prevents CSRF on callback
   - State parameter stored in session, validated on callback

5. **Rate Limiting**:
   - Public cache reduces API calls (most views don't hit GitHub)
   - Authenticated users use their own GitHub rate limit
   - Consider rate limiting login attempts to prevent abuse

6. **Input Validation**:
   - Validate all query parameters
   - Sanitize username input (alphanumeric and hyphens only)
   - Validate date formats and ranges
   - Reject unexpected parameters

7. **HTTPS**:
   - Require HTTPS in production
   - Configure secure cookies appropriately
   - Set HSTS headers
   - Ensure encryption key is never transmitted

## Configuration Changes

New settings in `gitbrag/conf/settings.py`:

```python
class WebSettings(BaseSettings):
    """Web interface settings."""

    # Session configuration
    session_secret_key: SecretStr = Field(
        default=None,
        description="Secret key for session cookie signing and token encryption (generate with secrets.token_hex(32))"
    )
    session_max_age: int = Field(
        default=86400,  # 24 hours
        description="Maximum session age in seconds"
    )

    # OAuth configuration (web-specific)
    oauth_callback_url: str = Field(
        default="http://localhost/auth/callback",
        description="OAuth callback URL (must match GitHub App settings)"
    )
    oauth_scopes: str = Field(
        default="read:user",
        description="OAuth scopes to request (read:user for minimal read-only public access)"
    )

    # Caching configuration
    public_report_cache_ttl: int = Field(
        default=31536000,  # 1 year (effectively permanent)
        description="TTL for public report cache in seconds"
    )
    authenticated_report_cache_ttl: int = Field(
        default=3600,  # 1 hour
        description="TTL for authenticated report cache in seconds"
    )

    # Security
    require_https: bool = Field(
        default=False,  # True in production
        description="Require HTTPS for secure cookies"
    )
```

## Testing Strategy

1. **Unit Tests**:
   - OAuth flow logic
   - Session management
   - Route handlers
   - Template rendering

2. **Integration Tests**:
   - Full OAuth flow with mock GitHub
   - Report generation end-to-end
   - Cache behavior

3. **Manual Testing**:
   - Browser testing (Chrome, Firefox, Safari)
   - Mobile responsiveness
   - OAuth flow with real GitHub

## Migration Path

This is a new feature with no migration requirements. Existing CLI functionality remains unchanged.

## Future Enhancements

Explicitly out of scope for this change but noted for future consideration:

1. Export functionality (PDF, JSON, Markdown)
2. Report customization UI
3. Compare date ranges
4. Team/organization reports
5. Webhook integration for auto-updating reports
6. Public report links (read-only, no auth required)
7. API endpoints for programmatic access
