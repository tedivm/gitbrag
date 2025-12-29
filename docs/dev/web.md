# Web Interface

The GitBrag web interface provides a browser-based way to view GitHub contribution reports. Users can authenticate with GitHub OAuth, generate reports, and share them via URL.

## Features

- **GitHub OAuth Authentication**: Secure login using GitHub OAuth with minimal permissions
- **Public Data Only**: Only displays publicly accessible GitHub data
- **Report Generation**: View pull request contributions by time period
- **Period Filtering**: Filter reports by 1 year, 2 years, or all time
- **Repository Breakdown**: See contributions organized by repository
- **Cached Reports**: Reports are cached for performance, with automatic staleness detection
- **Responsive Design**: Mobile-first design with dark mode support

## Running the Web Interface

### Using Docker Compose (Recommended)

```bash
docker compose up
```

This starts both the web server and Redis cache.

### Manual Setup

1. Install dependencies:

```bash
uv sync
```

1. Start Redis:

```bash
docker run -p 6379:6379 redis:alpine
```

1. Configure environment variables (`.env`):

```env
# GitHub OAuth
GITHUB_APP_CLIENT_ID=your_client_id
GITHUB_APP_CLIENT_SECRET=your_client_secret

# Session Security
SESSION_SECRET_KEY=your-secret-key-at-least-32-chars

# Web Settings
OAUTH_CALLBACK_URL=http://localhost/auth/callback
REQUIRE_HTTPS=false
OAUTH_SCOPES=read:user
```

1. Start the web server:

```bash
uvicorn gitbrag.www:app --host 0.0.0.0 --port 80
```

## Configuration

### Required Settings

- `GITHUB_APP_CLIENT_ID`: GitHub OAuth app client ID
- `GITHUB_APP_CLIENT_SECRET`: GitHub OAuth app client secret
- `SESSION_SECRET_KEY`: Secret key for session encryption (32+ characters)

### Optional Settings

- `OAUTH_CALLBACK_URL`: OAuth callback URL (default: `http://localhost/auth/callback`)
- `REQUIRE_HTTPS`: Enforce HTTPS for secure cookies (default: `false`)
- `OAUTH_SCOPES`: OAuth permission scopes (default: `read:user`)
- `SESSION_MAX_AGE`: Session lifetime in seconds (default: `86400` / 24 hours)
- `REPORT_CACHE_STALE_AGE`: Age when cached reports are considered stale (default: `3600` / 1 hour)

### Creating a GitHub OAuth App

1. Go to GitHub Settings → Developer settings → OAuth Apps
2. Click "New OAuth App"
3. Fill in:
   - Application name: "GitBrag"
   - Homepage URL: Your domain (e.g., `http://localhost`)
   - Authorization callback URL: `http://localhost/auth/callback`
4. Save and copy the Client ID and Client Secret

## Architecture

### Session Management

- Sessions are stored server-side in Redis
- Session cookies are HttpOnly and SameSite=Lax
- OAuth tokens are encrypted using Fernet symmetric encryption
- Sessions expire after 24 hours (configurable)

### Caching Strategy

- Reports are cached in Redis with period-based keys
- Cache keys include username, period, and feature flags (like star increase)
- Cached reports include metadata (creation time, creator)
- Stale reports (older than `REPORT_CACHE_STALE_AGE`, default 24h) trigger background regeneration for authenticated users
- Unauthenticated users see cached reports but cannot trigger regeneration

### Background Report Generation

The web interface uses FastAPI BackgroundTasks for asynchronous report generation, providing instant page loads while reports generate in the background.

**Key Features:**

- **Instant Response**: Serve cached reports immediately when available
- **Background Refresh**: Stale reports trigger background regeneration automatically
- **Task Deduplication**: Prevents multiple simultaneous generation of the same report
- **Per-User Rate Limiting**: Only one report generates at a time per GitHub username
- **Visual Feedback**: Spinner and auto-refresh during generation

**Request Flow:**

1. **Authenticated + Fresh Cache** (<24h): Serve immediately
2. **Authenticated + Stale Cache** (≥24h): Serve with "updating" notice + background refresh
3. **Authenticated + No Cache**: Show "generating" message + background task
4. **Unauthenticated**: Serve cache if available, show "Login to Refresh" if stale

**Task Tracking** (Redis-based):

- Task keys: `task:report:{username}:{period}:{params_hash}`
- User keys: `task:user:{username}:active` (per-user rate limiting)
- TTL: 300s (auto-cleanup for hung tasks)
- Max tasks per user: 1 (configurable via `MAX_REPORTED_USER_CONCURRENT_TASKS`)

