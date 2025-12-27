# Add Star Increase Column

## Summary

Add an optional column to the pull request report that displays the increase in GitHub repository stars from the start to the end of the filtered time period. This feature uses GitHub's GraphQL API to fetch stargazer timestamps and calculate the actual star growth during the contribution period, providing users with valuable context about the growth and popularity of projects they've contributed to.

## Motivation

When showcasing contributions for performance reviews, portfolios, or personal branding, demonstrating the growth of projects you've contributed to provides valuable context. A project that gained significant stars during your contribution period can be a strong indicator of your work's impact and the project's increasing adoption.

## Change Type

- **Type**: Enhancement
- **Scope**: CLI output formatting, GitHub API integration
- **Breaking**: No

## Requirements

### Must Have

- Display star increase (delta) for each repository in the PR report
- Optional column that is hidden by default (similar to URL display)
- CLI flag to enable star increase display (e.g., `--show-star-increase`)
- Handle cases where star data is unavailable gracefully
- Fetch repository star counts efficiently to minimize API calls

### Should Have

- Cache repository star data to avoid redundant API calls
- Clear indication when star data is unavailable (e.g., "-" or "N/A")
- Display format that clearly shows this is an increase (e.g., "+123" or "123")
- Sort capability by star increase

### Could Have

- Color coding for star increases (e.g., green for positive growth)
- Historical star count at the start and end of period (not just delta)

### Won't Have

- Star data for time periods before the repository was created
- Star prediction or forecasting
- Star breakdown by contributor

## Implementation Notes

The implementation will need to:

1. Add a `--show-star-increase` parameter to the CLI list command
2. Implement GraphQL client to query GitHub's GraphQL API
3. Fetch stargazer data with `starredAt` timestamps using paginated GraphQL queries
4. Filter stargazers to count only those within the time period (since/until dates)
5. Calculate the star increase (delta) for each unique repository
6. Add conditional column rendering in the formatter to display "+123" style increases
7. Handle API rate limiting and errors gracefully (GraphQL has separate rate limits)
8. Implement caching to minimize redundant queries for repeated requests
9. Handle repositories with large star counts efficiently (pagination, early termination)

## Alternatives Considered

1. **Always show star data**: Rejected because it adds visual clutter for users who don't need it
2. **Show current stars only**: Rejected because it doesn't meet the requirement - users want to see growth during their contribution period
3. **Show percentage increase**: Rejected because absolute numbers are clearer and percentage can be misleading for small/large repositories
4. **REST API with timestamp headers**: The REST `/repos/{owner}/{repo}/stargazers` endpoint lacks timestamp data, so GraphQL is required
5. **Fetch all stargazers every time**: Implement smart pagination with early termination when we've gone past the date range to minimize API calls

## Dependencies

- Existing GitHub API client infrastructure (will need GraphQL support added)
- Current CLI command and formatter architecture
- Rich table display system
- Existing `httpx` async HTTP client (already in use for REST API)
- Existing caching infrastructure (aiocache)

## Open Questions

1. Should we fetch star data using the GitHub REST API `/repos/{owner}/{repo}` endpoint?
   - **Answer**: Yes for current star counts (simple, one call per repo)
2. How should we handle repositories that were created during the time period (no "start" star count)?
   - **Answer**: Display current stars; historical delta would require GraphQL API with `starredAt` timestamps
3. Should the star increase be sortable (adds complexity)?
   - **Answer**: Yes, moved to "Should Have" - sort by current star count
4. What should happen if we can't fetch star data for some repositories (permissions, deleted repos)?
   - **Answer**: Display "-" or "N/A", log warning, continue with other repos

## Technical Notes

**GraphQL Implementation**: This feature requires GitHub's GraphQL API to fetch historical star data with timestamps. Example query:

```graphql
{
  repository(owner: "owner", name: "repo") {
    stargazers(first: 100, after: "cursor") {
      pageInfo { endCursor hasNextPage }
      edges { starredAt }
    }
  }
}
```

**Performance Optimization**:

- Pagination: Fetch 100 stargazers per query
- Early termination: Stop fetching when `starredAt` is before the `since` date (stars are returned in chronological order)
- Caching: Cache star increase per repository and date range to avoid redundant calculations
- Rate limiting: GraphQL has separate rate limits from REST API (typically 5000 points/hour)

**Rate Limit Considerations**: A repository with 10k stars added during a year might require 100 queries if all are within range, but with smart early termination based on date, most queries will be much cheaper. The REST API `/repos/{owner}/{repo}/stargazers` endpoint does not include timestamps, making GraphQL the only viable option.

## Related Specs

- `contribution-report-cli`: Will be modified to add star increase display option
- `github-authentication`: May need to verify sufficient permissions for repo API access
