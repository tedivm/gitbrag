# Spec: Contribution Report CLI

## ADDED Requirements

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

#### Scenario: Sort by default (created date descending)

**Given** the user has configured authentication
**When** the user runs `gitbrag list octocat` without sort options
**Then** the results are sorted by creation date in descending order (newest first)
**And** the most recent PRs appear at the top of the list

#### Scenario: Sort by single field

**Given** the user has configured authentication
**When** the user runs `gitbrag list octocat --sort repository`
**Then** the results are sorted alphabetically by repository name
**And** PRs are grouped together by repository

#### Scenario: Sort by multiple fields with primary and secondary sort

**Given** the user has configured authentication
**When** the user runs `gitbrag list octocat --sort repository --sort merged`
**Then** the results are sorted first by repository name alphabetically
**And** within each repository, PRs are sorted by merge date
**And** unmerged PRs appear after merged PRs within each repository

#### Scenario: Sort with explicit order direction

**Given** the user has configured authentication
**When** the user runs `gitbrag list octocat --sort repository:asc --sort created:desc`
**Then** the results are sorted by repository in ascending order (A-Z)
**And** within each repository, PRs are sorted by created date descending (newest first)

#### Scenario: Sort by state with custom ordering

**Given** the user has configured authentication
**When** the user runs `gitbrag list octocat --sort state --sort created`
**Then** the results are grouped by state (merged, open, closed)
**And** within each state group, PRs are sorted by creation date

#### Scenario: Handle invalid sort field

**Given** the user provides an invalid sort field
**When** the user runs `gitbrag list octocat --sort invalid_field`
**Then** the system raises a validation error
**And** the error message lists valid sort fields (repository, state, created, merged, title)
**And** the error message provides an example of correct usage
**And** the command exits with status code 1

#### Scenario: Handle invalid sort direction

**Given** the user provides an invalid sort direction
**When** the user runs `gitbag list octocat --sort repository:invalid`
**Then** the system raises a validation error
**And** the error message explains valid directions are 'asc' and 'desc'
**And** the command exits with status code 1

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

#### Scenario: Display PR list with formatted output including PR numbers

**Given** a successful query returning multiple PRs
**When** the system formats the output
**Then** the output includes a styled header with username and date range
**And** each PR is displayed with PR number, title, repository, state, and date
**And** PR numbers are clearly visible (e.g., "#42")
**And** PRs are grouped by repository with clear visual separation
**And** the output uses colors to distinguish different states (merged, open, closed)
**And** the output includes a summary footer with total count of PRs

#### Scenario: Use Rich tables for structured display

**Given** a successful query returning PRs
**When** the system formats the output with default settings
**Then** PRs are displayed in a Rich table with columns
**And** the table includes columns for PR number, state, title, repository, and date
**And** the table does not include a URL column by default
**And** the table is automatically sized to fit terminal width
**And** the table uses appropriate padding and borders for readability

#### Scenario: Display URLs when requested via flag

**Given** a successful query returning PRs
**And** the user has passed the --show-urls flag
**When** the system formats the output
**Then** PRs are displayed in a Rich table with columns
**And** the table includes an additional URL column
**And** each row shows the full GitHub URL for the PR
**And** the table adjusts column widths to accommodate URLs

#### Scenario: Hide URLs by default for cleaner output

**Given** a successful query returning PRs
**And** the user has not passed the --show-urls flag
**When** the system formats the output
**Then** the table does not include a URL column
**And** the output is more compact and easier to scan
**And** PR numbers provide sufficient reference for finding PRs

#### Scenario: Apply color coding to PR states

**Given** PRs with different states (merged, open, closed)
**When** displaying the results
**Then** merged PRs are displayed in green or with a green indicator
**And** open PRs are displayed in blue or with a blue indicator
**And** closed PRs are displayed in yellow/orange or with an appropriate indicator
**And** color choices follow common terminal conventions

#### Scenario: Display empty results with styled message

**Given** a query returning no pull requests
**When** the system formats the output
**Then** the output shows a styled panel with username and date range
**And** the panel includes a clearly formatted "No pull requests found" message
**And** the output maintains visual consistency with non-empty results
**And** the command exits successfully (not as an error)

#### Scenario: Format dates consistently

**Given** PRs with various creation and merge dates
**When** displaying the results
**Then** dates are formatted in readable format (YYYY-MM-DD)
**And** relative time information is shown when helpful (e.g., "3 months ago")
**And** date formatting is consistent across all PRs

#### Scenario: Handle terminal width gracefully

**Given** a PR with a long title or repository name
**When** displaying the results in terminals of various widths
**Then** content wraps or truncates appropriately for terminal width
**And** table columns adjust to available space
**And** the output remains readable in narrow terminals (>80 chars)
**And** critical information (PR number, repository) is never truncated

#### Scenario: Show progress indication for long operations

**Given** a query that takes more than 2 seconds to complete
**When** the system is fetching pull requests
**Then** a progress spinner or indicator is displayed
**And** the indicator shows the system is working
**And** the indicator disappears when results are ready
**And** the user is not left wondering if the command is frozen

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