See [Cache Documentation](cache.md) for detailed caching patterns.

### Authentication Flow

1. User clicks "Login with GitHub"
2. App redirects to GitHub OAuth with CSRF state token
3. GitHub redirects back to callback with authorization code
4. App exchanges code for access token
5. Token is encrypted and stored in session
6. User is redirected to original page

### Username Normalization

GitHub usernames are case-insensitive, but GitBrag normalizes them to lowercase for consistent caching and URL handling:

- **Cache Keys**: All cache keys use lowercase usernames to prevent duplicate entries
- **URL Redirects**: URLs with uppercase usernames automatically redirect (301 Permanent) to lowercase
- **Query Preservation**: Redirects preserve all query parameters (e.g., `?period=2_years`)
- **SEO Benefit**: Canonical lowercase URLs prevent duplicate content issues

Example: `/user/github/TEDIVM` → 301 Redirect → `/user/github/tedivm`

### Report Generation

1. User visits `/user/github/{username}?period={period}`
2. If username contains uppercase, 301 redirect to lowercase URL
3. System checks for cached report (using lowercase username)
4. If cache is stale and user is authenticated, regenerate
5. If no cache and user is not authenticated, show 404
6. Generate report by collecting PRs from GitHub API
7. Store report in cache with metadata
8. Render report template with data

## Routes

### Public Routes

- `GET /`: Home page with login option
- `GET /auth/login`: Initiate GitHub OAuth flow
- `GET /auth/callback`: Handle OAuth callback
- `GET /auth/logout`: Log out and clear session
- `GET /user/github/{username}`: View user's contribution report (cached or generate)

### Query Parameters

- `/user/github/{username}?period={period}`: Filter by time period (`1_year`, `2_years`, `all_time`)
- `/user/github/{username}?force=true`: Force regenerate report (requires authentication)
- `/auth/login?return_to={url}`: Redirect to URL after login

## Security

### OAuth Scope Minimization

- Only requests `read:user` scope
- No write permissions
- No access to private repositories
- No organization access

### CSRF Protection

- OAuth flow uses state parameter for CSRF protection
- State token stored in session and validated on callback

### Token Security

- OAuth tokens are encrypted at rest
- Encryption uses Fernet symmetric encryption with PBKDF2 key derivation
- 100,000 PBKDF2 iterations for key strengthening
- Session cookies are HttpOnly to prevent XSS

### HTTPS Enforcement

- Enable `REQUIRE_HTTPS=true` in production
- Forces secure cookies and HTTPS-only OAuth callback

## Templates

### Base Template (`base.html`)

- Shared header and navigation
- Conditional login/logout based on authentication status
- Footer with links

### Home Template (`home.html`)

- Landing page with login button
- Feature list
- Authenticated user message

### Report Template (`user_report.html`)

- Report header with username and date range
- Period selector (1 year, 2 years, all time)
- Summary card with statistics
- Repository sections with PR tables
- Cache status indicator

### Error Template (`error.html`)

- Generic error page for 404, 401, 429, 500
- Contextual error messages
- Optional login button

## Styling

- Mobile-first responsive design
- Dark mode support via `prefers-color-scheme`
- CSS custom properties for theming
- Print-friendly styles
- Status badges for PR states (merged, open, closed)

## Error Handling

- `404 Not Found`: Page doesn't exist
- `401 Unauthorized`: Authentication required
- `429 Rate Limited`: Too many requests
- `500 Internal Server Error`: Server error
- `400 Bad Request`: Invalid parameters

## Development

### Testing

Run web interface tests:

```bash
make test tests/test_www.py
```

### Local Development

Start in development mode with auto-reload:

```bash
uvicorn gitbrag.www:app --reload --host 0.0.0.0 --port 80
```

### Debugging

Enable debug logging:

```bash
export LOG_LEVEL=DEBUG
```

View container logs:

```bash
docker compose logs -f www
```

## Performance

### Caching Benefits

- Reduces GitHub API calls
- Faster page loads for cached reports
- Automatic cache invalidation based on age

### Redis Configuration

- Persistent storage recommended for production
- Configure memory limits appropriately
- Monitor cache hit rates

## Limitations

- Public data only (no private repositories)
- Rate limited by GitHub API (5000 requests/hour for authenticated users)
- Stale cache for unauthenticated users (cannot regenerate)
- No database (all data cached in Redis)
- Session-based authentication only (no API tokens)

## Future Enhancements

- User dashboard showing own reports
- Custom date ranges beyond predefined periods
- Export reports to PDF or JSON
- Share reports via unique shareable links
- Repository filtering options
- Enhanced statistics and charts
- Organization-level reports
