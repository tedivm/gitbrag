# contribution-report-cli Specification Delta

## ADDED Requirements

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

## MODIFIED Requirements

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

## REMOVED Requirements

None - this change only adds functionality without removing existing features.

## Notes

### API Limitation: Historical Star Counts

GitHub's REST API does not provide a straightforward way to query historical star counts. The `/repos/{owner}/{repo}/stargazers` endpoint exists but does not include `starredAt` timestamps by default.

To calculate a true "star increase" during the time period requires using the **GraphQL API**:

```graphql
{
  repository(owner: "owner", name: "repo") {
    stargazers(first: 100, after: "cursor") {
      pageInfo {
        endCursor
        hasNextPage
      }
      edges {
        starredAt
      }
    }
  }
}
```

This approach would require:

1. Adding a GraphQL client to the project
2. Paginating through all stargazers (100 per query)
3. Filtering to count stars added within the date range
4. Managing GraphQL rate limits (separate from REST API limits)

For a repository with 10,000 stars, this would require 100 GraphQL queries per repository. With multiple repositories, this quickly exhausts rate limits.

**Solution**: Display current total star count instead of time-period delta. This provides value by showing project popularity and scale while remaining performant and reliable.

### Implementation Approach

- Flag name: `--show-star-increase` (accurately describes the feature)
- Column name: "Star Increase" or "Stars +" (clear that it's a delta)
- API: GitHub GraphQL API with `stargazers` query and `starredAt` field
- Caching: 24-hour TTL via existing `aiocache` infrastructure (historical data doesn't change)
- Concurrent fetching: Use `asyncio.gather()` for parallel GraphQL queries across repositories
- Early termination: Stop fetching when `starredAt` < `since` date (stargazers are chronological)

### Future Enhancement

If further optimizations are needed or if GitHub improves the GraphQL API, the feature can be enhanced with:

- Smarter pagination strategies
- Parallel query batching
- More aggressive caching strategies
- Alternative data sources

The current design provides accurate star increase data as requested while remaining practical through smart optimizations.
