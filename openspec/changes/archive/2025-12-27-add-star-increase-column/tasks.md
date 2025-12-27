# Implementation Tasks

## Overview

This document outlines the ordered tasks required to implement the star count display feature. Tasks should be completed sequentially, with each task verified before moving to the next.

## Tasks

### 1. Add GraphQL Query Support to GitHub Client

- [ ] Add `execute_graphql()` async method to `GitHubClient` in `gitbrag/services/github/client.py`
  - Accept GraphQL query string and variables dict
  - POST to `https://api.github.com/graphql` using existing httpx client
  - Use existing GitHub token in Authorization header
  - Parse JSON response and extract data/errors
  - Handle HTTP errors and GraphQL errors appropriately
- [ ] Write unit tests in `tests/services/github/test_client.py`
  - Test successful GraphQL query execution
  - Test authentication (reuses existing token)
  - Test error handling (network, rate limits, invalid queries, GraphQL errors)
  - Mock httpx POST responses appropriately

**Validation**: Tests pass, GraphQL queries can be executed via httpx

### 2. Implement Stargazer Fetching with Pagination

- [ ] Create `gitbrag/services/github/stargazers.py` module
- [ ] Implement `fetch_repository_star_increase()` async function
  - Accept `client: GitHubClient`, `owner`, `repo`, `since`, `until`, `wait_for_rate_limit: bool = True`
  - Build GraphQL query for stargazers with `starredAt` timestamps and DESC ordering
  - Implement pagination loop: check `hasNextPage`, use `endCursor` for next page
  - Fetch 100 stargazers per request (maximum allowed)
  - Count stars where `starredAt` is between `since` and `until`
  - Implement early termination: stop when `starredAt` < `since` date
  - Handle rate limiting: parse `X-RateLimit-Reset` header, optionally wait or raise exception
  - Return integer count (star increase during period) or None on error
- [ ] Write unit tests in `tests/services/github/test_stargazers.py`
  - Test with mock GraphQL pagination responses
  - Test early termination logic
  - Test date filtering and counting
  - Test rate limit handling (both wait and no-wait modes)
  - Test handling of repositories with no stargazers
  - Test error handling (repository not found, permissions, etc.)

**Validation**: Tests pass, function correctly fetches, filters, and counts stargazers

### 3. Implement Batch Star Increase Collection

- [ ] Add `collect_repository_star_increases()` async function to `stargazers.py`
  - Accept `client`, list of repository full names, `since`, `until`, `wait_for_rate_limit: bool`
  - Extract unique repositories from list (deduplicate)
  - Use `asyncio.gather()` to fetch star increases concurrently for all repositories
  - Return dictionary mapping repository name to star increase (or None if unavailable)
  - Handle errors per repository without failing entire operation
  - Log warnings for repositories where data cannot be fetched
- [ ] Add unit tests to `tests/services/github/test_stargazers.py`
  - Test with multiple repositories
  - Test deduplication of repository names
  - Test concurrent fetching (verify asyncio.gather() usage)
  - Test with various date ranges
  - Test with repositories that have zero increase
  - Test error handling for some repositories failing while others succeed

**Validation**: Tests pass, star increases fetched concurrently and accurately

### 4. Add Caching for Star Increase Results

