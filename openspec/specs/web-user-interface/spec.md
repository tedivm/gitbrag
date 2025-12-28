# web-user-interface Specification

## Purpose
TBD - created by archiving change add-web-interface. Update Purpose after archive.
## Requirements
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

The system MUST cache generated reports in Redis using standardized period names (not exact dates) to ensure cache reuse across different days and users, avoiding repeated GitHub API calls and providing instant loading for shared report URLs. Report generation MUST happen asynchronously in the background, allowing users to see cached content immediately while fresh reports are being generated.

#### Scenario: Serve cached report with background regeneration for authenticated user

**Given** a cached report exists for username "octocat" and period "1_year"
**And** the cache metadata shows `created_at` was 36 hours ago (stale)
**And** an authenticated user requests `/user/github/octocat?period=1_year`
**When** the request is processed
**Then** the system retrieves the cached report immediately
**And** the system schedules a background task to regenerate the report with fresh data
**And** the system serves the cached report to the user without delay
**And** the report displays "This report is being updated" notice with a loading indicator
**And** the background task regenerates the report with current GitHub API data
**And** the background task updates the cache with new report data and metadata
**And** when the user refreshes the page, they see the updated report without the "updating" notice

#### Scenario: Prevent duplicate background tasks for same report

**Given** a cached report exists for username "octocat" and period "1_year"
**And** the cache is stale (>24 hours old)
**And** user A requests `/user/github/octocat?period=1_year` (authenticated)
**And** the system schedules a background task to regenerate the report
**When** user B requests `/user/github/octocat?period=1_year` 2 seconds later (authenticated)
**Then** the system detects a background task is already active for this report
**And** the system serves the cached report to user B
**And** the system displays "This report is being updated" notice
**And** the system does NOT schedule a second background task
**And** both users see the updated report after the single background task completes

#### Scenario: Background task updates cache on successful completion

**Given** a background task is regenerating a report for username "octocat" and period "1_year"
**When** the background task successfully generates the report data
**Then** the system updates the cache with key `report:octocat:1_year:{params_hash}`
**And** the system updates metadata with key `report:meta:octocat:1_year:{params_hash}`
**And** metadata includes new `created_at` timestamp (current time)
**And** metadata includes new `since` and `until` dates (recalculated from period)
**And** the system removes the task tracking key from Redis
**And** subsequent requests serve the fresh cached data
**And** no "updating" notice is shown

#### Scenario: Background task fails gracefully without affecting users

**Given** a background task is regenerating a report for username "octocat"
**When** the GitHub API returns an error (e.g., rate limit exceeded, network timeout)
**Then** the background task logs the error with details
**And** the background task cleans up the task tracking key in Redis
**And** the background task does NOT update the cache (old cache remains valid)
**And** users continue to see the old cached report
**And** the error is not displayed to users (only logged server-side)
**And** users can manually retry by clicking "Refresh Now" button

#### Scenario: Display loading indicator for report with no cache

**Given** no cached report exists for username "octocat" and period "1_year"
**And** an authenticated user requests `/user/github/octocat?period=1_year`
**When** the request is processed
**Then** the system schedules a background task to generate the report
**And** the system immediately returns a "Generating Report" page
**And** the page displays a loading spinner and message: "Your report is being generated. This may take 10 seconds to several minutes."
**And** the page includes a "Refresh" button or auto-refresh meta tag
**And** when the user refreshes after the background task completes, they see the full report

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

### Requirement: Background task management for report generation

The system MUST use FastAPI BackgroundTasks to regenerate reports asynchronously, preventing request blocking and enabling immediate response with cached data while updates occur in the background.

#### Scenario: Schedule background task for stale report

**Given** a cached report exists but is stale (≥24 hours old)
**And** an authenticated user requests the report
**When** the system processes the request
**Then** the system schedules a FastAPI background task to regenerate the report
**And** the background task is registered with a unique task ID: `{username}:{period}:{params_hash}`
**And** the system immediately returns the stale cached report to the user
**And** the background task executes after the response is sent
**And** the background task updates the cache when complete

#### Scenario: Background task cleans up after completion

**Given** a background task is regenerating a report
**When** the background task completes (successfully or with error)
**Then** the system removes the task tracking key from Redis: `task:report:{username}:{period}:{params_hash}`
**And** the system removes the user's active task from `task:user:{username}:active` set
**And** subsequent requests can schedule new background tasks for this report
**And** Redis memory is not leaked by uncleaned task keys

#### Scenario: Background task respects GitHub API rate limits

