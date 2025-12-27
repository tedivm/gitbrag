# contribution-report-cli Specification

## Purpose
TBD - created by archiving change add-github-contribution-collection. Update Purpose after archive.
## Requirements
### Requirement: List command interface

The system MUST provide a CLI command that accepts a GitHub username and displays their pull requests from a specified time period.

#### Scenario: List contributions with username argument

**Given** the user has configured authentication
**When** the user runs `gitbrag list octocat`
**Then** the system queries GitHub for PRs authored by "octocat"
**And** the system displays all PRs from the default date range (1 year)
**And** the output is formatted for terminal readability
**And** the command completes successfully

#### Scenario: List contributions with custom date range

**Given** the user has configured authentication
**When** the user runs `gitbrag list octocat --since 2024-01-01 --until 2024-06-30`
**Then** the system queries GitHub for PRs created between those dates
**And** the system displays only PRs within that range
**And** the output shows the date range used

#### Scenario: List contributions with only start date

**Given** the user has configured authentication
**When** the user runs `gitbrag list octocat --since 2024-01-01`
**Then** the system uses "2024-01-01" as the start date
**And** the system uses today as the end date
**And** the system displays PRs created in that range

#### Scenario: List contributions with only end date

**Given** the user has configured authentication
**When** the user runs `gitbrag list octocat --until 2024-12-31`
**Then** the system uses one year before end date as start date
**And** the system uses "2024-12-31" as the end date
**And** the system displays PRs created in that range

### Requirement: Authentication override via CLI

The system MUST allow users to provide authentication credentials via CLI options, overriding environment variables for convenience and testing.

#### Scenario: Override PAT with --token option

**Given** the user has not set GITHUB_TOKEN environment variable
**Or** the user wants to use a different token
**When** the user runs `gitbrag list octocat --token ghp_xxxxx`
**Then** the system uses the provided token for authentication
**And** the token is not logged or displayed
**And** environment variable settings are ignored for this execution

#### Scenario: Combine token override with date options

**Given** the user provides both token and date options
**When** the user runs `gitbrag list octocat --token ghp_xxxxx --since 2024-01-01`
**Then** the system uses the provided token
**And** the system uses the provided date range
**And** both overrides work correctly together

### Requirement: URL display control

The system MUST provide a CLI option to display PR URLs in the output, defaulting to hiding URLs for cleaner display while always showing PR numbers.

#### Scenario: Show PR numbers by default without URLs

**Given** the user has configured authentication
**When** the user runs `gitbrag list octocat`
**Then** the output displays PR numbers for all PRs (e.g., "#42")
**And** the output does not include URL columns
**And** the display is compact and easy to scan

#### Scenario: Include URLs when flag is provided

**Given** the user has configured authentication
**When** the user runs `gitbrag list octocat --show-urls`
**Then** the output displays PR numbers for all PRs
**And** the output includes full GitHub URLs for each PR
**And** URLs are displayed in a separate column or alongside PR information

#### Scenario: Combine URL flag with other options

**Given** the user provides multiple flags
**When** the user runs `gitbrag list octocat --show-urls --include-private --since 2024-01-01`
**Then** the output includes URLs as requested
**And** all other flags work correctly together
**And** the combined options produce expected filtered results with URLs

### Requirement: Result sorting

The system MUST provide sorting options with support for multiple sort fields, allowing users to organize results by different criteria.

**Changes**: Added "stars" as a valid sort field when --show-stars is enabled.

#### Scenario: Handle invalid sort field

**Given** the user provides an invalid sort field
**When** the user runs `gitbrag list octocat --sort invalid_field`
**Then** the system raises a validation error
**And** the error message lists valid sort fields (repository, state, created, merged, title, stars)
**And** the error message indicates that "stars" requires the --show-star-increase flag
**And** the error message provides an example of correct usage
**And** the command exits with status code 1

Note: "stars" is only valid when --show-star-increase flag is provided