- [ ] Add cache configuration for star increases in `gitbrag/conf/cache.py`
  - Cache key format: `repo:{owner}/{repo}:star_increase:{since}:{until}`
  - TTL: 86400 seconds (24 hours - historical data doesn't change)
  - Use existing `aiocache` setup
- [ ] Update `collect_repository_star_increases()` to use caching
  - Check cache before GraphQL queries
  - Store results in cache after successful calculation
  - Log cache hits/misses for debugging
- [ ] Write tests for caching behavior
  - Test cache hit (no GraphQL queries)
  - Test cache miss (queries executed)
  - Test cache expiration (TTL respected)
  - Test cache key includes date range correctly

**Validation**: Tests pass, cache reduces GraphQL queries for repeated calculations

### 5. Integrate Star Increase Collection into PR Collection Flow

- [ ] Modify `PullRequestCollector.collect_user_prs()` in `gitbrag/services/github/pullrequests.py`
  - Add optional `include_star_increase: bool = False` parameter
  - Add `since` and `until` parameters if not already available
  - If enabled, extract unique repository names from PR list
  - Call star increase collection method after PR collection
  - Return both PR list and star increase dictionary
- [ ] Update return type to tuple: `(list[PullRequestInfo], dict[str, int | None] | None)`
- [ ] Update tests in `tests/services/github/test_pullrequests.py`
  - Test with star increase enabled and disabled
  - Test that star increase collection happens after PR collection
  - Mock star increase collection method appropriately

**Validation**: Tests pass, PR collector can optionally fetch star increase data

### 6. Add CLI Flag for Star Increase Display

- [ ] Add `--show-star-increase` flag to `list_contributions()` command in `gitbrag/cli.py`
  - Boolean option, default `False`
  - Help text: "Display star increase (stars gained during time period) for repositories"
- [ ] Pass flag value to `PullRequestCollector.collect_user_prs()`
- [ ] Pass star increase data to `format_pr_list()` formatter
- [ ] Update CLI tests in `tests/test_cli.py`
  - Test command with and without `--show-star-increase` flag
  - Verify flag is passed correctly to collector
  - Verify star increase data is passed to formatter

**Validation**: Tests pass, CLI accepts and processes --show-star-increase flag

### 7. Update Formatter to Display Star Increase

- [ ] Modify `format_pr_list()` in `gitbrag/services/formatter.py`
  - Add optional `star_increase_data: dict[str, int | None] | None = None` parameter
  - Conditionally add "Star Increase" column when star_increase_data is provided
  - Position column after "Repository" column
  - Display star increase with "+" prefix for positive values (e.g., "+123")
  - Display "0" or "+0" for zero increase
  - Display "-" for missing/unavailable star increase data
  - Ensure star data aligns correctly with repository names
- [ ] Update tests in `tests/services/test_formatter.py`
  - Test formatter with star increase enabled (data provided)
  - Test formatter with star increase disabled (no data)
  - Test formatter with mixed availability (some repos have data, some don't)
  - Test column positioning and formatting
  - Test "+" prefix display
  - Verify existing behavior unchanged when star increase not enabled

**Validation**: Tests pass, formatter correctly displays star increase column when data provided

### 8. Add Star Increase Sorting Support

- [ ] Update `_parse_sort_fields()` in `gitbrag/cli.py`
  - Add "stars" as valid sort field
  - Add validation: "stars" requires `--show-star-increase` flag
  - Provide clear error message if stars sort used without flag
- [ ] Update `_sort_pull_requests()` in `gitbrag/services/formatter.py`
  - Add sort key function for "stars" field
  - Look up star increase from star_increase_data dictionary by repository name
  - Handle missing star increase data (treat as 0 or sort to end)
- [ ] Update sort validation and documentation
  - Update help text to mention "stars" field
  - Add note about --show-star-increase requirement
- [ ] Write tests for star increase sorting
  - Test sort by stars ascending
  - Test sort by stars descending
  - Test sort with missing star increase data
  - Test multi-field sort including stars
  - Test error when sorting by stars without --show-star-increase flag

**Validation**: Tests pass, sorting by star increase works correctly

### 9. Update Documentation

- [ ] Update `docs/dev/cli.md`
  - Document `--show-star-increase` flag
  - Provide usage examples with date ranges
  - Explain GraphQL API usage and rate limiting
  - Note performance considerations for popular repositories
- [ ] Update `docs/dev/github-api.md`
  - Document GraphQL endpoint usage via httpx
  - Explain stargazer queries with `starredAt` field
  - Detail early termination optimization with DESC ordering
  - Explain star increase calculation and caching
  - Note GraphQL rate limit considerations (separate from REST API)
  - Provide example GraphQL query and httpx POST request
  - Document rate limit handling strategy (automatic wait vs exit)
- [ ] Update `README.md` if appropriate
  - Add example with --show-star-increase flag
  - Mention star increase feature and its value
  - Note that GraphQL support is included

**Validation**: Documentation is clear, accurate, and includes GraphQL details

### 10. Integration Testing

- [ ] Run full test suite: `make test`
  - All existing tests still pass
  - New tests pass
  - Coverage maintained or improved
- [ ] Manual testing with real GitHub token
  - Test with various users and repositories
  - Test with different date ranges
  - Test with deleted/private repositories
  - Test with repositories that have many stars
  - Test early termination optimization (check logs)
  - Test caching behavior across multiple runs
  - Test error handling for GraphQL rate limits
  - Test combined with other flags (--show-urls, --include-private, --sort)
- [ ] Verify performance
  - Measure GraphQL query count
  - Confirm early termination reduces queries
  - Confirm caching reduces repeated queries
  - Test with popular repositories (high star counts)

**Validation**: All tests pass, feature works correctly with real GitHub data, performance is acceptable

### 10. Final Validation and Cleanup

- [ ] Run `make lint` and fix any issues
- [ ] Run `make format` to ensure consistent formatting
- [ ] Run `mypy` type checking and resolve any errors
- [ ] Review code for:
  - Proper error handling
  - Appropriate logging
  - Type hints on all functions
  - Docstrings with parameter descriptions
  - Security considerations (no token leakage)
- [ ] Verify all tasks marked complete
- [ ] Update proposal status

**Validation**: Code passes all quality checks, ready for review

## Dependencies

- **Task 2** depends on **Task 1** (needs client method)
- **Task 3** depends on **Task 2** (adds caching to collection)
- **Task 4** depends on **Task 3** (integrates into PR flow)
- **Task 5** and **Task 6** can be done in parallel after **Task 4**
- **Task 7** depends on **Task 6** (needs formatter with star support)
- **Task 8** can be done anytime after **Task 7**
- **Task 9** depends on all previous tasks
- **Task 10** depends on **Task 9**

## Estimated Effort

- Task 1: Add GraphQL support to client (~1-2 hours)
- Tasks 2-3: Stargazer fetching and batch collection (~4-6 hours)
- Task 4: Caching implementation (~2 hours)
- Task 5: Integration into PR flow (~2 hours)
- Tasks 6-7: CLI and display (~3-4 hours)
- Task 8: Sorting support (~2-3 hours)
- Task 9: Documentation (~2 hours)
- Tasks 10-11: Testing and validation (~3-4 hours)

**Total estimated effort**: 18-23 hours

Note: Using httpx directly (already a dependency) is simpler than adding a GraphQL library, while still delivering the accurate star increase feature as requested.

## Success Criteria

- [ ] All unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing successful with real GitHub API
- [ ] Code quality checks pass (lint, format, type checking)
- [ ] Documentation complete and accurate
- [ ] Feature works as specified in requirements
- [ ] No regression in existing functionality
- [ ] Performance is acceptable (minimal API calls, proper caching)
