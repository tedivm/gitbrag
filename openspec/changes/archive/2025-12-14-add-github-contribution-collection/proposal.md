# Proposal: GitHub Contribution Collection

## Overview

Implement the core functionality of GitBrag by creating a CLI that collects and displays a user's GitHub pull requests from a specified time period. This foundational feature enables developers to query their open source contributions and serves as the basis for future reporting and visualization capabilities.

## Problem

Developers need a way to showcase their open source contributions for performance reviews, portfolio building, and professional self-promotion. Currently, there's no straightforward tool to aggregate and report GitHub contributions across repositories over a specified time period.

## Solution

Create a CLI command that:

- Accepts a GitHub username as input
- Queries the GitHub API for all pull requests created by that user across all organizations and repositories
- Defaults to public repositories only, with an optional flag to include private repositories
- Filters results by a time period (defaulting to one year)
- Displays the results in a clear, readable format

The solution will use the PyGithub library for GitHub API access and support two authentication methods:

1. **Personal Access Token (PAT)**: Simple token-based authentication for individual users
2. **GitHub App with OAuth**: Modern OAuth flow where the app acts on behalf of the user, enabling access to user-specific data and private repositories

## Scope

### In Scope

1. **GitHub Authentication System**
   - PAT-based authentication configuration
   - GitHub App OAuth flow (user authorization, token exchange)
   - Secure credential storage using Pydantic SecretStr
   - Authentication state management and token refresh

2. **Pull Request Collection**
   - Query GitHub API for user's pull requests across all organizations and repositories
   - Filter by repository visibility (public by default, optional private)
   - Filter by date range (start date, end date)
   - Retrieve essential PR metadata (title, repository, URL, state, created date, merged date)
   - Handle pagination for users with many contributions

3. **CLI Interface**
   - `gitbrag list <username>` command
   - `--since` option for start date (default: one year ago)
   - `--until` option for end date (default: today)
   - `--include-private` flag to include private repositories (default: public only)
   - `--show-urls` flag to display PR URLs in output (default: hidden for cleaner display)
   - `--sort` option for sorting results with multiple sort fields (default: created date descending)
   - `--token` option for PAT authentication
   - Environment variable support for authentication
   - Clear error messages for authentication failures

### Out of Scope

- Web interface or API endpoints
- Advanced visualizations (charts, graphs)
- Statistics or analytics on contributions
- Issue tracking or other GitHub entities
- Multi-user or team reporting
- Export functionality (CSV, JSON, etc.)
- Caching of GitHub API responses

## User Impact

### Affected Users

- Developers using GitBrag CLI to track their contributions
- First-time users setting up authentication

### Benefits

- Quick access to contribution history without manual GitHub searches
- Well-formatted, readable CLI output with colors and structure
- Simple authentication setup with clear documentation
- Foundation for future reporting features

### Migration Path

N/A - This is the initial implementation with no existing users.

## Dependencies

### New Libraries

- **PyGithub (>=2.5.0)**: Official GitHub API client for Python
  - Provides typed interfaces to GitHub API
  - Handles authentication, pagination, and rate limiting
  - Active maintenance and good documentation
  - Async support through aiohttp integration

### Existing Libraries

- **pydantic-settings**: For configuration management
- **typer**: For CLI commands
- **rich**: For terminal formatting and visualization
- **httpx**: For testing API interactions

## Technical Considerations

### Authentication Strategy

Two authentication methods will be supported:

1. **PAT (Personal Access Token)**:
   - Simplest for individual users
   - Configured via environment variable or CLI option
   - Requires `read:user` scope for public repositories
   - Requires `repo` scope for private repositories (when using `--include-private` flag)

2. **GitHub App with OAuth**:
   - Modern authentication approach with better rate limits
   - Uses OAuth flow to act on behalf of the authenticated user
   - Requires app ID, client ID, and client secret
   - User must authorize the app via browser-based OAuth flow
   - Access token is user-specific, enabling access to user's private data
   - Configured via environment variables (app credentials) and OAuth callback

### API Rate Limiting

- GitHub API has rate limits (5000/hour authenticated, 60/hour unauthenticated)
- PyGithub provides built-in rate limit checking
- Initial implementation will handle rate limit exceptions with clear error messages
- Future: Implement caching to reduce API calls

### Date Handling

- Use Python's datetime module with timezone awareness
- Default time range: one year from current date
- Accept ISO 8601 date formats for user input

## Alternatives Considered

### Alternative Libraries

1. **ghapi**: FastCore-based GitHub API client
   - Pros: Lightweight, fast
   - Cons: Less mature, smaller community

2. **gidgethub**: Async-first GitHub API client
   - Pros: Fully async, modern
   - Cons: Lower-level, requires more boilerplate

3. **requests + manual API calls**
   - Pros: Full control, no new dependencies
   - Cons: Significant development time, reinventing the wheel

**Decision**: PyGithub chosen for its maturity, comprehensive documentation, and built-in handling of pagination and rate limiting.

### Authentication Approaches

1. **Installation Token (GitHub App as Installation)**: App acts as itself
   - Pros: Simpler implementation
   - Cons: Cannot access user-specific data, limited to organization repositories

2. **OAuth Flow (GitHub App on behalf of User)**: App acts as the user
   - Pros: Full access to user's data including private repos
   - Cons: Requires browser-based OAuth flow, more complex setup

3. **SSH Key Authentication**: Use Git SSH keys
   - Pros: Leverages existing credentials
   - Cons: Limited API scope, complex implementation

**Decision**: PAT for simplicity and GitHub App with OAuth flow for enterprise use. OAuth flow is essential because the app needs to act as the user to access their pull requests across all organizations, including private repositories.

## Open Questions

None - Requirements are clear and well-defined for this initial implementation.

## Success Criteria

1. Users can authenticate using either PAT or GitHub App credentials
2. CLI command successfully retrieves and displays pull requests for any valid GitHub username
3. Date filtering works correctly with custom and default date ranges
4. Error handling provides clear, actionable messages
5. All code passes type checking and linting
6. Test coverage meets project standards (>80%)
7. Documentation explains authentication setup and command usage

## Related Work

- None (initial implementation)

## References

- [GitHub REST API - Pull Requests](https://docs.github.com/en/rest/pulls/pulls)
- [PyGithub Documentation](https://pygithub.readthedocs.io/)
- [GitHub App Authentication](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/about-authentication-with-a-github-app)
- [Personal Access Tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)
