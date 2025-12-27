# Proposal: Add Web Interface

## Overview

This change adds a web-based user interface to GitBrag, complementing the existing CLI tool. The web interface allows users to view GitHub contribution reports through their browser by authenticating with GitHub OAuth, enabling the application to use their personal access scopes and rate limits.

## Motivation

GitBrag currently provides a CLI tool for generating contribution reports, which requires users to:

1. Install Python and the gitbrag package
2. Configure authentication via environment variables
3. Run commands from the terminal

A web interface offers several advantages:

- **Lower barrier to entry**: No installation required - users can access reports immediately
- **Shareable URLs**: Reports accessible at `/user/github/USERNAME` can be shared with others
- **Better discoverability**: Web presence increases tool visibility and adoption
- **Enhanced UX**: HTML rendering allows for richer data visualization and interactivity
- **OAuth integration**: Seamless GitHub authentication without manual token management

## Scope

### In Scope

1. **Web application routes**:
   - User report pages at `/user/github/{username}`
   - OAuth authentication flow endpoints
   - HTML-based report rendering

2. **OAuth authentication**:
   - GitHub OAuth flow for web users
   - Session management with secure cookies
   - Token storage for authenticated requests

3. **Report generation**:
   - Reuse existing PR collection and formatting logic
   - Default to 1-year time range with custom range support via query parameters
   - Repository-level breakdown below high-level summary

4. **Caching**:
   - Redis-backed caching for all environments (including development)
   - Cache GitHub API responses to minimize rate limit usage

5. **HTML templates**:
   - Jinja2 templates for report pages
   - Responsive design for mobile and desktop
   - Professional styling for sharing

### Out of Scope

- Database persistence (use Redis caching only)
- User accounts or profile management
- Report customization UI (use query parameters instead)
- PDF/export functionality
- Admin interface
- API endpoints (focus on HTML rendering)
- Support for non-GitHub platforms

## Constraints

- **No databases**: All data is ephemeral or cached in Redis
- **Public data only**: Only access public repositories and pull requests (private repositories are out of scope)
- **OAuth required**: Users must authenticate to generate reports (no anonymous access for generation)
- **Redis dependency**: Development environment must include Redis (already configured in compose.yaml)

## Success Criteria

1. Users can visit `/user/github/{username}` and authenticate with GitHub OAuth
2. Authenticated users see their contribution report in HTML format
3. Reports default to the past year but accept custom date ranges via query parameters
4. Reports include both high-level summary and repository-level breakdown
5. All API calls are properly cached to minimize GitHub rate limit usage
6. Development environment works with Redis cache from `docker compose up`

## Dependencies

- Existing GitHub authentication infrastructure (PAT and OAuth support already implemented)
- Existing PR collection service (`PullRequestCollector`)
- Existing caching configuration (Redis via aiocache)
- FastAPI application framework (already configured in `gitbrag/www.py`)
- **New**: `cryptography` library for token encryption (Fernet symmetric encryption)

## Related Changes

None - this is a new feature addition.

## Impact Assessment

- **Breaking changes**: None (additive only)
- **CLI compatibility**: No changes to CLI behavior
- **Configuration**: New settings for OAuth callback URL and session secret
- **Dependencies**: No new dependencies required (FastAPI, Jinja2, Redis already included)
- **Documentation**: Requires new user guide for web interface usage
