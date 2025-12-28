# web-user-interface Specification Delta

## ADDED Requirements

### Requirement: Web-based user report pages

The system MUST provide web pages that display GitHub contribution reports for any username, accessible via browser at a standard URL pattern.

#### Scenario: Access user report via URL

**Given** a user has authenticated with GitHub OAuth
**And** the user visits `/user/github/octocat`
**When** the report page loads
**Then** the system displays a contribution report for user "octocat"
**And** the report shows pull requests from the default date range (past year)
**And** the report is rendered as HTML

#### Scenario: Access user report with custom date range

**Given** a user has authenticated with GitHub OAuth
**And** the user visits `/user/github/octocat?since=2024-01-01&until=2024-12-31`
**When** the report page loads
**Then** the system displays a contribution report for user "octocat"
**And** the report shows only pull requests from 2024-01-01 to 2024-12-31
**And** the date range is clearly displayed on the page

#### Scenario: Redirect unauthenticated user to login for uncached report

**Given** a user is not authenticated
**And** the user visits `/user/github/octocat`
**And** no public cache exists for this report
**When** the page processes the request
**Then** the system displays a prompt: "Login with GitHub to generate this report"
**And** the prompt includes a "Login" button redirecting to `/auth/login`
**And** the system preserves the original URL for post-login redirect
**And** after authentication completes, the system generates the report and caches it publicly

#### Scenario: Handle invalid username format

**Given** a user has authenticated with GitHub OAuth
**And** the user visits `/user/github/invalid@username`
**When** the page processes the request
**Then** the system displays a 400 error page
**And** the error explains that the username format is invalid
**And** the error provides guidance on valid username formats

#### Scenario: Serve cached report without authentication

**Given** a user is not authenticated
**And** the user visits `/user/github/octocat`
**And** a public cache exists for this user's report (past year)
**When** the page processes the request
**Then** the system serves the report from public cache immediately
**And** no GitHub API calls are made
**And** no authentication is required
**And** the report displays normally with all data

### Requirement: OAuth authentication for web users

The system MUST implement GitHub OAuth flow for web users, allowing them to authenticate and authorize the application to access their GitHub data and rate limits.

#### Scenario: Initiate OAuth flow from login page

**Given** an unauthenticated user visits `/auth/login`
**When** the user clicks "Login with GitHub"
**Then** the system generates a secure state parameter
**And** the system redirects to GitHub's authorization page
**And** the authorization request includes scopes: read:user (minimal read-only access)
**And** the state parameter is stored in the session for CSRF protection

#### Scenario: Complete OAuth flow and establish session

**Given** a user has authorized the application on GitHub
**When** GitHub redirects back to `/auth/callback?code=abc123&state=xyz789`
**And** the state parameter matches the session state
**Then** the system exchanges the authorization code for an access token
**And** the system stores the access token in the session cookie
**And** the session cookie is set with httponly, secure (in prod), and samesite=lax
**And** the system redirects to the originally requested URL or home page

#### Scenario: Reject OAuth callback with mismatched state

**Given** a user is in the OAuth flow
**When** GitHub redirects back to `/auth/callback?code=abc123&state=wrong_state`
**And** the state parameter does not match the session state
**Then** the system rejects the callback
**And** the system displays a security error page
**And** the system does not store any access token
**And** the system logs a potential CSRF attempt

#### Scenario: Handle OAuth authorization denial

**Given** a user is redirected to GitHub for authorization
**When** the user clicks "Cancel" or denies authorization
**And** GitHub redirects back to `/auth/callback?error=access_denied`
**Then** the system displays an error page explaining authorization was denied
**And** the error page includes a button to retry authorization
**And** no access token is stored

#### Scenario: Logout and clear session

**Given** a user is authenticated
**When** the user visits `/auth/logout`
**Then** the system clears the session cookie
**And** the system removes all session data from Redis
**And** the system redirects to the home page
**And** subsequent requests are unauthenticated

### Requirement: Session-based authentication management

The system MUST manage user sessions with secure cookies and server-side storage, maintaining authentication state across multiple requests.

#### Scenario: Store OAuth token in session

**Given** a user completes OAuth flow and receives an access token
**When** the system stores the token
**Then** the token is stored in a server-side session (Redis)
**And** a session cookie is set in the user's browser
**And** the session cookie contains only a session ID (not the token)
**And** the actual token is never sent to the browser

