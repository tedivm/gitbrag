# github-pull-request-collection Specification

## Purpose
TBD - created by archiving change add-github-contribution-collection. Update Purpose after archive.
## Requirements
### Requirement: Collect user pull requests by date range

The system MUST retrieve all pull requests created by a specific GitHub user within a specified date range across all organizations and repositories, providing comprehensive contribution data for reporting.

#### Scenario: Retrieve all PRs for user in date range

**Given** a valid authenticated GitHub client
**And** a GitHub username "octocat"
**And** a start date of "2024-01-01"
**And** an end date of "2024-12-31"
**When** the system collects pull requests
**Then** the system queries GitHub for all PRs authored by "octocat"
**And** the results include only PRs created between the start and end dates
**And** the results include PRs from all repositories across all organizations
**And** the results are returned as a list of PullRequestInfo objects

#### Scenario: Retrieve PRs with default date range

**Given** a valid authenticated GitHub client
**And** a GitHub username "octocat"
**And** no explicit date range specified
**When** the system collects pull requests
**Then** the system defaults to one year ago as the start date
**And** the system defaults to today as the end date
**And** the system retrieves all PRs in that default range

#### Scenario: Handle user with no pull requests

**Given** a valid authenticated GitHub client
**And** a GitHub username with no pull requests in the date range
**When** the system collects pull requests
**Then** the system returns an empty list
**And** no error is raised
**And** the system completes successfully

#### Scenario: Handle non-existent user

**Given** a valid authenticated GitHub client
**And** a GitHub username that does not exist
**When** the system attempts to collect pull requests
**Then** the system raises a user not found error
**And** the error message clearly states the username was not found
**And** the error message suggests verifying the username

### Requirement: Extract essential pull request metadata

The system MUST extract and structure key information from each pull request, providing all data needed for contribution reporting without exposing raw GitHub API objects.

#### Scenario: Extract PR metadata fields

**Given** a pull request from the GitHub API
**When** the system transforms it to a PullRequestInfo object
**Then** the object includes the PR title
**And** the object includes the repository name in "owner/repo" format
**And** the object includes the full PR URL
**And** the object includes the PR state (open, closed, merged)
**And** the object includes the creation date as a datetime
**And** the object includes the merged date as a datetime or None
**And** the object includes the PR number

#### Scenario: Handle merged pull request

**Given** a pull request that was merged
**When** the system extracts metadata
**Then** the state is set to "merged"
**And** the merged_at field contains the merge datetime
**And** all other fields are populated correctly

#### Scenario: Handle open pull request

**Given** a pull request that is still open
**When** the system extracts metadata
**Then** the state is set to "open"
**And** the merged_at field is None
**And** all other fields are populated correctly

#### Scenario: Handle closed but not merged pull request

**Given** a pull request that was closed without merging
**When** the system extracts metadata
**Then** the state is set to "closed"
**And** the merged_at field is None
**And** all other fields are populated correctly

### Requirement: Handle pagination automatically

The system MUST handle GitHub API pagination transparently, ensuring all matching pull requests are retrieved regardless of result set size.

#### Scenario: Retrieve PRs across multiple pages

**Given** a user with more than 100 pull requests in the date range
**And** GitHub API returns results in pages of 30 items
**When** the system collects pull requests
**Then** the system automatically fetches all pages
**And** the system aggregates results from all pages
**And** the final result includes all matching PRs
**And** no duplicates are present in the results

#### Scenario: Handle single page of results

**Given** a user with fewer than 30 pull requests in the date range
**When** the system collects pull requests
**Then** the system retrieves the single page of results
**And** pagination does not cause unnecessary API calls
**And** all PRs are returned correctly

### Requirement: Filter results by date accurately

The system MUST filter pull requests based on creation date with correct timezone handling and inclusive date bounds.

#### Scenario: Filter by creation date inclusively

**Given** a start date of "2024-01-01T00:00:00Z"
**And** an end date of "2024-12-31T23:59:59Z"
**And** PRs created at various times
**When** the system filters results
**Then** PRs created at exactly the start date are included
**And** PRs created at exactly the end date are included
**And** PRs created before the start date are excluded
**And** PRs created after the end date are excluded

#### Scenario: Handle timezone-aware dates

**Given** dates specified in different timezones
**When** the system performs date filtering
**Then** all dates are normalized to UTC for comparison
**And** filtering logic accounts for timezone differences
**And** results are consistent regardless of local timezone

#### Scenario: Parse ISO 8601 date formats

**Given** dates provided in ISO 8601 format (e.g., "2024-01-01")
**When** the system parses the dates
**Then** dates without time default to start of day (00:00:00)
**And** dates with time use the specified time
**And** dates without timezone default to UTC
**And** invalid date formats raise a clear parsing error

### Requirement: Filter by repository visibility

The system MUST filter pull requests by repository visibility, defaulting to public repositories only with an option to include private repositories.

#### Scenario: Retrieve only public repository PRs by default

**Given** a valid authenticated GitHub client
**And** a GitHub username with PRs in both public and private repositories
**And** no explicit visibility filter specified
**When** the system collects pull requests
**Then** the system returns only PRs from public repositories
**And** PRs from private repositories are excluded
**And** the filtering happens during the query to minimize API calls

#### Scenario: Include private repository PRs when requested

**Given** a valid authenticated GitHub client with repo scope
**And** a GitHub username with PRs in both public and private repositories
**And** the include_private flag is set to true
**When** the system collects pull requests
**Then** the system returns PRs from both public and private repositories
**And** all matching PRs are included regardless of visibility

#### Scenario: Handle insufficient permissions for private repositories

**Given** an authenticated GitHub client without repo scope
**And** the include_private flag is set to true
**When** the system attempts to collect pull requests
**Then** the system raises a permissions error
**And** the error message explains that repo scope is required for private repositories
**And** the error message suggests updating the token permissions

### Requirement: Handle API errors gracefully

The system MUST handle various GitHub API error conditions with clear, actionable error messages.

#### Scenario: Handle network connectivity errors

**Given** a network connectivity issue
**When** the system attempts to query the GitHub API
**Then** the system raises a network error
**And** the error message suggests checking internet connectivity
**And** the error message suggests retrying the request

#### Scenario: Handle API service errors

**Given** the GitHub API returns a 5xx server error
**When** the system processes the response
**Then** the system raises an API service error
**And** the error message explains GitHub is experiencing issues
**And** the error message suggests trying again later

#### Scenario: Handle authentication errors during collection

**Given** an invalid or expired authentication token
**When** the system attempts to collect pull requests
**Then** the system raises an authentication error
**And** the error message explains the authentication failed
**And** the error message suggests checking credentials

### Requirement: Provide type-safe domain models

The system MUST use strongly-typed domain models for pull request data, enabling reliable serialization and future extensibility.

#### Scenario: PullRequestInfo is a typed dataclass

**Given** the PullRequestInfo model
**When** examining its definition
**Then** all fields have explicit type annotations
**And** required fields are not Optional
**And** merged_at is Optional (can be None)
**And** the model uses @dataclass decorator

#### Scenario: PullRequestInfo supports serialization

**Given** a PullRequestInfo instance
**When** converting to a dictionary
**Then** the instance can be serialized to dict
**And** dates are serialized in ISO format
**And** None values are preserved
**And** the structure is suitable for JSON export

#### Scenario: PullRequestInfo validates types

**Given** an attempt to create PullRequestInfo with wrong types
**When** instantiating the class
**Then** Python's type system catches type mismatches
**And** mypy reports type errors during static analysis
**And** runtime type checking (if enabled) catches errors

