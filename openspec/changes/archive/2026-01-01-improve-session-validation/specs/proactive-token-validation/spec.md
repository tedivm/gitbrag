# proactive-token-validation Specification

## ADDED Requirements

### Requirement: Token validation before expensive operations

The system MUST validate GitHub OAuth tokens with the GitHub API before initiating expensive operations to detect expired or invalid tokens early and prevent resource waste.

**Rationale**: Proactive validation prevents background jobs and API-heavy operations from running with invalid credentials, saving system resources and providing faster feedback to users.

#### Scenario: Validate token before starting background job

**Given** a user has a session with a GitHub OAuth token
**And** a background job for report generation is about to be scheduled
**When** the system checks if the job can be scheduled
**Then** the system validates the token with GitHub's `/user` endpoint
**And** the job is only scheduled if the token is valid
**And** if the token is invalid, the job is not scheduled and a warning is logged

#### Scenario: Validate token before authenticated web request

**Given** a user has a session with a GitHub OAuth token
**And** the user makes a request to an authenticated route (e.g., `/reports/{username}`)
**When** the authentication dependency `get_authenticated_github_client()` is called
**Then** the system validates the token with GitHub's `/user` endpoint
**And** if the token is valid, the request proceeds normally
**And** if the token is invalid, the session is cleared and the user receives a 401 error

#### Scenario: Token validation uses lightweight API call

**Given** the system needs to validate a GitHub token
**When** the validation is performed
**Then** the system makes a GET request to `https://api.github.com/user`
**And** the request includes the token in the Authorization header
**And** the response is checked for status code 200 (valid) or 401/403 (invalid)
**And** the validation completes in under 5 seconds
**And** no data from the response is persisted (validation only)

#### Scenario: Token validation distinguishes auth errors from other errors

**Given** the system validates a token with GitHub
**When** the GitHub API responds
**Then** status code 200 indicates the token is valid
**And** status codes 401 or 403 indicate the token is invalid or expired
**And** status code 429 or network errors do not invalidate the token (may retry)
**And** other 4xx/5xx errors are treated as API errors, not token validation failures

#### Scenario: Token validation result is not cached

**Given** a token has been validated successfully
**And** time passes after the validation
**When** the system needs to validate the same token again
**Then** the system makes a fresh API call to GitHub
**And** no cached validation result is used
**And** the token validity is checked in real-time

**Rationale**: Not caching validation results ensures we always have authoritative information from GitHub, preventing serving requests with tokens that became invalid between validations.

### Requirement: Add validate_token method to GitHubAPIClient

The `GitHubAPIClient` class MUST provide a `validate_token()` method to check token validity with the GitHub API.

**Rationale**: Centralizing token validation in the GitHub client ensures consistent validation logic and makes it easy to use across the codebase.

#### Scenario: Call validate_token on authenticated client

**Given** a `GitHubAPIClient` instance with a valid token
**When** the `validate_token()` method is called
**Then** the method makes a GET request to `/user` endpoint
**And** the method returns `True` if the status code is 200
**And** the method returns `False` if the status code is 401 or 403
**And** the method raises an exception for network errors or rate limits

#### Scenario: validate_token uses existing retry logic

**Given** a `GitHubAPIClient` instance
**When** `validate_token()` makes an API call that times out
**Then** the method uses the existing `_request_with_retry()` logic
**And** the method retries up to the configured maximum retries
**And** exponential backoff is applied between retries

#### Scenario: validate_token is async

**Given** a `GitHubAPIClient` instance
**When** `validate_token()` is called
**Then** the method is an async method
**And** the method must be awaited
**And** the method can be used in async context with other async operations

#### Scenario: validate_token is safe to call multiple times

**Given** a `GitHubAPIClient` instance
**When** `validate_token()` is called multiple times
**Then** each call makes a fresh API request
**And** the method has no side effects on the client state
**And** multiple calls can be made safely without affecting client behavior
