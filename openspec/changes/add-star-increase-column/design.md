# Design: Star Increase Column

## Overview

This design document details the technical approach for adding an optional star increase column to the pull request report. The feature will display the actual change in repository star count from the beginning to the end of the filtered time period, using GitHub's GraphQL API to fetch stargazer timestamps.

## Architecture

### Component Changes

```text
gitbrag/services/github/
├── client.py         # MODIFY: Add async GraphQL query method using httpx
├── stargazers.py     # ADD: New module for stargazer fetching and star increase calculation
├── models.py         # ADD: StarIncrease dataclass with star delta
└── pullrequests.py   # MODIFY: Add optional star increase collection

gitbrag/services/
└── formatter.py      # MODIFY: Add optional star increase column

gitbrag/
└── cli.py            # MODIFY: Add --show-star-increase and --no-wait-for-rate-limit flags
```

### Data Flow

1. **User invokes CLI** with `--show-star-increase` flag and date range (--since/--until)
2. **PullRequestCollector** collects PRs as usual
3. **After PR collection**, if flag is set:
   - Extract unique repositories from PR list
   - For each repository, use GraphQL to fetch stargazer timeline with `starredAt` timestamps
   - Paginate through stargazers, counting those with `starredAt` within the date range
   - Use early termination: stop when `starredAt` is before `since` date
   - Calculate star increase (count of stars added during period)
4. **Formatter** receives PR list with star increase data
5. **Rich table** conditionally renders star increase column with "+" prefix for positive values

### API Interactions

#### GraphQL Stargazers Endpoint

```graphql
query {
  repository(owner: "owner", name: "repo") {
    stargazers(first: 100, after: "cursor", orderBy: {field: STARRED_AT, direction: DESC}) {
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

**Response structure:**

```json
{
  "data": {
    "repository": {
      "stargazers": {
        "pageInfo": {
          "endCursor": "Y3Vyc29yOnYyOpK5MjAyNC0wMS0wMVQxMjowMDowMFo=",
          "hasNextPage": true
        },
        "edges": [
          {"starredAt": "2024-12-16T14:20:00Z"},
          {"starredAt": "2024-12-15T10:30:00Z"}
        ]
      }
    }
  }
}
```

**Key considerations:**

- GraphQL endpoint: `https://api.github.com/graphql` (POST)
- Rate limit: 5000 points/hour (each query costs points based on complexity)
- Pagination: 100 stargazers per request (maximum allowed)
- **Verified ordering**: Default is ASC (oldest first), but we use DESC (newest first) to optimize for common use case
- **Optimized for recent data**: DESC ordering means most recent stars appear first, enabling early termination for typical queries (last 1-2 years)
- Early termination: Stop paginating when `starredAt` < `since` date (works efficiently with DESC since we encounter recent data first)
- **No date filtering**: GraphQL API does not support filtering stargazers by date range in the query itself - must filter client-side

### Data Model Changes

#### New: StarIncrease Model

```python
@dataclass
class StarIncrease:
    """Star increase information for a repository during a time period."""

    repository: str  # Full name: "owner/repo"
    increase: int  # Number of stars added during period
    since: datetime  # Start of period
    until: datetime  # End of period
```

**Implementation approach:** Keep star increase data separate in a dictionary keyed by repository name, passed to formatter. This avoids modifying the core PR model and keeps star data optional.

## Implementation Strategy

### Phase 1: GraphQL Query Support

1. Add `execute_graphql()` async method to existing `GitHubClient` in `client.py` using httpx
2. Create `gitbrag/services/github/stargazers.py` module with async function for fetching stargazers
3. Implement stargazer query with pagination, early termination, and rate limit handling
4. Use existing GitHub token authentication (same as REST API)

### Phase 2: Star Increase Calculation

1. Add method to fetch and count stargazers within date range
2. Implement pagination logic with early termination
3. Handle errors gracefully (repository not found, permissions, etc.)
4. Return dictionary mapping repository name to star increase

