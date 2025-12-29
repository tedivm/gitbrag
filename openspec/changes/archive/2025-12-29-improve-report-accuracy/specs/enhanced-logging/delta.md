# enhanced-logging Specification Delta

## Purpose

Add comprehensive logging throughout the PR collection and file fetching pipeline to enable debugging of data accuracy issues, particularly for longer time periods where silent failures may occur.

## ADDED Requirements

### Requirement: Log PR collection statistics

The system MUST log aggregate statistics about PR collection operations to provide visibility into the overall health and completeness of data collection.

#### Scenario: Log PR collection start and completion

**Given** a report generation request for a user
**When** PR collection begins
**Then** the system logs the username, date range, and collection parameters at INFO level
**And** when collection completes, the system logs the total PRs collected at INFO level
**And** the log includes the time taken for collection

#### Scenario: Log file fetching summary

**Given** PR collection has retrieved a list of pull requests
**When** file fetching begins for PR metrics
**Then** the system logs the total number of PRs requiring file data at DEBUG level
**And** after all file fetching completes, the system logs success and failure counts at INFO level
**And** the log includes the overall success rate percentage
**And** if any failures occurred, the system logs a WARNING with the failure count

### Requirement: Log individual PR file fetch operations

The system MUST log details of individual PR file fetch attempts to enable diagnosis of specific failures without requiring debug-level logs for all operations.

#### Scenario: Log successful PR file fetch

**Given** a PR file fetch request
**When** the fetch succeeds
**Then** the system logs the repository, PR number, and metrics at DEBUG level
**And** the log includes additions, deletions, and changed file counts

#### Scenario: Log failed PR file fetch with reason

**Given** a PR file fetch request
**When** the fetch fails
**Then** the system logs the repository and PR number at WARNING level
**And** the log includes the error type and message
**And** the log includes whether the error was retried or skipped
**And** if the error is a rate limit, the log includes the wait time

#### Scenario: Log cached vs fetched data

**Given** a PR file fetch request
**When** the data is found in cache
**Then** the system logs a cache hit at DEBUG level with the PR identifier
**And** when data is fetched fresh, the system logs it was cached for future use at DEBUG level

### Requirement: Log rate limiting encounters

The system MUST log when GitHub API rate limits are encountered to correlate rate limiting with data accuracy issues.

#### Scenario: Log rate limit detection

**Given** a GitHub API request
**When** a rate limit response is received (403 or 429)
**Then** the system logs a WARNING with the current rate limit status
**And** the log includes remaining requests and reset time
**And** the log includes whether the system will wait or fail

#### Scenario: Log rate limit recovery

**Given** the system is waiting for rate limit reset
**When** the wait completes
**Then** the system logs an INFO message that rate limiting has passed
**And** the system logs the new rate limit status

### Requirement: Track and report partial failures

The system MUST distinguish between complete failures (no data collected) and partial failures (some PRs missing data) to help users understand data completeness.

#### Scenario: Report partial PR data collection

**Given** file fetching completed for a set of PRs
**When** some PRs have missing code metrics
**Then** the system logs a WARNING listing the count and percentage of PRs with incomplete data
**And** if the percentage exceeds 10%, the system logs an ERROR level message
**And** the log suggests possible remediation steps (retry, check rate limits)

#### Scenario: Track zero-data PRs separately

**Given** file fetching for multiple PRs
**When** a PR returns zero additions, deletions, and changed files
**Then** the system logs at DEBUG level that the PR may have non-code changes
**And** the PR is not counted as a "failure" in success rate calculations
**And** the log distinguishes between fetch errors and legitimately empty PRs

## MODIFIED Requirements

### Requirement: Handle API errors gracefully (from github-pull-request-collection)

The system MUST log detailed error information before returning empty data when PR file fetching fails, enabling diagnosis of data accuracy issues.

#### Scenario: Log errors before returning empty data

**Given** a PR file fetch request that encounters an error
**When** the system catches the exception
**Then** the system logs the full error with traceback at WARNING or ERROR level
**And** the log includes contextual information (repo, PR number, error type)
**And** only then does the system return empty data tuple
**And** the log indicates that empty data was returned due to an error

## Implementation Notes

- Use structured logging where possible to enable log parsing and analysis
- Include correlation IDs or request identifiers to trace operations across logs
- Ensure sensitive data (tokens, API keys) is never logged
- Use appropriate log levels: DEBUG for verbose operation details, INFO for summary statistics, WARNING for recoverable errors, ERROR for critical failures
- Consider adding metrics/telemetry hooks in addition to logging for production monitoring