#### Scenario: Validate session on authenticated request

**Given** a user has an active session with a stored OAuth token
**And** the session cookie is present in the request
**When** the user accesses a protected route like `/user/github/octocat`
**Then** the system retrieves the session from Redis using the session ID
**And** the system validates the session has not expired
**And** the system creates a GitHubClient authenticated with the session token
**And** the request proceeds with the authenticated client

#### Scenario: Reject expired session

**Given** a user has a session that expired 25 hours ago (TTL: 24 hours)
**And** the session cookie is still present in the browser
**When** the user attempts to access a protected route
**Then** the system detects the session has expired
**And** the system clears the expired session from Redis
**And** the system redirects to `/auth/login`
**And** the system preserves the original URL for post-login redirect

#### Scenario: Handle missing or invalid session cookie

**Given** a user's browser does not have a valid session cookie
**When** the user attempts to access a protected route
**Then** the system detects no valid session exists
**And** the system redirects to `/auth/login`
**And** no error is displayed (missing session is expected for new users)

### Requirement: Two-section report layout

The system MUST display contribution reports in a structured format with a high-level summary section at the top and a detailed repository-by-repository breakdown below.

#### Scenario: Display high-level summary section

**Given** a user has authenticated and requests a report for "octocat"
**And** the report contains 42 PRs across 12 repositories
**And** 35 PRs are merged, 5 are open, and 2 are closed
**When** the report page renders
**Then** the top section displays a summary card with:

- Total PR count: 42
- State breakdown: "35 merged, 5 open, 2 closed"
- Repository count: 12
- Date range: "January 1, 2024 - December 31, 2024"
**And** the summary section uses prominent styling (e.g., card or panel)
**And** the summary section appears above the repository breakdown

#### Scenario: Display repository breakdown section

**Given** a user has authenticated and requests a report for "octocat"
**And** the report contains PRs from repositories: owner/repo1 (15 PRs), owner/repo2 (10 PRs), owner/repo3 (8 PRs)
**When** the report page renders
**Then** below the summary section, repositories are displayed in order by PR count descending
**And** each repository section shows:

- Repository name as a heading with link to GitHub
- PR count for this repository
- List of PRs with number, title, state, and dates
**And** PRs within each repository are sorted by creation date descending
**And** each repository section is visually separated (e.g., with borders or spacing)

#### Scenario: Display star increase in report sections

**Given** a user has authenticated and requests a report with `?show_star_increase=true`
**And** owner/repo1 gained 234 stars during the period
**And** owner/repo2 gained 50 stars during the period
**When** the report page renders
**Then** the summary section includes total star increase across all repositories
**And** each repository section displays its star increase (e.g., "+234" for repo1)
**And** star increases are displayed prominently with green styling or icon

#### Scenario: Handle repository with no star increase data

**Given** a user has authenticated and requests a report with `?show_star_increase=true`
**And** one repository's star data is unavailable (deleted, private, or rate limited)
**When** the report page renders
**Then** that repository's section displays "-" or "N/A" for star increase
**And** the tooltip or note explains why data is unavailable
**And** other repositories with valid star data display normally

### Requirement: HTML template rendering with Jinja2

The system MUST use Jinja2 templates to render HTML pages with consistent styling, layout, and responsive design.

#### Scenario: Render page with base template inheritance

**Given** the system has a base template defining header, footer, and navigation
**And** the user report template extends the base template
**When** a user report page is rendered
**Then** the page includes the header from base template
**And** the page includes the footer from base template
**And** the page includes navigation links (Home, Logout, etc.)
**And** the report content is inserted in the content block

#### Scenario: Render responsive layout

**Given** a user report page is rendered
**When** the page is viewed on a mobile device (viewport width < 768px)
**Then** the layout adapts to a single-column format
**And** tables display in a mobile-friendly format (scrollable or stacked)
**And** text remains readable without horizontal scrolling
**And** navigation collapses to a mobile menu (hamburger or similar)

#### Scenario: Render page with custom CSS styling

**Given** the system includes custom CSS stylesheets
**When** any page is rendered
**Then** the styling matches GitBrag's visual identity
**And** colors and fonts are consistent across pages
**And** the design is clean and professional for sharing/printing
**And** accessibility guidelines are followed (contrast, font sizes, etc.)

#### Scenario: Render error pages with consistent layout