### Requirement: Repository visibility filtering

The system MUST provide a CLI option to include private repositories, defaulting to public repositories only.

#### Scenario: List only public repository contributions by default

**Given** the user has configured authentication
**And** the user has contributions in both public and private repositories
**When** the user runs `gitbrag list octocat`
**Then** the system queries GitHub for public repository PRs only
**And** private repository PRs are excluded from results
**And** the output shows only public repository contributions

#### Scenario: Include private repository contributions with flag

**Given** the user has configured authentication with repo scope
**And** the user has contributions in both public and private repositories
**When** the user runs `gitbrag list octocat --include-private`
**Then** the system queries GitHub for both public and private repository PRs
**And** the output includes contributions from all repositories
**And** private repositories are clearly marked or indicated

#### Scenario: Handle insufficient permissions for private repositories

**Given** the user has configured authentication without repo scope
**When** the user runs `gitbrag list octocat --include-private`
**Then** the system raises a permissions error
**And** the error message explains that repo scope is required
**And** the error message provides guidance on updating token permissions
**And** the command exits with status code 1

### Requirement: Date format validation

The system MUST validate date inputs and provide clear error messages for invalid formats.

#### Scenario: Accept valid ISO date formats

**Given** various valid ISO date formats
**When** the user provides dates like "2024-01-01", "2024-01-01T00:00:00", or "2024-01-01T00:00:00Z"
**Then** the system parses all formats successfully
**And** the command proceeds with valid dates
**And** no validation errors occur

#### Scenario: Reject invalid date formats

**Given** an invalid date format like "01/01/2024" or "Jan 1, 2024"
**When** the user provides this as a date option
**Then** the system raises a validation error
**And** the error message explains the expected format (ISO 8601)
**And** the error message provides an example: "2024-01-01"
**And** the command exits with non-zero status

#### Scenario: Validate date range logic

**Given** a start date that is after the end date
**When** the user runs the list command
**Then** the system raises a validation error
**And** the error message explains start must be before end
**And** the error message shows the provided dates
**And** the command exits with non-zero status

### Requirement: Output formatting and visualization

The system MUST format pull request information in a clear, readable, and visually appealing terminal output using Rich library for enhanced display.

**Changes**: Added optional Star Increase column when --show-star-increase flag is provided.

#### Scenario: Display star increase in formatted table

**Given** a successful query returning PRs
**And** the user has passed the --show-star-increase flag with a date range
**When** the system formats the output
**Then** PRs are displayed in a Rich table with all standard columns
**And** the table includes an additional "Star Increase" column after the repository column
**And** star increases are displayed with "+" prefix for positive values (e.g., "+123")
**And** zero star increase is displayed as "0" or "+0"
**And** the table adjusts column widths to accommodate star increase data
**And** repositories with unavailable star data show "-" in the Star Increase column

#### Scenario: Hide star increase by default for cleaner output

**Given** a successful query returning PRs
**And** the user has not passed the --show-star-increase flag
**When** the system formats the output
**Then** the table does not include a Star Increase column
**And** the output remains compact and matches existing behavior
**And** no star data is fetched or displayed

### Requirement: Error handling and user feedback

The system MUST provide clear, actionable error messages for all failure scenarios.

#### Scenario: Display authentication errors

**Given** authentication fails due to invalid credentials
**When** the list command attempts to execute
**Then** the system displays a clear authentication error
**And** the error explains what went wrong
**And** the error suggests checking environment variables or --token option
**And** the error references documentation for setup
**And** the command exits with status code 1

#### Scenario: Display user not found errors

**Given** a GitHub username that does not exist
**When** the list command queries GitHub
**Then** the system displays a user not found error
**And** the error mentions the specific username
**And** the error suggests verifying the username spelling
**And** the command exits with status code 1

#### Scenario: Display rate limit errors