**Given** an authenticated user has multiple reports across different repositories
**When** background tasks are generating reports
**Then** all background tasks use the same GitHub OAuth token (user's token)
**And** all API calls count against the user's GitHub rate limit (5000/hour)
**And** the system does not make API calls for unauthenticated requests
**And** rate limit errors are logged and handled gracefully (see failure scenario above)

### Requirement: Task deduplication to prevent redundant API calls

The system MUST use Redis-based task tracking to ensure only one background task runs for each unique report at any given time, preventing duplicate API calls and resource waste.

#### Scenario: Check for active task before scheduling

**Given** a user requests a report that requires regeneration
**When** the system prepares to schedule a background task
**Then** the system checks Redis for key `task:report:{username}:{period}:{params_hash}`
**And** if the key exists and has not expired (TTL > 0), the task is already active
**And** the system does NOT schedule a new background task
**And** the system serves cached data with "This report is being updated" notice
**And** if the key does not exist, the system proceeds to schedule the task

#### Scenario: Atomically register background task

**Given** the system determines a background task should be scheduled
**When** the system registers the task
**Then** the system uses Redis SET NX (set if not exists) to atomically create the task key
**And** the command is `SET task:report:{task_id} {metadata} NX EX 300`
**And** if the SET succeeds, the task is registered and the background task is scheduled
**And** if the SET fails (key already exists), another process registered the task first
**And** the system does NOT schedule a duplicate background task
**And** this prevents race conditions when multiple requests arrive simultaneously

#### Scenario: Task key auto-expires after timeout

**Given** a background task is registered with Redis key `task:report:{task_id}`
**And** the key has TTL of 300 seconds
**When** the background task hangs or fails to complete within 300 seconds
**Then** Redis automatically expires and removes the task key
**And** subsequent requests can schedule new background tasks
**And** this prevents permanently stuck task keys from blocking regeneration

### Requirement: Per-reported-user rate limiting for report generation

The system MUST limit report generation to one active task per reported GitHub username at a time, ensuring sequential generation allows cache reuse and reduces redundant API calls for the same user's data.

#### Scenario: Enforce one active task per reported GitHub user

**Given** a background task is generating a report for GitHub user "tedivm" with period "1_year"
**And** the task is registered in Redis at `task:user:tedivm:active`
**When** someone requests a different report for "tedivm" with period "2_years"
**And** the system attempts to schedule a new background task
**Then** the system checks `task:user:tedivm:active` in Redis
**And** the system detects "tedivm" already has an active report generation task
**And** the system does NOT schedule the new background task
**And** the system logs: "Reported user tedivm already has active task, skipping"
**And** the request returns cached data (if available) or shows "Report is being generated" message

#### Scenario: Allow task after previous task completes

**Given** a background task generating a report for "tedivm" completed 10 seconds ago
**And** the task removed itself from `task:user:tedivm:active`
**When** someone requests a new report for "tedivm" (different period or parameters)
**And** the system attempts to schedule a background task
**Then** the system checks `task:user:tedivm:active` and finds no active tasks
**And** the system allows the new background task to be scheduled
**And** the new task is registered in `task:user:tedivm:active`

#### Scenario: Different reported users can have concurrent tasks

**Given** a background task is generating a report for GitHub user "tedivm"
**When** someone requests a report for GitHub user "torvalds" (different reported user)
**And** the system attempts to schedule a background task
**Then** the system checks `task:user:torvalds:active` (separate from tedivm's tasks)
**And** the system finds no active tasks for "torvalds"
**And** the system schedules the background task for "torvalds"
**And** both "tedivm" and "torvalds" report generation tasks run concurrently
**And** per-reported-user limiting allows different users' reports to generate in parallel

#### Scenario: Sequential generation benefits from shared cache

**Given** a background task is generating a report for "tedivm" with period "1_year"
**And** the task fetches tedivm's profile, repositories, and PRs from GitHub API
**And** some of this data is cached (user profile, repository list)
**When** a second request for "tedivm" with period "2_years" arrives
**Then** the system enforces per-reported-user limiting and waits
**And** when the first task completes, the second task can start
**And** the second task benefits from cached data populated by the first task
**And** the second task makes fewer GitHub API calls
**And** overall performance is improved compared to parallel generation

### Requirement: Visual feedback for report regeneration state

The system MUST display clear visual indicators to users when reports are being regenerated in the background, differentiating between fresh, stale, and actively-updating reports.

#### Scenario: Display "updating" notice for active background task

**Given** a background task is actively regenerating a report
**And** a user views the report page
**When** the page renders
**Then** the page displays a prominent notice: "This report is being updated with the latest data."
**And** the notice includes a loading spinner icon
**And** the notice uses info-level styling (blue background)
**And** the notice includes text: "Refresh this page in a few moments to see the updated report."
**And** the cached report data is displayed below the notice

#### Scenario: Display stale cache prompt for unauthenticated users

**Given** a cached report is stale (≥24 hours old)
**And** an unauthenticated user views the report page
**And** no background task is active (unauthenticated users cannot trigger tasks)
**When** the page renders
**Then** the page displays a notice: "This report was last updated {time} ago."
**And** the notice uses warning-level styling (yellow background)
**And** the notice includes a "Login to Refresh" button
**And** clicking the button redirects to `/auth/login?return_to={current_url}`
**And** the cached report data is displayed below the notice

#### Scenario: Display refresh button for authenticated users with stale cache

**Given** a cached report is stale (≥24 hours old)
**And** an authenticated user views the report page
**And** no background task is currently active
**When** the page renders
**Then** the page displays a notice: "This report was last updated {time} ago."
**And** the notice uses warning-level styling
**And** the notice includes a "Refresh Now" button or link
**And** clicking "Refresh Now" reloads the page with `?force=true` parameter
**And** the force parameter triggers an immediate background task (bypassing stale check)

#### Scenario: Hide notices for fresh cache

**Given** a cached report is fresh (<24 hours old)
**And** no background task is active
**When** a user views the report page
**Then** no "updating" or "stale" notices are displayed
**And** only the report data is shown
**And** the cache age is displayed subtly (e.g., "Last updated 2 hours ago" in footer or metadata section)

