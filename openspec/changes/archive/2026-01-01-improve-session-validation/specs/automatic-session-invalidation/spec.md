# automatic-session-invalidation Specification

## MODIFIED Requirements

### Requirement: Automatic session invalidation on token validation failure

The system MUST automatically clear session data when GitHub token validation fails, ensuring users are not shown as authenticated when their tokens are expired or invalid.

**Changes**: Extends session management to automatically detect and clear invalid sessions based on GitHub API responses.

**Rationale**: Prevents misleading UI states where users appear logged in but cannot perform authenticated actions.

#### Scenario: Clear session when token validation fails

**Given** a user has an active session with an encrypted OAuth token
**And** the user makes a request to an authenticated route
**When** token validation with GitHub returns 401 or 403
**Then** the system clears all session data for that user
**And** the session's `authenticated` flag is set to False
**And** the encrypted token is removed from the session
**And** a warning is logged indicating session invalidation

#### Scenario: Redirect to login after session invalidation

**Given** a user's session has been invalidated due to failed token validation
**When** the system responds to the user's request
**Then** the system raises a 401 HTTPException
**And** the exception detail message says "Your session has expired. Please log in again."
**And** the user's original requested URL is stored for post-login redirect
**And** the existing exception handler redirects the user to `/auth/login`

#### Scenario: Session invalidation is idempotent

**Given** a user's session has already been invalidated
**When** the session invalidation function is called again
**Then** the function completes without error
**And** no duplicate logs are generated
**And** the session remains cleared

#### Scenario: Session invalidation preserves redirect URL

**Given** a user makes a request to `/reports/octocat` with an invalid token
**When** the session is invalidated
**Then** the original URL `/reports/octocat` is stored in session as `redirect_after_login`
**And** after the user re-authenticates, they are redirected to `/reports/octocat`
**And** the user doesn't lose context of what they were trying to do

## ADDED Requirements

### Requirement: Centralized session invalidation helper

The system MUST provide a centralized `invalidate_session()` helper function to ensure consistent session clearing logic across the codebase.

**Rationale**: Centralizing invalidation logic prevents inconsistencies, makes testing easier, and provides a single place to add cleanup logic.

#### Scenario: Use invalidate_session helper for clearing sessions

**Given** any part of the system needs to invalidate a user session
**When** the code calls `invalidate_session(request)`
**Then** all session data is cleared via `clear_session()`
**And** a log entry is created at INFO level
**And** the log message indicates the reason for invalidation (e.g., "invalid token")

#### Scenario: invalidate_session is available from session module

**Given** a module needs to invalidate a session
**When** the code imports from `gitbrag.services.session`
**Then** the `invalidate_session` function is available
**And** the function signature is `invalidate_session(request: Request) -> None`
**And** the function is documented with clear docstring

### Requirement: Update is_authenticated to reflect token validity

The `is_authenticated()` helper MUST accurately reflect whether a user can perform authenticated actions, not just whether a session cookie exists.

**Changes**: The existing `is_authenticated()` function behavior is updated to validate tokens when needed.

**Rationale**: Prevents false positives where session exists but token is invalid.

#### Scenario: is_authenticated returns False after token validation failure

**Given** a user has a session cookie with an encrypted token
**And** the token has been validated and found to be invalid
**When** `is_authenticated(request)` is called on subsequent requests
**Then** the function returns False
**And** the user is treated as unauthenticated
**And** the user is redirected to login for protected routes

**Note**: This scenario is achieved by session invalidation clearing the session data, so `is_authenticated()` naturally returns False when checking for the `authenticated` session key.

#### Scenario: is_authenticated remains fast check for session existence

**Given** a user makes a request
**When** `is_authenticated(request)` is called
**Then** the function checks for the `authenticated` flag in session
**And** no API calls to GitHub are made by this function
**And** the function completes in under 1ms
**And** token validation happens separately in `get_authenticated_github_client()`

**Rationale**: `is_authenticated()` remains a fast session check; actual token validation happens at the boundary of operations requiring GitHub API access.

### Requirement: Log session invalidation events

The system MUST log all session invalidation events with appropriate context for debugging and monitoring.

**Rationale**: Visibility into session invalidations helps diagnose authentication issues and track token expiration patterns.

#### Scenario: Log warning when session invalidated due to invalid token

**Given** a user's token fails validation
**When** the session is invalidated
**Then** a log entry is created at WARNING level
**And** the log includes the reason "Token validation failed"
**And** the log includes a sanitized session identifier (not the token itself)
**And** the log does not contain any secret values

#### Scenario: Log info when session cleared for explicit logout

**Given** a user clicks the logout button
**When** the session is invalidated
**Then** a log entry is created at INFO level
**And** the log indicates "User logged out"
**And** the log distinguishes explicit logout from automatic invalidation

#### Scenario: Never log token values in invalidation logs

**Given** the system is logging session invalidation
**When** any log entry is generated
**Then** no OAuth token values appear in the logs
**And** no decrypted token strings appear in the logs
**And** only session identifiers or usernames are logged for context
