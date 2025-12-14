# Design: GitHub Contribution Collection

## Architecture Overview

The implementation follows a layered architecture with clear separation of concerns:

```
CLI Layer (gitbrag/cli.py)
    ↓
Service Layer (gitbrag/services/github/)
    ↓
Configuration Layer (gitbrag/conf/settings.py)
    ↓
GitHub API (via PyGithub)
```

## Component Design

### 1. Authentication Service

**Location**: `gitbrag/services/github/auth.py`

**Responsibilities**:

- Create authenticated GitHub client instances
- Support PAT and GitHub App OAuth authentication methods
- Handle OAuth flow (browser launch, callback server, token exchange)
- Manage OAuth token storage and refresh
- Validate credentials and handle auth errors
- Provide rate limit information

**Key Classes**:

```python
class GitHubAuthType(str, Enum):
    """Supported GitHub authentication types."""
    PAT = "pat"
    GITHUB_APP = "github_app"

class OAuthCallbackServer:
    """Local HTTP server to receive OAuth callback."""

    def __init__(self, port: int = 8080):
        """Initialize callback server."""

    async def start(self) -> str:
        """Start server and wait for authorization code."""

    def stop(self) -> None:
        """Stop callback server."""

class GitHubOAuthFlow:
    """Handle GitHub App OAuth authentication flow."""

    def __init__(self, client_id: str, client_secret: SecretStr):
        """Initialize OAuth flow handler."""

    async def initiate_flow(self) -> str:
        """Start OAuth flow and return authorization URL."""

    async def complete_flow(self, code: str) -> str:
        """Exchange authorization code for access token."""

    def get_cached_token(self) -> str | None:
        """Retrieve cached user access token if valid."""

    async def refresh_token(self) -> str:
        """Refresh expired token (if refresh token available)."""

class GitHubClient:
    """Wrapper for PyGithub client with authentication."""

    def __init__(self, settings: GitHubSettings):
        """Initialize with settings."""

    async def get_authenticated_client(self) -> Github:
        """Return authenticated PyGithub client.

        For PAT: Use token directly.
        For GitHub App: Complete OAuth flow if needed, use user access token.
        """

    def get_rate_limit(self) -> dict:
        """Get current rate limit status."""
```

**Design Decisions**:

- Use factory pattern to create appropriate client based on auth type
- GitHub App OAuth flow uses user authorization (not installation tokens)
- Token acts on behalf of the user, providing access to user's data
- Cache OAuth tokens securely (keyring or encrypted file) to avoid repeated auth
- Local callback server on localhost:8080 (configurable port)
- Browser opens automatically for OAuth authorization
- Lazy client initialization to avoid unnecessary API calls
- Use syncify decorator for Typer compatibility

### 2. Pull Request Collection Service

**Location**: `gitbrag/services/github/pullrequests.py`

**Responsibilities**:

- Query GitHub for user's pull requests across all organizations and repositories
- Filter by repository visibility (public/private)
- Filter by date range
- Handle pagination automatically
- Transform API responses to domain models

**Key Classes**:

```python
@dataclass
class PullRequestInfo:
    """Domain model for pull request information."""
    title: str
    repository: str
    url: str
    state: str
    created_at: datetime
    merged_at: datetime | None
    number: int

class PullRequestCollector:
    """Collects pull requests from GitHub API."""

    def __init__(self, client: Github):
        """Initialize with authenticated client."""

    async def collect_user_prs(
        self,
        username: str,
        since: datetime,
        until: datetime | None = None,
        include_private: bool = False
    ) -> list[PullRequestInfo]:
        """Collect all PRs for user in date range across all organizations."""
```

**Design Decisions**:

- Use dataclass for PR data to enable future serialization
- Return domain models rather than GitHub API objects
- Implement date filtering at collection level
- Use list comprehension with pagination for memory efficiency

### 3. Settings Configuration

**Location**: `gitbrag/conf/github.py`

**Responsibilities**:

- Define GitHub-related settings
- Handle authentication configuration
- Validate required settings based on auth type

**Key Classes**:

```python
class GitHubSettings(BaseSettings):
    """GitHub API configuration."""

    # Authentication
    github_auth_type: GitHubAuthType = GitHubAuthType.PAT
    github_token: SecretStr | None = Field(
        default=None,
        description="GitHub Personal Access Token"
    )

    # GitHub App OAuth authentication
    github_app_client_id: str | None = Field(
        default=None,
        description="GitHub App client ID for OAuth"
    )
    github_app_client_secret: SecretStr | None = Field(
        default=None,
        description="GitHub App client secret for OAuth"
    )
    github_oauth_callback_port: int = Field(
        default=8080,
        description="Local port for OAuth callback server"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @model_validator(mode="after")
    def validate_auth_config(self) -> "GitHubSettings":
        """Validate that required auth settings are present.

        PAT: Requires github_token
        GitHub App: Requires github_app_client_id and github_app_client_secret
        """
        # Validation logic
```

**Design Decisions**:

- Use Pydantic SecretStr for all sensitive data
- Environment-first configuration with CLI overrides
- Validator ensures correct settings for chosen auth type
- Allow None for optional settings with clear descriptions

### 4. CLI Interface

**Location**: `gitbrag/cli.py` (extend existing)

**Responsibilities**:

- Parse command-line arguments
- Orchestrate service calls
- Format output for terminal display
- Handle errors with user-friendly messages

**Command Structure**:

```python
@app.command(name="list")
@syncify
async def list_contributions(
    username: str = typer.Argument(
        ...,
        help="GitHub username to fetch contributions for"
    ),
    since: str = typer.Option(
        None,
        "--since",
        help="Start date (ISO format, default: 1 year ago)"
    ),
    until: str = typer.Option(
        None,
        "--until",
        help="End date (ISO format, default: today)"
    ),
    token: str = typer.Option(
        None,
        "--token",
        help="GitHub Personal Access Token (overrides env var)"
    ),
    include_private: bool = typer.Option(
        False,
        "--include-private",
        help="Include private repositories (requires repo scope)"
    ),
    show_urls: bool = typer.Option(
        False,
        "--show-urls",
        help="Display PR URLs in output"
    ),
    sort: list[str] = typer.Option(
        None,
        "--sort",
        help="Sort fields (format: field or field:asc/desc). Can be specified multiple times."
    )
) -> None:
    """List pull requests for a GitHub user across all organizations."""
```

**Design Decisions**:

- Use descriptive command name "list" (future: add "report", "export", etc.)
- ISO date format for consistency and clarity
- CLI token option for convenience, env var for security
- Rich library for enhanced terminal output with tables, colors, and progress indicators
- Progress spinner for operations taking >2 seconds

### 5. Output Formatting Service

**Location**: `gitbrag/services/formatter.py`

**Responsibilities**:

- Format PR lists for terminal display
- Create Rich tables and panels
- Apply color coding based on PR state
- Handle terminal width adjustments

**Key Functions**:

```python
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn
from rich.panel import Panel

def sort_prs(
    prs: list[PullRequestInfo],
    sort_fields: list[str] | None = None
) -> list[PullRequestInfo]:
    """Sort PRs by multiple fields with direction support.

    Args:
        prs: List of pull requests to sort
        sort_fields: List of sort specs (e.g., ["repository:asc", "created:desc"])
                     Defaults to ["created:desc"]

    Returns:
        Sorted copy of PR list
    """
    if not sort_fields:
        sort_fields = ["created:desc"]

    # Parse sort specifications
    sort_specs = []
    for spec in sort_fields:
        if ":" in spec:
            field, direction = spec.split(":", 1)
            reverse = direction.lower() == "desc"
        else:
            field = spec
            reverse = True  # Default to descending
        sort_specs.append((field, reverse))

    # Define sort keys for each field
    def get_sort_keys(pr: PullRequestInfo) -> tuple:
        keys = []
        for field, reverse in sort_specs:
            if field == "repository":
                key = pr.repository.lower()
            elif field == "state":
                # Custom order: merged, open, closed
                state_order = {"merged": 0, "open": 1, "closed": 2}
                key = state_order.get(pr.state.lower(), 3)
            elif field == "created":
                key = pr.created_at
            elif field == "merged":
                key = pr.merged_at or datetime.min
            elif field == "title":
                key = pr.title.lower()
            else:
                key = ""

            keys.append(key if not reverse else (not key if isinstance(key, bool) else -key if isinstance(key, (int, float)) else key))
        return tuple(keys)

    # Sort with all keys, handle reverse per field
    sorted_prs = sorted(prs, key=get_sort_keys)
    return sorted_prs

def format_pr_list(
    prs: list[PullRequestInfo],
    username: str,
    since: str,
    until: str,
    show_urls: bool = False,
    sort_fields: list[str] | None = None
) -> None:
    """Display PR list with Rich formatting."""
    console = Console()

    if not prs:
        panel = Panel(
            f"No pull requests found for [bold]{username}[/bold]\n"
            f"Date range: {since} to {until}",
            title="Results",
            border_style="yellow"
        )
        console.print(panel)
        return

    # Sort PRs before display
    sorted_prs = sort_prs(prs, sort_fields)

    # Create table with conditional URL column
    table = Table(title=f"Pull Requests for {username}")
    table.add_column("PR #", style="cyan")
    table.add_column("State", style="bold")
    table.add_column("Repository")
    table.add_column("Title")
    table.add_column("Date")
    if show_urls:
        table.add_column("URL", style="blue underline")

    for pr in sorted_prs:
        state_style = {
            "merged": "green",
            "open": "blue",
            "closed": "yellow"
        }.get(pr.state.lower(), "white")

        row = [
            f"#{pr.number}",
            f"[{state_style}]{pr.state.upper()}[/{state_style}]",
            pr.repository,
            pr.title,
            pr.created_at.strftime("%Y-%m-%d")
        ]

        if show_urls:
            row.append(pr.url)

        table.add_row(*row)

    console.print(table)
    console.print(f"\n[bold]Total:[/bold] {len(sorted_prs)} pull requests")

def show_progress(message: str) -> Progress:
    """Create progress spinner for long operations."""
    return Progress(
        SpinnerColumn(),
        *Progress.get_default_columns(),
        console=Console()
    )
```