**Given** the GitHub API rate limit is exceeded
**When** the list command attempts a query
**Then** the system displays a rate limit error
**And** the error shows when the rate limit will reset
**And** the error suggests waiting until reset time
**And** the command exits with status code 1

#### Scenario: Display network errors

**Given** a network connectivity issue
**When** the list command attempts to query GitHub
**Then** the system displays a network error
**And** the error suggests checking internet connectivity
**And** the error suggests retrying the command
**And** the command exits with status code 1

#### Scenario: Display validation errors

**Given** invalid input (bad date format, invalid username format, etc.)
**When** the list command validates inputs
**Then** the system displays a validation error before making API calls
**And** the error explains what input is invalid
**And** the error provides guidance on correct format
**And** the command exits with status code 1

### Requirement: Help and documentation

The system MUST provide comprehensive help text accessible via the CLI.

#### Scenario: Display command help

**Given** the user is unsure about command usage
**When** the user runs `gitbrag list --help`
**Then** the system displays help text for the list command
**And** help includes command description
**And** help documents the username argument
**And** help documents all options (--since, --until, --token)
**And** help includes usage examples
**And** help references authentication setup

#### Scenario: Display global help

**Given** the user wants to see all available commands
**When** the user runs `gitbrag --help`
**Then** the system displays global help
**And** help lists all available commands including "list"
**And** help includes brief description of each command
**And** help explains how to get more help on specific commands

### Requirement: Async command execution

The system MUST execute CLI commands using async/await patterns while maintaining compatibility with Typer's synchronous interface.

#### Scenario: Execute async logic in sync CLI context

**Given** the list command implementation uses async functions
**And** Typer requires synchronous command functions
**When** the command is invoked
**Then** the syncify decorator converts async to sync execution
**And** the command runs async service calls correctly
**And** errors are propagated properly to the CLI layer
**And** the async event loop is managed automatically

#### Scenario: Handle async errors in sync context

**Given** an async service call raises an exception
**When** executing through the syncify wrapper
**Then** the exception is caught and handled properly
**And** the error message is displayed to the user
**And** the command exits with appropriate status code
**And** no async event loop errors occur

### Requirement: Command naming and organization

The system MUST organize CLI commands in a logical structure that supports future expansion.

#### Scenario: Use "list" as command name

**Given** the CLI application structure
**When** the user explores available commands
**Then** the command is named "list" (not "list-prs" or "show-prs")
**And** the command name is intuitive and concise
**And** the naming leaves room for future commands (export, report, etc.)

#### Scenario: Support future command expansion

**Given** the current CLI structure
**When** future commands are added (e.g., "report", "export")
**Then** the command structure accommodates additions
**And** command names follow consistent patterns
**And** the list command remains backward compatible

### Requirement: Repository star count display

The system MUST provide a CLI option to display star increase (stars gained during the time period) for repositories in the pull request report, defaulting to hiding this column for cleaner display.

#### Scenario: Hide star increase by default

**Given** the user has configured authentication
**When** the user runs `gitbrag list octocat`
**Then** the output displays PR information without a star increase column
**And** the display remains compact and easy to scan
**And** no additional GitHub API calls are made to fetch star data

#### Scenario: Display star increase when flag is provided

**Given** the user has configured authentication
**And** the user specifies a date range with --since and --until
**When** the user runs `gitbrag list octocat --show-star-increase --since 2024-01-01 --until 2024-12-31`
**Then** the system uses GraphQL API to fetch stargazer timestamps for all unique repositories
**And** the system counts stars added between 2024-01-01 and 2024-12-31 for each repository
**And** the output displays a "Star Increase" column showing the delta (e.g., "+123")
**And** the star increase reflects only stars gained during the specified time period

#### Scenario: Display unavailable star increase as placeholder

**Given** the user has configured authentication
**And** the user runs `gitbrag list octocat --show-star-increase --since 2024-01-01 --until 2024-12-31`
**When** star increase data cannot be fetched for a repository (deleted, permission denied, rate limit, etc.)
**Then** the system displays "-" or "N/A" in the Star Increase column for that repository
**And** the system logs a warning about the unavailable data
**And** the command continues successfully for other repositories
**And** the user is not blocked from seeing other data