**Given** an error occurs (404, 401, 500, etc.)
**When** the error page is rendered
**Then** the page uses the base template for consistency
**And** the error message is displayed clearly
**And** actionable next steps are provided (e.g., "Login" button, "Go Home" link)
**And** the error page is styled consistently with the rest of the site

### Requirement: Query parameter support for report customization

The system MUST accept and process query parameters to customize report generation without requiring a complex UI.

#### Scenario: Parse date range from query parameters

**Given** a user visits `/user/github/octocat?since=2024-01-01&until=2024-06-30`
**When** the system processes the request
**Then** the system parses "2024-01-01" as the start date
**And** the system parses "2024-06-30" as the end date
**And** the system generates a report for only that date range
**And** the report page displays the custom date range

#### Scenario: Default date range when parameters omitted

**Given** a user visits `/user/github/octocat` (no query parameters)
**When** the system processes the request
**Then** the system uses a start date of 365 days ago
**And** the system uses today as the end date
**And** the report page displays the custom date range

#### Scenario: Validate query parameter formats

**Given** a user visits `/user/github/octocat?since=invalid_date`
**When** the system processes the request
**Then** the system detects the invalid date format
**And** the system displays a 400 error page
**And** the error explains the expected date format (ISO 8601: YYYY-MM-DD)
**And** the error provides an example of correct usage

### Requirement: Report caching for performance

The system MUST cache generated reports in Redis using standardized period names (not exact dates) to ensure cache reuse across different days and users, avoiding repeated GitHub API calls and providing instant loading for shared report URLs.

#### Scenario: Period-based cache key generation

**Given** a user requests `/user/github/octocat?period=1_year`
**When** the system generates a cache key
**Then** the cache key is `report:octocat:1_year:{params_hash}`
**And** the same cache key is used regardless of the current date
**And** a report generated on Tuesday uses the same cache as one accessed on Friday
**And** the metadata key is `report:meta:octocat:1_year:{params_hash}`

#### Scenario: Support standard period values

