# web-user-interface Specification Delta

## MODIFIED Requirements

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

## ADDED Requirements

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