#### Scenario: Combine star increase flag with other options

**Given** the user provides multiple flags
**When** the user runs `gitbrag list octocat --show-star-increase --show-urls --include-private --since 2024-01-01`
**Then** the output includes the Star Increase column as requested
**And** all other flags work correctly together
**And** the combined options produce expected filtered results with star increases

#### Scenario: Fetch star increase data efficiently with early termination

**Given** a repository gained 1000 stars total, with 200 during the period and 800 before
**And** stargazers are returned in chronological order (oldest first)
**When** the system fetches star increase data
**Then** the system uses GraphQL pagination to scan through stargazers
**And** the system counts stars with `starredAt` within the date range
**And** the system stops fetching when `starredAt` is before the `since` date (early termination)
**And** the system minimizes API calls by not fetching all historical stargazers unnecessarily

### Requirement: Repository star count sorting

The system MUST provide sorting capability by repository star increase when star data is displayed.

#### Scenario: Sort by star increase descending

**Given** the user has configured authentication
**And** the user has enabled star increase display
**When** the user runs `gitbrag list octocat --show-star-increase --sort stars:desc --since 2024-01-01`
**Then** the results are sorted by star increase in descending order (highest growth first)
**And** PRs from repositories with more star growth appear first
**And** PRs from the same repository maintain their relative order

#### Scenario: Sort by star increase ascending

**Given** the user has configured authentication
**And** the user has enabled star increase display
**When** the user runs `gitbrag list octocat --show-star-increase --sort stars:asc --since 2024-01-01`
**Then** the results are sorted by star increase in ascending order (lowest growth first)
**And** PRs from repositories with less star growth appear first

#### Scenario: Combine star sorting with other sort fields

**Given** the user has configured authentication
**When** the user runs `gitbrag list octocat --show-star-increase --sort repository --sort stars:desc --since 2024-01-01`
**Then** the results are sorted first by repository name alphabetically
**And** within each repository group, PRs are sub-sorted by star increase descending
**And** multi-field sorting works correctly

#### Scenario: Handle star sorting without flag

**Given** the user has not enabled star increase display
**When** the user runs `gitbrag list octocat --sort stars:desc --since 2024-01-01` (without --show-star-increase)
**Then** the system raises a validation error
**And** the error message explains that --show-star-increase is required to sort by stars
**And** the error suggests adding the --show-star-increase flag
**And** the command exits with status code 1

### Requirement: Repository star count caching

The system MUST cache repository star increase calculations to minimize redundant API calls and improve performance for repeated queries.

#### Scenario: Cache star increase for reuse

**Given** the user has configured authentication
**And** the user runs `gitbrag list octocat --show-star-increase --since 2024-01-01 --until 2024-12-31`
**When** the user runs the same command again within the cache TTL period
**Then** the system uses cached star increase data
**And** no additional GraphQL queries are made for star data
**And** the output displays the same star increases as before

#### Scenario: Respect cache TTL

**Given** the user has configured authentication
**And** the user ran `gitbrag list octocat --show-star-increase --since 2024-01-01` more than 24 hours ago
**When** the user runs the command again
**Then** the system fetches fresh star increase data from GitHub GraphQL API
**And** the cache is updated with new values
**And** the output displays current star increases

#### Scenario: Cache works across different queries with same date range

**Given** the user queries PRs from user A who contributed to repos X, Y, Z in 2024
**And** the user then queries PRs from user B who also contributed to repos Y, Z in 2024
**When** both queries use the same date range and are run with --show-star-increase within cache TTL
**Then** the system reuses cached star increase data for repos Y and Z
**And** the system only fetches fresh data for repo X (unique to user A query)
**And** performance is improved for overlapping repositories and date ranges

