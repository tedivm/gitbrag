# GitHub API Integration

This project integrates with GitHub's API to collect and display user contributions, specifically pull requests across all repositories and organizations.

## Overview

The GitHub integration provides:

- **Authentication**: Personal Access Token (PAT) support
- **PR Collection**: Gather all pull requests authored by a user
- **Filtering**: Filter by date range and repository visibility
- **Rate Limiting**: Automatic rate limit detection and exponential backoff
- **Async Operations**: High-performance async HTTP client using httpx

## Architecture

### Components

```
gitbrag/services/github/
├── auth.py           # Authentication and client factory
├── client.py         # Async GitHub API client with rate limiting
├── pullrequests.py   # PR collection service
└── models.py         # Data models (PullRequestInfo)
```

### Flow

1. **Authentication**: `GitHubClient` factory creates authenticated `GitHubAPIClient`
2. **Collection**: `PullRequestCollector` uses client to search GitHub API
3. **Pagination**: Client automatically handles pagination for large result sets
4. **Rate Limiting**: Exponential backoff on rate limit hits with header monitoring
5. **Transformation**: Raw API responses converted to `PullRequestInfo` models

## Authentication Setup

### Personal Access Token (PAT)

#### Creating a PAT

1. Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token (classic)"
3. Set a descriptive name (e.g., "GitBrag CLI")
4. Select scopes:
   - `public_repo` - Access public repositories (minimum required)
   - `repo` - Full control of private repositories (only if using `--include-private`)