**Design Decisions**:

- Separate formatting logic from CLI command for testability
- Use Rich Console for all output (consistent styling)
- Color codes match common terminal conventions (green=merged, blue=open, yellow=closed)
- Tables auto-adjust to terminal width
- Progress indicators for user feedback during API calls

## Data Flow

### Pull Request Collection Flow

1. **User invokes CLI**: `gitbrag list username --since 2024-01-01 --sort repository:asc --sort merged:desc`
2. **CLI validates inputs**: Parse dates, validate username format, validate sort fields
3. **Settings loaded**: Pydantic loads env vars + CLI overrides
4. **Auth service creates client**: Based on configured auth type
5. **PR collector queries API**: Search for user PRs in date range
6. **Results transformed**: GitHub API objects → PullRequestInfo models
7. **Formatter sorts results**: Apply multi-field sorting with directions
8. **CLI formats output**: Display in readable table format with sorted data
9. **User sees results**: Terminal output with PR list sorted as requested

### Authentication Flow - PAT

1. User sets `GITHUB_TOKEN` environment variable
2. GitHubSettings loads token as SecretStr
3. GitHubClient creates Github instance with token
4. All API calls use authenticated client

### Authentication Flow - GitHub App OAuth

1. User sets `GITHUB_APP_CLIENT_ID` and `GITHUB_APP_CLIENT_SECRET` environment variables
2. GitHubSettings validates all required fields present
3. GitHubClient checks for cached user access token
4. **If no cached token or expired**:
   a. Start local callback server on `localhost:8080`
   b. Generate OAuth authorization URL with state parameter
   c. Open user's browser to GitHub authorization page
   d. User reviews permissions and authorizes app
   e. GitHub redirects to callback server with authorization code
   f. Exchange authorization code for user access token
   g. Store token securely (keyring or encrypted file)
   h. Stop callback server
5. **If cached token exists**:
   a. Validate token is still valid
   b. Use cached token
6. GitHubClient creates Github instance with user access token
7. All API calls use user access token (acting as the user)
8. User's private repositories and data are accessible

## Error Handling Strategy

### Authentication Errors

- **Missing credentials**: Clear message about which env vars to set
- **Invalid token**: Distinguish between malformed and expired tokens
- **Rate limit exceeded**: Show reset time and current usage

### API Errors

- **User not found**: Verify username is correct
- **Network errors**: Suggest checking connectivity, retry
- **API changes**: Log detailed error for debugging

### Input Validation Errors

- **Invalid date format**: Show expected format with example
- **Invalid date range**: since must be before until
- **Empty username**: Require non-empty username

### Implementation Pattern

```python
try:
    client = await github_client.get_authenticated_client()
except GithubAuthenticationError as e:
    logger.error("Authentication failed", exc_info=e)
    typer.echo(f"Error: {user_friendly_message}", err=True)
    raise typer.Exit(code=1)
```

## Testing Strategy

### Unit Tests

- **Auth service**: Mock PyGithub client, test factory logic
- **PR collector**: Mock GitHub API responses, test filtering
- **Settings**: Test validation logic for each auth type
- **CLI**: Test argument parsing and error messages

### Integration Tests

