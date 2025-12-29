# configurable-concurrency Specification Delta

## Purpose

Make concurrency limits configurable with sensible defaults to balance speed and reliability, allowing different limits for different deployment scenarios and operation types.

## ADDED Requirements

### Requirement: Configure PR file fetch concurrency

The system MUST allow configuration of concurrent PR file fetch operations to tune the balance between speed and reliability.

#### Scenario: Use environment variable for concurrency limit

**Given** the system is configured with environment variables
**When** `GITHUB_PR_FILE_FETCH_CONCURRENCY` is set to a value between 1 and 20
**Then** the system uses that value for the semaphore limit
**And** the system logs the configured limit at INFO level during startup or first use
**And** if the value is outside the valid range, the system logs WARNING and uses default

#### Scenario: Default to conservative concurrency

**Given** no concurrency configuration is provided
**When** the system initializes PR file fetching
**Then** the system uses a default semaphore limit of 5
**And** this default is lower than the previous limit of 10 for better reliability
**And** the system logs that the default limit is being used at DEBUG level

#### Scenario: Allow different limits for background vs interactive

**Given** a report generation request
**When** the request is from a background job
**Then** the system may use a higher concurrency limit (e.g., 8)
**And** when the request is from interactive CLI or web
**Then** the system uses a lower limit for better reliability (e.g., 5)
**And** the configuration allows separate settings for each mode

### Requirement: Configure repository description fetch concurrency

The system MUST allow separate configuration for repository description fetching to avoid conflating different operation limits.

#### Scenario: Use environment variable for repo description concurrency

**Given** the system is configured with environment variables
**When** `GITHUB_REPO_DESC_FETCH_CONCURRENCY` is set to a value between 1 and 20
**Then** the system uses that value for repository description fetching semaphore
**And** this limit is independent of PR file fetch concurrency
**And** the system logs the configured limit at INFO level

#### Scenario: Default repository description concurrency

**Given** no repository description concurrency configuration is provided
**When** the system fetches repository descriptions
**Then** the system uses a default semaphore limit of 10
**And** this can be higher than PR file fetching as it's a simpler operation
**And** the system logs the default at DEBUG level

### Requirement: Document concurrency configuration

The system MUST document concurrency configuration options for users and operators.

#### Scenario: Include in example environment file

**Given** a new installation or development setup
**When** a user reviews `.env.example`
**Then** the file includes `GITHUB_PR_FILE_FETCH_CONCURRENCY` with recommended values
**And** includes comments explaining the tradeoffs
**And** includes `GITHUB_REPO_DESC_FETCH_CONCURRENCY` with its recommended values
**And** explains that lower values are more reliable but slower

#### Scenario: Include in deployment documentation

**Given** a user is deploying the system
**When** they review deployment documentation
**Then** the documentation explains the concurrency settings
**And** provides guidance on tuning based on API rate limits
**And** explains symptoms of concurrency being too high (missing data, errors)
**And** explains symptoms of concurrency being too low (slow reports)

### Requirement: Validate concurrency configuration

The system MUST validate concurrency configuration values to prevent misconfiguration.

#### Scenario: Reject invalid concurrency values

**Given** a concurrency configuration value
**When** the value is less than 1 or greater than 20
**Then** the system logs ERROR with the invalid value
**And** the system uses the default value instead
**And** the system continues operation without failing

#### Scenario: Warn on extreme values

**Given** a concurrency configuration value
**When** the value is 1 (very conservative)
**Then** the system logs INFO that this will be slower but very reliable
**And** when the value is greater than 15
**Then** the system logs WARNING that high concurrency may cause rate limiting or errors

## MODIFIED Requirements

### Requirement: Extract essential pull request metadata (from github-pull-request-collection)

The system MUST fetch PR file data using configurable concurrency limits to balance speed and reliability based on deployment scenarios and API rate limiting considerations.

#### Scenario: Use configured limit for file fetching

**Given** PR collection has retrieved a list of PRs
**When** the system begins fetching file data concurrently
**Then** the system creates a semaphore with the configured limit
**And** the semaphore limit is not hardcoded to 10
**And** the limit is retrieved from configuration or defaults
**And** the limit used is logged at DEBUG level

## Implementation Notes

- Add settings to `gitbrag/conf/settings.py` using Pydantic Settings
- Use `Field()` with validation for min/max values (1-20)
- Provide descriptive help text for each setting
- Consider adding a `--concurrency` CLI flag for interactive use
- Default to lower concurrency (5) rather than higher (10) for reliability
- Document in both code comments and external documentation
- Consider future enhancement: auto-tune based on rate limit feedback
