# error-resilience Specification Delta

## Purpose

Enhance error handling and retry logic in concurrent operations to improve data collection reliability and reduce silent failures during PR metrics fetching.

## ADDED Requirements

### Requirement: Retry failed PR file fetches

The system MUST implement retry logic for transient failures during PR file fetching to maximize data completeness.

#### Scenario: Retry on timeout

**Given** a PR file fetch request
**When** the request times out
**Then** the system retries the request up to 3 times
**And** each retry waits with exponential backoff (1s, 2s, 4s) plus jitter
**And** jitter adds ±25% randomness to prevent thundering herd when multiple requests fail
**And** each retry attempt is logged at WARNING level with the actual wait time
**And** after max retries, the system logs ERROR and returns empty data

#### Scenario: Retry on rate limit in fetch_pr_metrics

**Given** a PR file fetch request
**When** the underlying API client indicates rate limiting (via existing retry mechanism)
**Then** the system waits for the rate limit to clear
**And** the operation continues after the wait
**And** the system logs the rate limit encounter and recovery

#### Scenario: No retry on 404 errors

**Given** a PR file fetch request
**When** a 404 (Not Found) error occurs
**Then** the system does NOT retry
**And** the system logs a WARNING that the PR was not found
**And** the system returns empty data immediately
**And** the log indicates this is expected for deleted PRs

### Requirement: Distinguish fatal from transient errors

The system MUST categorize errors to apply appropriate handling strategies and avoid unnecessary retries of permanent failures.

#### Scenario: Handle transient errors with retry

**Given** an error occurs during file fetching
**When** the error is a timeout, connection error, or 429/503 response
**Then** the system categorizes it as transient
**And** applies retry logic with backoff
**And** logs the error as WARNING with retry count

#### Scenario: Handle fatal errors without retry

**Given** an error occurs during file fetching
**When** the error is 401 (unauthorized), 404 (not found), or 422 (unprocessable)
**Then** the system categorizes it as fatal
**And** does NOT retry the operation
**And** logs the error as ERROR or WARNING based on type
**And** returns empty data immediately

#### Scenario: Handle unexpected errors conservatively

**Given** an error occurs during file fetching
**When** the error type is not explicitly categorized
**Then** the system treats it as transient
**And** applies retry logic to be resilient
**And** logs the error with full traceback at ERROR level
**And** includes error type for future categorization

### Requirement: Add error context to failures

The system MUST enrich error information to enable effective debugging and issue resolution.

#### Scenario: Include PR context in errors

**Given** an error occurs during PR file fetching
**When** the error is logged or raised
**Then** the error message includes the repository name
**And** includes the PR number
**And** includes the operation being performed
**And** includes the error count for this operation if retrying

#### Scenario: Include rate limit context in errors

**Given** a rate limit error occurs
**When** the error is logged
**Then** the log includes the current rate limit remaining count
**And** includes the rate limit reset timestamp
**And** includes estimated wait time
**And** includes the endpoint being rate limited

### Requirement: Validate fetched data

The system MUST validate PR file data before returning it to catch and handle malformed responses.

#### Scenario: Validate tuple structure from fetch_pr_files

**Given** data is retrieved from cache or API
**When** the data is checked before returning
**Then** the system validates it is a tuple of length 4
**And** validates the first element is a list
**And** validates the other three elements are integers
**And** if validation fails, logs ERROR and refetches from API (if from cache)

#### Scenario: Validate non-negative metrics

**Given** PR file data is fetched from the API
**When** the metrics are extracted
**Then** the system validates additions >= 0
**And** validates deletions >= 0
**And** validates changed_files >= 0
**And** if any are negative, logs WARNING and treats as 0

## MODIFIED Requirements

### Requirement: Handle API errors gracefully (from github-pull-request-collection)

The system MUST distinguish between fatal and transient errors when handling API failures, applying retry logic for transient errors and failing fast for permanent failures to maximize data completeness while avoiding wasted effort.

#### Scenario: Return empty data only after retries exhausted

**Given** a PR file fetch encounters a transient error
**When** all retry attempts have been exhausted
**Then** the system logs a final ERROR message
**And** the error includes all retry attempt details
**And** only then returns empty data tuple `([], 0, 0, 0)`
**And** the failure is tracked in collection statistics

## Implementation Notes

- Reuse existing retry logic from `GitHubAPIClient._request_with_retry` where possible
- Add retry logic at the `fetch_pr_metrics` level for operation-specific errors
- Consider circuit breaker pattern if high failure rates are detected
- Track failure reasons in memory for end-of-collection summary
- Ensure retry logic respects overall request timeouts for long-running reports
