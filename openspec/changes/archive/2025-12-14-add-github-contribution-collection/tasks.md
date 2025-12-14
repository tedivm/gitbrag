# Implementation Tasks: GitHub Contribution Collection

This document outlines the ordered implementation tasks for adding GitHub contribution collection functionality to GitBrag.

## Phase 1: Foundation & Configuration

- [x] **Add PyGithub dependency** to `pyproject.toml` (>=2.5.0)
- [x] **Create GitHub settings module** at `gitbrag/conf/github.py` with GitHubSettings class
  - Define authentication type enum
  - Add PAT authentication fields with SecretStr
  - Add GitHub App OAuth fields (client ID, client secret)
  - Add OAuth callback port configuration
  - Implement model validator for auth config
  - Update main Settings class to inherit from GitHubSettings
- [x] **Update .env.example** with GitHub authentication variables and documentation
- [x] **Create settings tests** in `tests/test_github_settings.py`
  - Test PAT configuration validation
  - Test GitHub App configuration validation
  - Test authentication type validation
  - Test environment variable loading

## Phase 2: GitHub Authentication Service

- [x] **Create GitHub service directory** at `gitbrag/services/github/`
- [x] **Implement OAuth callback server** at `gitbrag/services/github/oauth.py`
  - Create OAuthCallbackServer class for receiving OAuth callbacks
  - Implement local HTTP server on configurable port
  - Handle authorization code extraction from callback
  - Add timeout handling for user authorization
  - Implement secure state parameter validation
- [x] **Implement OAuth flow handler** at `gitbrag/services/github/oauth.py`
  - Create GitHubOAuthFlow class
  - Implement OAuth authorization URL generation
  - Implement authorization code exchange for access token
  - Add token caching (keyring or encrypted file)
  - Implement token validation and refresh
  - Handle browser launch for user authorization
- [x] **Implement authentication service** at `gitbrag/services/github/auth.py`
  - Create GitHubAuthType enum
  - Implement GitHubClient class with factory pattern
  - Add PAT authentication method
  - Add GitHub App OAuth authentication method (uses OAuth flow)
  - Implement rate limit checking
  - Add error handling for authentication failures
- [x] **Create authentication tests** in `tests/services/github/test_auth.py`
  - Test PAT client creation
  - Test GitHub App OAuth client creation
  - Test OAuth flow (mock browser and callback)
  - Test token caching and retrieval
  - Test authentication error handling
  - Test rate limit checking
  - Mock PyGithub client for testing

## Phase 3: Pull Request Collection Service

- [x] **Create PR domain model** in `gitbrag/services/github/models.py`
  - Define PullRequestInfo dataclass
  - Include all required fields (title, repo, url, state, dates, number)
  - Add type annotations
- [x] **Implement PR collector** at `gitbrag/services/github/pullrequests.py`
  - Create PullRequestCollector class
  - Implement collect_user_prs method with include_private parameter
  - Add repository visibility filtering (public by default)
  - Add date filtering logic
  - Handle pagination automatically
  - Query across all organizations and repositories
  - Transform GitHub API objects to PullRequestInfo models
  - Add error handling for API failures and permission issues
- [x] **Create PR collection tests** in `tests/services/github/test_pullrequests.py`
  - Test PR collection with date filtering
  - Test repository visibility filtering (public only vs include private)
  - Test collection across all organizations
  - Test pagination handling
  - Test data transformation
  - Test error scenarios (user not found, network errors, permission errors)
  - Mock GitHub API responses

## Phase 4: Output Formatting Service

- [x] **Create formatter service** at `gitbrag/services/formatter.py`
  - Implement format_pr_list function using Rich library
  - Create Rich table with columns for PR #, state, repository, title, date
  - Add conditional URL column based on show_urls parameter
  - Always display PR numbers for easy reference
  - Apply color coding based on PR state (green=merged, blue=open, yellow=closed)
  - Handle empty results with styled panel
  - Add summary footer with total count
  - Implement show_progress function for progress spinners
  - Handle terminal width adjustments
- [x] **Create formatter tests** in `tests/services/test_formatter.py`
  - Test table generation with sample PRs (with and without URLs)
  - Test PR number display
  - Test URL column display when enabled
  - Test URL column hidden by default
  - Test empty results formatting
  - Test color coding for different states
  - Test terminal width handling
  - Test sorting with single field (ascending and descending)
  - Test sorting with multiple fields (primary and secondary)
  - Test default sorting (created:desc)
  - Test state-based sorting order (merged, open, closed)
  - Test invalid sort field handling
  - Mock Rich Console for testing