### Phase 3: Display Integration

1. Add `--show-star-increase` CLI flag
2. Add `--no-wait-for-rate-limit` CLI flag (default: wait enabled)
3. Modify formatter to accept optional star increase data
4. Add conditional column rendering in Rich table
5. Display star delta with "+" prefix for positive values

### Phase 4: Optimization

1. Add caching for star increase results (keyed by repo + date range)
2. Implement concurrent GraphQL queries for multiple repositories
3. Add intelligent rate limit handling with automatic wait and recovery
4. Optimize query performance with smart pagination

## Star Increase Calculation Algorithm

### GraphQL Query Strategy

1. **Initialize**: Set `since` and `until` dates from CLI arguments
2. **For each unique repository**:
   - Start GraphQL pagination with `first: 100, orderBy: {field: STARRED_AT, direction: DESC}`
   - For each page of stargazers (newest first):
     - Skip stars where `starredAt` > `until` (too recent)
     - Count stars where `starredAt` is between `since` and `until`
     - If `starredAt` of last edge < `since`, stop (early termination - we've passed our date range)
     - If `pageInfo.hasNextPage`, continue with `after: endCursor`
   - Return total count of stars added during period

### Optimization: Reverse Chronological Order

Using DESC (newest first) ordering is critical for performance with typical use cases:

- **Common case** (last 1-2 years): Recent stars appear on first pages, allowing early termination after a few queries
- **Example**: Repository with 10k total stars, querying last year with 200 new stars
  - With DESC: Read first 2-3 pages (~200-300 stars), find all 200 recent stars, terminate
  - With ASC: Would need to read all 100 pages (~10k stars) to find the 200 recent ones at the end
- Early termination happens when `starredAt` < `since` (we've gone too far back in history)

### Example Calculation

**Scenario**: User queries PRs from 2024-01-01 to 2024-12-31

**Repository with 5000 total stars** (gained 200 stars in 2024):

With DESC ordering (newest first):

- Page 1 (100 stars): 50 from 2025 (skip), 50 from 2024 (count)
- Page 2 (100 stars): 100 from 2024 (count)
- Page 3 (100 stars): 50 from 2024 (count), 50 from 2023 (stop - early termination)
- Result: +200 stars during 2024
- API calls: **3 queries** (optimal for recent data)

With ASC ordering (oldest first) - INEFFICIENT:

- Pages 1-48 (4800 stars): All from 2020-2023 (skip all)
- Page 49 (100 stars): 100 from 2024 (count)
- Page 50 (100 stars): 100 from 2024 (count)
- Result: +200 stars during 2024
- API calls: **50 queries** (must scan entire history)

**Optimization benefit**: DESC ordering reduces API calls by ~94% for typical recent date ranges

## Error Handling

### Scenarios

1. **Repository deleted**: Display "-" or "N/A"
2. **Insufficient permissions**: Log warning, display "-"
3. **Rate limit exceeded**: Wait for rate limit reset (default behavior, can be disabled with flag)
4. **Repository not found**: Display "-"

### Strategy

- Catch exceptions per repository
- Don't fail entire command if one repo's data unavailable
- Log warnings for debugging
- Display clear indicator in table for missing data

### Rate Limit Handling

When GraphQL API rate limit is exceeded:

1. **Default behavior** (wait enabled):
   - Parse rate limit reset time from API response headers (`X-RateLimit-Reset`)
   - Calculate wait duration until reset
   - Log clear message: "GraphQL rate limit exceeded. Waiting until [timestamp] (X minutes) for reset..."
   - Sleep until rate limit resets
   - Resume operation automatically

2. **Opt-out behavior** (with `--no-wait-for-rate-limit` flag):
   - Display error message about rate limit
   - Exit gracefully with clear instructions
   - Return partial results collected before rate limit

3. **Implementation details**:
   - Check rate limit headers proactively before requests when possible
   - Handle both primary rate limit and secondary abuse detection
   - Respect `Retry-After` header if present
   - Display progress indicator during wait (e.g., countdown timer)

## Performance Considerations

### API Call Optimization

For a typical report with N PRs across M unique repositories:

- PR search: ~1-3 REST API calls (paginated)
- Star increase data: Variable GraphQL queries per repository (depends on star count and date range)

**Best case** (DESC with recent date range - typical usage): Repository with recent star activity

- Queries needed: 1-5 (early termination after finding all recent stars)
- Example: Last year's data appears in first few pages

**Worst case** (DESC with old date range): Querying stars from many years ago

- Queries needed: Must paginate through all recent stars to reach historical range
- Example: Querying 2020 data when repo has 10k stars from 2021-2024
- Mitigation: This is rare - users typically query recent contributions

**Optimization**: DESC ordering with early termination optimized for 95% of use cases (recent date ranges, default 1-year lookback)

### Caching Strategy

Use existing `aiocache` infrastructure:

- Cache key: `repo:{owner}/{repo}:star_increase:{since}:{until}`
- TTL: 24 hours (star counts for past periods don't change)
- Reduces repeated calculations for same repository and date range
- Cache hit avoids all GraphQL queries for that repository

### Concurrent Fetching

Fetch star increase data for multiple repositories concurrently using `asyncio.gather()`:

- Minimize total request time
- Already implemented pattern in `client.py`
- GraphQL rate limits are separate from REST API


## Testing Strategy

### Unit Tests

1. Test `get_repository()` client method
2. Test formatter with and without star data
3. Test CLI flag parsing
4. Test error handling for missing data

### Integration Tests

1. Test with mock GitHub API responses
2. Test with various repository counts
3. Test rate limiting behavior
4. Test caching effectiveness

### Manual Testing

1. Test with real GitHub token
2. Test with repositories of varying sizes
3. Test with deleted repositories
4. Test with private repositories

## Security Considerations

- No new authentication requirements
- Uses existing token permissions
- Repository endpoint accessible with `public_repo` scope
- No sensitive data exposed

## Backward Compatibility

- Feature is opt-in via flag
- No changes to existing behavior without flag
- No data model changes that affect serialization
- Tests updated to maintain existing functionality

## Future Enhancements

## Future Enhancements

1. **Performance optimizations**: Further optimize GraphQL queries and caching strategies
2. **Other metrics**: Forks, watchers, contributors with timeline data
3. **Comparative metrics**: "Your PRs contributed to projects that gained X total stars"
4. **Visualization**: Charts or graphs for star growth over time
5. **Configurable page size**: Allow tuning GraphQL batch size based on repository characteristics

## Open Implementation Questions

1. Should we fetch stars concurrently or sequentially?
   - **Answer**: Concurrently using asyncio.gather() for performance across multiple repositories

2. Should we cache star increase calculations?
   - **Answer**: Yes, 24-hour TTL reasonable since historical data doesn't change

3. What happens if star fetching fails for some repos?
   - **Answer**: Display "-", log warning, continue with other repos

4. Should this work with `--include-private`?
   - **Answer**: Yes, should work with both public and private repos (same token permissions)

5. What GraphQL library should we use?
   - **Answer**: Use `httpx` directly (already a dependency) with manual GraphQL queries - simpler than adding `gql` library for a single query

## Implementation Summary

**Original request**: Display star increase from start to end of time period

**Implementation approach**: Use GitHub GraphQL API with `stargazers` and `starredAt` timestamps

**Key features**:

- Actual star increase calculation (not approximation or current total)
- Early termination optimization based on chronological ordering
- Aggressive caching (24-hour TTL for historical data)
- Concurrent fetching across repositories
- Graceful error handling and rate limit management

**Result**: Provides accurate star increase data that meets the original requirement while remaining practical through smart optimizations.