5. Click "Generate token"
6. Copy the token immediately (you won't see it again)

#### Configuring the Token

**Option 1: Environment Variable**

```bash
export GITHUB_TOKEN="ghp_your_token_here"
```

**Option 2: .env File** (recommended for development)

Create a `.env` file in the project root:

```bash
GITHUB_TOKEN=ghp_your_token_here
```

**Option 3: CLI Override**

Pass the token directly to commands:

```bash
gitbrag list username --token ghp_your_token_here
```

### Token Permissions

Different use cases require different permissions:

| Use Case | Required Scope | Notes |
|----------|---------------|-------|
| Public repositories only | `public_repo` | Default, safest option |
| Include private repos | `repo` | Grants full repository access |

## Usage

### Basic PR Collection

List all pull requests from the last year:

```bash
gitbrag list username
```

### Date Range Filtering

The `--since` and `--until` options filter by **last activity** (updated time), not just creation date. This means a PR created last year but merged this year will appear in this year's results.

```bash
# PRs with activity in the last month
gitbrag list username --since 2024-11-14 --until 2024-12-14

# PRs active this year
gitbrag list username --since 2024-01-01
```

### Including Private Repositories

Requires a token with `repo` scope:

```bash
gitbrag list username --include-private
```

### Display Options

Show PR URLs in output:

```bash
gitbrag list username --show-urls
```

Show repository star increases during the filtered period:

```bash
gitbrag list username --since 2024-12-14 --show-star-increase
```

### Sorting Results

Sort by one or more fields:

```bash
# Sort by repository name
gitbrag list username --sort repository

# Sort by merge date (newest first)
gitbrag list username --sort merged:desc

# Multi-field sort: repository, then by merge date
gitbrag list username --sort repository --sort merged:desc

# Sort by star increase (requires --show-star-increase)
gitbrag list username --show-star-increase --sort stars:desc
```

Valid sort fields:

- `repository` - Repository full name (owner/repo)
- `state` - PR state (merged, open, closed)
- `created` - Creation date
- `merged` - Merge date
- `title` - PR title
- `stars` - Repository star increase (requires `--show-star-increase` flag)

Valid sort orders:

- `asc` - Ascending (default for most fields)
- `desc` - Descending (default for date fields)

## API Details

### GitHub Search API

The integration uses GitHub's [Search Issues API](https://docs.github.com/en/rest/search#search-issues-and-pull-requests) with the following query patterns:

```
is:pr author:username updated:2024-01-01..2024-12-31
```

Query components:

- `is:pr` - Filter to pull requests only
- `author:username` - Filter by PR author
- `updated:YYYY-MM-DD..YYYY-MM-DD` - Filter by last update/activity time

### GitHub GraphQL API

For star increase data, the integration uses GitHub's [GraphQL API](https://docs.github.com/en/graphql) to fetch stargazer timestamps:

```graphql
query($owner: String!, $name: String!, $cursor: String) {
  repository(owner: $owner, name: $name) {
    stargazers(first: 100, after: $cursor, orderBy: {field: STARRED_AT, direction: DESC}) {
      edges {
        starredAt
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
}
```

**Optimization Strategy:**

- **Pagination**: Fetches 100 stargazers per page
- **DESC Ordering**: Most recent stars first enables early termination
- **Early Termination**: Stops fetching when `starredAt < since` date
- **Concurrent Fetching**: Multiple repositories fetched in parallel
- **Deduplication**: Unique repositories extracted from PR list
- **Caching**: Results cached for 24 hours to minimize API calls

**Rate Limiting:**

GraphQL shares the same rate limits as REST API (5,000 requests/hour). The client implements:

- Automatic retry with exponential backoff on 429/403 responses
- Optional wait for rate limit reset (`wait_for_rate_limit` parameter)
- Cache to avoid redundant queries for same repositories

### Rate Limiting

GitHub's rate limits:

- **Authenticated requests**: 5,000 requests/hour for core API, 30 requests/minute for search
- **Unauthenticated**: 60 requests/hour (not supported in this project)

The client automatically handles rate limiting:

1. **Detection**: Monitors `X-RateLimit-Remaining` header and 429 status codes
2. **Backoff**: Exponential backoff (1s, 2s, 4s, 8s, etc.)
3. **Reset Time**: Waits until `X-RateLimit-Reset` time when limit is hit
4. **Retry**: Automatically retries failed requests up to max_retries (default: 3)

### Pagination

The GitHub Search API returns up to 100 results per page. The client automatically:

1. Makes initial request with `per_page=100`
2. Checks `total_count` in response
3. Calculates required pages
4. Fetches remaining pages sequentially
5. Combines all results

Large result sets are handled transparently - no user intervention needed.

## Data Models

### PullRequestInfo

```python
@dataclass
class PullRequestInfo:
    number: int                    # PR number
    title: str                     # PR title
    repository: str                # Full repo name (owner/repo)
    organization: str              # Organization/owner name
    author: str                    # PR author username
    state: str                     # "open" or "closed"
    created_at: datetime           # Creation timestamp
    closed_at: datetime | None     # Close timestamp (if closed)
    merged_at: datetime | None     # Merge timestamp (if merged)
    url: str                       # GitHub URL to PR
```

## Error Handling

### Common Errors

**Authentication Failure**

```
Error: 401 Unauthorized
```

- **Cause**: Invalid or expired token
- **Solution**: Generate a new token and update configuration

**Rate Limit Exceeded**

```
Error: 403 Forbidden - Rate limit exceeded
```

- **Cause**: Too many requests in short time
- **Solution**: Wait for rate limit reset (handled automatically with backoff)

**User Not Found**

```
Error: 422 Unprocessable Entity
```

- **Cause**: Invalid username or user doesn't exist
- **Solution**: Verify username spelling

**Permission Denied**

```
Error: Access forbidden - check token permissions
```

- **Cause**: Token lacks required scopes for private repos
- **Solution**: Regenerate token with `repo` scope if using `--include-private`

## Security Best Practices

### Token Storage

✅ **DO:**

- Store tokens in `.env` file (gitignored)
- Use environment variables in production
- Use secret management services in CI/CD
- Regenerate tokens periodically

❌ **DON'T:**

- Hardcode tokens in source code
- Commit `.env` files to version control
- Share tokens in chat/email
- Use tokens with broader permissions than needed

### Token Security

The project uses Pydantic's `SecretStr` to:

- Prevent accidental token logging
- Mask tokens in error messages
- Protect tokens in memory dumps

Tokens are never logged or displayed in output.

### Minimal Permissions

Always use the minimum required scope:

- Public repos only → `public_repo` scope
- Private repos needed → `repo` scope

## Troubleshooting

### "No pull requests found"

**Possible causes:**

1. User has no PRs in the date range
2. User has no public PRs (need `--include-private`)
3. Date range is too restrictive
4. Username is incorrect

**Solutions:**

```bash
# Try wider date range
gitbrag list username --since 2020-01-01

# Include private repos
gitbrag list username --include-private

# Verify username exists
curl https://api.github.com/users/username
```

### Slow Performance

**Causes:**

- Large number of PRs requiring many API calls
- Rate limiting causing delays
- Network latency

**Solutions:**

- Narrow date range to reduce results
- Use more specific filters
- Monitor rate limits: check `X-RateLimit-Remaining` in debug logs

**Enable debug logging:**

```bash
export LOG_LEVEL=DEBUG
gitbrag list username
```

### Token Permission Issues

**Symptoms:**

- Can see public repos but not private ones
- "Access forbidden" errors

**Solution:**
Regenerate token with correct scopes (see [Creating a PAT](#creating-a-pat))

## Performance Considerations

### Optimization Tips

1. **Narrow Date Ranges**: Smaller ranges = fewer API calls

   ```bash
   gitbrag list username --since 2024-01-01 --until 2024-12-31
   ```

2. **Public Only**: Skip `--include-private` if not needed

   ```bash
   gitbrag list username  # Faster than --include-private
   ```

3. **Caching**: Results are not cached - each run queries GitHub API fresh

### Expected Performance

| PRs | API Calls | Time (approx) |
|-----|-----------|---------------|
| <100 | 1-2 | <1 second |
| 100-500 | 2-5 | 1-3 seconds |
| 500-1000 | 5-10 | 3-5 seconds |
| >1000 | 10+ | 5+ seconds |

*Times assume no rate limiting and good network conditions*

## Development

### Testing Against GitHub API

The project includes integration tests that can run against the real GitHub API:

```bash
# Set token in .env
echo "GITHUB_TOKEN=your_token" > .env

# Run integration tests (not skipped with token present)
pytest tests/integration/test_github_integration.py -v
```

### Testing Without API Access

Unit tests mock the GitHub API:

```bash
# Run all tests (mocked, no token needed)
make tests
```

### Manual API Testing

A test script is provided for manual API verification:

```bash
python test_github_api.py
```

This script:

- Verifies token authentication
- Checks rate limits
- Tests search queries
- Shows raw API responses

## References

- [GitHub REST API Documentation](https://docs.github.com/en/rest)
- [Search API Reference](https://docs.github.com/en/rest/search)
- [Rate Limiting](https://docs.github.com/en/rest/overview/rate-limits-for-the-rest-api)
- [Personal Access Tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token)
- [httpx Documentation](https://www.python-httpx.org/)