## Phase 5: CLI Interface

- [x] **Add list command** to `gitbrag/cli.py`
  - Implement list_contributions function with syncify decorator
  - Add username argument
  - Add --since option with default (1 year ago)
  - Add --until option with default (today)
  - Add --include-private flag (default: False)
  - Add --show-urls flag (default: False)
  - Add --sort option (multiple allowed) with default (created:desc)
  - Add --token option for PAT override
  - Parse and validate date inputs (ISO format)
  - Parse and validate sort field specifications (field:direction format)
  - Validate sort fields against allowed list (repository, state, created, merged, title)
  - Validate sort directions (asc/desc)
  - Call authentication service
  - Show progress spinner during API calls
  - Call PR collection service with appropriate visibility filter
  - Call formatter service with show_urls and sort_fields parameters for output display
  - Implement comprehensive error handling including permission errors and invalid sort specifications
- [x] **Create CLI tests** in `tests/test_cli.py` (extend existing)
  - Test list command with default dates
  - Test list command with custom date range
  - Test list command with --include-private flag
  - Test list command with --show-urls flag
  - Test list command with --sort flag (single field)
  - Test list command with multiple --sort flags (multi-field sorting)
  - Test list command with explicit sort directions (:asc, :desc)
  - Test list command with invalid sort field (error handling)
  - Test list command with invalid sort direction (error handling)
  - Test list command with token override
  - Test combined flags (--show-urls --include-private)
  - Test date parsing and validation
  - Test error message formatting for permission errors
  - Test output formatting integration
  - Mock service layer for testing

## Phase 6: Integration & Testing

- [x] **Create integration test fixture** in `tests/conftest.py`
  - Add fixture for GitHub client with test credentials
  - Add fixture for sample PR data
  - Document test setup requirements
- [x] **Create integration tests** in `tests/integration/test_github_integration.py`
  - Test full flow from CLI to GitHub API (with test account)
  - Test authentication with real credentials
  - Test PR retrieval and filtering
  - Mark as optional/skipable if no credentials
- [x] **Run full test suite** and verify coverage meets standards (>80%)
- [x] **Run type checking** with mypy and fix any issues
- [x] **Run linting** with ruff and fix any issues

## Phase 7: Documentation

- [x] **Create GitHub integration docs** at `docs/dev/github-api.md`
  - Explain authentication setup
  - Document PAT creation and configuration
  - Document GitHub App setup and configuration
  - Include security best practices
  - Add troubleshooting section
- [x] **Update main README.md** with CLI usage examples
  - Add authentication setup section
  - Include list command examples
  - Show output examples
- [x] **Update developer docs index** at `docs/dev/README.md`
  - Add link to github-api.md
- [x] **Update CLI help docs** at `docs/dev/cli.md`
  - Document list command
  - Include all options and arguments
  - Add usage examples

## Phase 8: Validation & Release Prep

- [x] **Manual testing** with real GitHub accounts
  - Test PAT authentication
  - Test with various usernames
  - Test date range filtering
  - Test error scenarios
- [x] **Performance validation**
  - Test with high-contribution users (>100 PRs)
  - Verify pagination works correctly
  - Check response times
- [x] **Security review**
  - Verify tokens not logged
  - Check .env in .gitignore
  - Review credential handling

## Dependencies Between Tasks

- Phase 2 depends on Phase 1 (settings must exist)
- Phase 3 depends on Phase 2 (authentication must work)
- Phase 4 depends on Phases 2 & 3 (services must exist)
- Phase 5 depends on all previous phases
- Phase 6 can be done in parallel with Phase 5
- Phase 7 must be last

## Parallelizable Work

- Settings tests (Phase 1) can be written while implementing settings
- Documentation (Phase 6) can be written while doing integration testing (Phase 5)
- All tests can be written immediately after their corresponding implementation

## Validation Criteria

Each task should be validated before marking complete:

- Code passes mypy type checking
- Code passes ruff linting
- Tests pass and maintain >80% coverage
- Manual testing confirms expected behavior
- Documentation is clear and accurate