**Given** a user requests a report
**When** the system normalizes the period parameter
**Then** the system supports `period=1_year` (default: today - 365 days to today)
**And** the system supports `period=2_years` (today - 730 days to today)
**And** the system supports `period=all_time` (beginning of user's GitHub history to today)
**And** custom date ranges use `period=custom_{hash}` where hash is derived from `since` and `until`
**And** the actual date range is recalculated on each regeneration (stored in metadata)

#### Scenario: Cross-day cache reuse

**Given** an authenticated user generates a report on Tuesday at `/user/github/octocat?period=1_year`
**And** the report is cached with key `report:octocat:1_year:{hash}`
**And** the cache metadata includes `since=2023-12-24` and `until=2024-12-24` (Tuesday's dates)
**When** an unauthenticated user accesses the same URL on Friday (3 days later)
**Then** the system uses the same cache key `report:octocat:1_year:{hash}`
**And** the system serves the cached report instantly
**And** the report displays the original date range from metadata
**And** the report shows "Last updated: 3 days ago"
**And** no GitHub API calls are made
**And** the same cached data is shared between all users accessing this period

#### Scenario: First report generation by authenticated user

**Given** an authenticated user requests `/user/github/octocat?period=1_year`
**And** no cached report exists for this user and period
**When** the report is generated
**Then** the system computes date range: `since` = today - 365 days, `until` = today
**And** the system fetches data from GitHub API using computed dates
**And** the system generates the report data
**And** the system stores report data in Redis with key `report:octocat:1_year:{params_hash}`
**And** the system stores metadata with key `report:meta:octocat:1_year:{params_hash}`
**And** metadata includes `created_at` timestamp, `created_by` (authenticated username), `since`, `until` (computed dates)
**And** the cache has no TTL (permanent storage)
**And** the report is rendered and served

#### Scenario: Serve cached report to unauthenticated user

**Given** a cached report exists for username "octocat" and period "1_year"
**And** an unauthenticated user requests `/user/github/octocat?period=1_year`
**When** the request is processed
**Then** the system retrieves the report data from cache using period-based key
**And** the report is rendered and served instantly (no GitHub API calls)
**And** the user sees the report without needing to log in
**And** the report displays the date range from metadata (original computed dates)
**And** the report displays "Last updated: X hours/days ago" based on cache metadata

#### Scenario: Serve fresh cached report to authenticated user

**Given** a cached report exists for username "octocat" and period "1_year"
**And** the cache metadata shows `created_at` was 6 hours ago (<24 hours)
**And** an authenticated user requests `/user/github/octocat?period=1_year`
**When** the request is processed
**Then** the system retrieves the cache metadata
**And** the system calculates cache age as 6 hours
**And** the system determines cache is fresh (age < 24 hours)
**And** the system serves the cached report without regeneration
**And** no GitHub API calls are made

#### Scenario: Auto-refresh stale cache for authenticated user with date recalculation

**Given** a cached report exists for username "octocat" and period "1_year"
**And** the cache metadata shows `created_at` was 36 hours ago
**And** the cached metadata has `since=2023-12-24` and `until=2024-12-24`
**And** an authenticated user requests `/user/github/octocat?period=1_year`
**And** today's date is December 27, 2024
**When** the request is processed
**Then** the system retrieves the cache metadata
**And** the system calculates cache age as 36 hours
**And** the system determines cache is stale (age ≥ 24 hours)
**And** the system recalculates date range: `since=2023-12-27`, `until=2024-12-27` (current 1 year)
**And** the system regenerates the report with fresh GitHub API data using new dates
**And** the system updates the cache with new report data
**And** the system updates metadata with new `created_at`, `created_by`, `since`, `until`
**And** the fresh report is rendered and served
**And** subsequent users (auth or unauth) see the updated data with new date range

#### Scenario: Show stale cache to unauthenticated user with refresh option

**Given** a cached report exists for username "octocat" and period "1_year"
**And** the cache metadata shows `created_at` was 48 hours ago (>24 hours)
**And** an unauthenticated user requests `/user/github/octocat?period=1_year`
**When** the request is processed
**Then** the system retrieves the cached report (stale but available)
**And** the system serves the cached report to the user
**And** the report displays the original date range from metadata
**And** the report displays "Last updated: 2 days ago"
**And** the report shows a "Refresh" button
**And** the "Refresh" button has prominent styling indicating data is stale
**And** clicking "Refresh" redirects to `/auth/login` with return URL

#### Scenario: Manual refresh by authenticated user

**Given** an authenticated user requests `/user/github/octocat?period=1_year&refresh=true`
**And** a cached report exists (regardless of age)
**When** the request is processed
**Then** the system detects `refresh=true` parameter
**And** the system bypasses cache age check
**And** the system recalculates current date range from period (1_year = today - 365 to today)
**And** the system regenerates the report with fresh GitHub API data
**And** the system updates the cache with new report data and metadata
**And** the fresh report is rendered and served
**And** this works even if cache is only 1 hour old (user-initiated refresh)

#### Scenario: Manual refresh by unauthenticated user

**Given** an unauthenticated user requests `/user/github/octocat?period=1_year&refresh=true`
**When** the request is processed
**Then** the system detects `refresh=true` parameter
**And** the system detects user is not authenticated
**And** the system redirects to `/auth/login`
**And** the system preserves the original URL with `refresh=true` for post-login redirect
**And** after successful authentication, the system regenerates the report with current dates

#### Scenario: Prompt unauthenticated user for missing cache

**Given** no cached report exists for username "octocat" with period "1_year"
**And** an unauthenticated user requests `/user/github/octocat?period=1_year`
**When** the request is processed
**Then** the system detects cache miss
**And** the system detects user is not authenticated
**And** the system renders a prompt: "Login to generate this report"
**And** the prompt includes a "Login with GitHub" button
**And** the login redirects back to the original report URL after authentication

#### Scenario: Store cache metadata with computed dates

**Given** a report is generated for username "octocat" with period "1_year"
**And** the authenticated user is "alice"
**And** today's date is December 27, 2024
**When** the report data is cached
**Then** the system stores metadata separately from report data
**And** metadata includes:

- `created_at`: ISO 8601 timestamp of generation
- `created_by`: "alice" (or "system" for automated processes)
- `since`: "2023-12-27" (computed date 365 days ago)
- `until`: "2024-12-27" (computed date today)
**And** metadata key is `report:meta:octocat:1_year:{params_hash}`
**And** metadata is used for age calculation, date display, and showing last refresh date
**And** metadata is updated on every regeneration with newly computed dates

### Requirement: Error handling with user-friendly pages

The system MUST display clear, actionable error pages for all failure scenarios, helping users understand what went wrong and how to proceed.

#### Scenario: Display 404 error for non-existent user

**Given** a user requests a report for a non-existent GitHub username
**When** the GitHub API returns a 404 (user not found)
**Then** the system displays a 404 error page
**And** the error message states "User '{username}' not found on GitHub"
**And** the error page suggests checking the username spelling
**And** the error page includes a link to search GitHub for the username

#### Scenario: Display 401 error for unauthenticated request

**Given** a user attempts to access `/user/github/octocat` without authentication
**When** the system detects no valid session
**Then** the system redirects to `/auth/login` (not an error page)
**And** the login page explains authentication is required
**And** the login page includes a "Login with GitHub" button

#### Scenario: Display 429 error for rate limit exceeded

**Given** a user's GitHub OAuth token has exceeded its rate limit
**When** the system attempts to fetch PR data
**Then** the system displays a 429 error page
**And** the error message explains the rate limit has been exceeded
**And** the error displays the rate limit reset time
**And** the error suggests waiting until the reset time
**And** the error page includes a link to GitHub rate limit documentation

#### Scenario: Display 500 error for unexpected failures

**Given** an unexpected server error occurs during report generation
**When** the system catches the error
**Then** the system displays a 500 error page
**And** the error message is generic and user-friendly ("Something went wrong")
**And** the error page suggests trying again later
**And** the error page includes a link to return home
**And** detailed error information is logged server-side (not shown to user)

#### Scenario: Display OAuth error page

**Given** an error occurs during OAuth flow (e.g., GitHub returns an error)
**When** the system processes the OAuth callback with an error parameter
**Then** the system displays an OAuth error page
**And** the error message explains what went wrong based on the error type
**And** the error page includes a "Try Again" button to restart OAuth flow
**And** the error page includes a link to GitHub documentation if relevant

### Requirement: Static asset serving

The system MUST serve static assets (CSS, JavaScript, images) efficiently with proper caching headers.

#### Scenario: Serve CSS stylesheets

**Given** the system has CSS files in the `gitbrag/static/css/` directory
**When** a page references `/static/css/styles.css`
**Then** the system serves the CSS file with content-type "text/css"
**And** the response includes cache-control headers (e.g., max-age=3600)
**And** the CSS file is delivered without errors

#### Scenario: Serve JavaScript files

**Given** the system has JavaScript files in the `gitbrag/static/js/` directory
**When** a page references `/static/js/app.js`
**Then** the system serves the JavaScript file with content-type "application/javascript"
**And** the response includes appropriate cache-control headers
**And** the JavaScript file is delivered without errors

#### Scenario: Serve images and other assets

**Given** the system has image files in the `gitbrag/static/images/` directory
**When** a page references `/static/images/logo.png`
**Then** the system serves the image with the correct content-type
**And** the response includes cache-control headers
**And** the image is displayed correctly in the browser

#### Scenario: Return 404 for missing static assets

**Given** a page references `/static/css/nonexistent.css`
**When** the system attempts to serve the file
**Then** the system returns a 404 response
**And** the browser console logs a missing resource error
**And** the page continues to render (gracefully handles missing asset)

### Requirement: Home page and navigation

The system MUST provide a home page that introduces GitBrag and provides navigation to key features.

#### Scenario: Display home page for unauthenticated users

**Given** an unauthenticated user visits `/`
**When** the home page loads
**Then** the page displays the GitBrag title and tagline
**And** the page explains what GitBrag does
**And** the page includes a "Login with GitHub" button
**And** the page includes a link to documentation or README
**And** the page is styled consistently with the rest of the site

#### Scenario: Display home page for authenticated users

**Given** an authenticated user visits `/`
**When** the home page loads
**Then** the page displays the GitBrag title and tagline
**And** the page includes a welcome message with the user's GitHub username
**And** the page includes a link to view their own report (e.g., "View My Contributions")
**And** the page includes a logout button or link
**And** the page includes instructions for viewing other users' reports

#### Scenario: Navigate to user report from home

**Given** an authenticated user is on the home page
**And** the page includes a form or link to view any user's report
**When** the user enters "octocat" and submits
**Then** the system redirects to `/user/github/octocat`
**And** the report page loads for user "octocat"

#### Scenario: Navigate between pages with consistent header

**Given** any page is rendered
**When** the page includes the site header
**Then** the header displays the GitBrag logo/name with a link to home
**And** the header includes navigation links appropriate for auth state:

- Unauthenticated: "Login"
- Authenticated: "Home", "Logout"
**And** the header styling is consistent across all pages