- **GitHub API**: Use real API with test token (rate limit aware)
- **End-to-end**: Full flow from CLI to output
- **Error scenarios**: Test all error paths

### Test Fixtures

```python
@pytest.fixture
def mock_github_client():
    """Mock authenticated GitHub client."""

@pytest.fixture
def sample_pull_requests():
    """Sample PR data for testing."""

@pytest.fixture
def github_settings_pat():
    """Settings configured for PAT auth."""
```

## Performance Considerations

### API Rate Limits

- Default to 1 year of history (balance usefulness vs API calls)
- PyGithub handles pagination automatically
- Consider implementing progress indicator for large result sets

### Response Time

- Typical query: 1-5 seconds depending on result count
- Rate limit check: ~100ms
- Large result sets (>100 PRs): 5-30 seconds
- Progress spinner shown for operations >2 seconds

### Future Optimizations

- Implement caching service for repeated queries
- Incremental updates (only fetch new PRs since last query)
- Parallel API calls for multiple users (future multi-user feature)

### Terminal Performance

- Rich library handles terminal width detection automatically
- Tables render efficiently even with large datasets
- Color output degrades gracefully in non-color terminals

## Security Considerations

### Credential Storage

- Never log tokens or private keys
- Use SecretStr to prevent accidental exposure
- .env file in .gitignore
- Document secure credential management in user guide

### Token Permissions

- Document minimum required scopes
- PAT: `read:user`, `public_repo` (or `repo` for private repos)
- Validate token has required scopes on first use

### GitHub App Setup

- Document app permission requirements
- Store private key securely (environment variable, not file)
- Rotate credentials regularly (document in ops guide)

## Migration and Deployment

### First Release (v0.1.0)

1. Add PyGithub to dependencies
2. Implement core services
3. Add CLI command
4. Update documentation
5. Release to PyPI

### Configuration Migration

- New required env vars documented in .env.example
- README updated with authentication setup guide
- Developer docs include GitHub App setup instructions

## Monitoring and Observability

### Logging

- Log all GitHub API calls with timing
- Log authentication attempts (success/failure)
- Log rate limit warnings (>80% consumed)

### Metrics (Future)

- API call count
- Average response time
- Error rate by type
- Authentication method usage

## Open Technical Questions

None - design is complete and ready for implementation.

## Appendix

### PyGithub API Examples

```python
# PAT Authentication
from github import Github

g = Github("ghp_xxxxxxxxxxxx")

# Search for user PRs
query = "type:pr author:username created:>=2024-01-01"
results = g.search_issues(query)

# GitHub App Authentication
from github import GithubIntegration

integration = GithubIntegration(app_id, private_key)
installation = integration.get_installation(installation_id)
g = installation.get_github_for_installation()
```

### Example Output Format

**Default output (without --show-urls):**

```text
                              Pull Requests for octocat
┏━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ PR #  ┃ State  ┃ Repository          ┃ Title                ┃ Date       ┃
┡━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ #42   │ MERGED │ octocat/Hello-World │ Add feature X        │ 2024-11-15 │
│ #123  │ OPEN   │ example/demo-repo   │ Fix bug in parser    │ 2024-10-03 │
│ #87   │ MERGED │ octocat/Spoon-Knife │ Update documentation │ 2024-09-20 │
└───────┴────────┴─────────────────────┴──────────────────────┴────────────┘

Total: 3 pull requests
```

**With --show-urls flag:**

```text
                                        Pull Requests for octocat
┏━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PR #  ┃ State  ┃ Repository          ┃ Title                ┃ Date       ┃ URL                                      ┃
┡━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ #42   │ MERGED │ octocat/Hello-World │ Add feature X        │ 2024-11-15 │ https://github.com/octocat/Hello-World/… │
│ #123  │ OPEN   │ example/demo-repo   │ Fix bug in parser    │ 2024-10-03 │ https://github.com/example/demo-repo/p… │
│ #87   │ MERGED │ octocat/Spoon-Knife │ Update documentation │ 2024-09-20 │ https://github.com/octocat/Spoon-Knife/… │
└───────┴────────┴─────────────────────┴──────────────────────┴────────────┴──────────────────────────────────────────┘

Total: 3 pull requests
```

**Notes:**

- PR numbers always displayed for easy reference
- MERGED state shown in green
- OPEN state shown in blue
- CLOSED state shown in yellow
- URLs hidden by default for cleaner, more scannable output
- Progress spinner shown during API calls
- Empty results displayed in a styled panel

```
