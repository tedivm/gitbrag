# Enrich Contribution Reports

## Summary

Enhance the contribution report display in both the web interface and CLI to highlight developer's role and technical impact by adding code change statistics (additions, deletions, changed files), contributor relationship indicators at the repository level, and language contribution analysis based on file extensions. This makes developers look more impressive by showcasing their technical contributions and expertise areas beyond basic PR counts.

## Motivation

Currently, GitBrag reports display only basic PR information (title, number, status, creation date). The GitHub API provides much richer data that can better demonstrate a developer's:

1. **Technical Impact**: Lines of code changed (additions/deletions) and files changed demonstrate the scope and scale of contributions
2. **Contributor Role**: Author association (OWNER, MEMBER, CONTRIBUTOR) shows the developer's relationship and trust level with projects at the repository level
3. **Language Expertise**: File extensions from changed files reveal the programming languages and technologies the developer works with

This enrichment makes reports more compelling for performance reviews, portfolio building, and demonstrating both breadth and depth of technical contributions.

## Goals

- Show code change statistics as aggregate metrics (total additions, deletions, changed files) in summary sections
- Display PR size categorization ("One Liner", "Small", "Medium", etc.) per PR in web reports and CLI output
- Display contributor relationship (OWNER, MEMBER, etc.) at repository level in both interfaces
- Analyze file extensions to determine primary programming languages contributed to
- Enhance summary statistics with total lines changed and language breakdown
- Fetch file lists efficiently with caching to get code change and language data
- Display language expertise prominently in web summary card and CLI output
- Maintain consistent data enrichment across web and CLI interfaces

## Non-Goals

- Displaying full PR descriptions (too verbose for table format)
- Showing engagement metrics (comments, reactions) - focus is on technical contributions
- Indicating draft status - not relevant for showcasing completed work
- Displaying branch information or merge commit details
- Adding filtering/sorting UI controls (can be added later)
- Fetching individual file contents or diffs (language detection via extensions only)

## Impact

### User Experience

- **Web Interface Users**: More impressive reports that showcase technical scope and language expertise with visual formatting
- **CLI Users**: Enhanced terminal output with code statistics and language breakdown in tabular format
- **Developers**: Consistent enriched data across both web and CLI interfaces for flexible report generation
- **Reviewers**: Better context for evaluating contribution scale and technical breadth regardless of viewing method
- **Performance**: Moderate impact - requires fetching file lists for each PR, but with intelligent caching shared across interfaces

### Technical

- Extend `PullRequestInfo` model with code change fields (additions, deletions, changed_files)
- Fetch PR file lists via `/repos/{owner}/{repo}/pulls/{number}/files` API with 6-hour TTL caching
- Calculate aggregate code statistics (additions, deletions, changed_files) from per-file data
- Implement file extension mapping dictionary for language detection (no external dependencies)
- Add repository-level author_association tracking from most recent PR
- Calculate language contribution percentages from file extensions across all PRs
- Implement PR size categorization function based on total lines changed (additions + deletions)
- Update web report template with "Size" column showing PR size category
- Update CLI output to display PR size categories in PR table and aggregate statistics in summary
- Modify web summary card to include total lines changed and top 3-5 languages with percentages
- Enhance CLI summary output with aggregate code statistics and language breakdown

### Compatibility

- Non-breaking: All new fields are optional with sensible defaults
- Existing reports will continue to work (new fields show as N/A)
- Cache invalidation: Cached reports will regenerate with new data on next refresh

## Technical Decisions

1. **API Efficiency and Caching Strategy**: Uses a two-tier caching approach. Intermediate data (PR file lists from GitHub API) are cached with a 6-hour TTL (configurable) to enable efficient generation when users request overlapping time periods (1 year, then 2 years, then all time). Final report data with all computed metrics (aggregated code statistics, language percentages) is cached permanently to allow public viewing without authentication. Batch fetching with rate limit awareness prevents 403 errors.

2. **Language Detection**: Fetches file lists for each PR via `/repos/{owner}/{repo}/pulls/{number}/files` API (cached with 6-hour TTL). Uses file extension mapping (e.g., .py → Python, .js → JavaScript) with a comprehensive extension-to-language dictionary. This is fast, simple, and covers 95% of cases without requiring external dependencies like Linguist.

3. **Repository-Level Role**: Uses the author_association from the most recent PR in the report period for that repository. This is readily available from search API data and accurately reflects current relationship.

## Open Questions

1. **Display Density**: How much code metrics can we show without cluttering the interface?
   - **Decision**: Focus on aggregate statistics in summary (total additions/deletions/files). Add concise "Size" column to PR tables categorizing each PR ("One Liner", "Small", "Medium", "Large", "Huge", "Massive") based on total lines changed (additions + deletions). Size categories: One Liner (1 line), Small (2-100), Medium (101-500), Large (501-1500), Huge (1501-5000), Massive (5000+). Show language breakdown in summary as top 3-5 languages with percentages.

## Alternatives Considered

### Alternative 1: Use Search API Only (No Full PR Details)

**Rejected**: Search API doesn't provide code change statistics (additions, deletions, changed_files) which are critical for showing technical impact. The value of these metrics justifies the additional API calls.

### Alternative 2: Use GitHub's Linguist for Language Detection

**Deferred**: GitHub uses Linguist for repository language detection, but it's complex to integrate. Start with simple extension mapping. Can enhance with Linguist integration later if needed for more accuracy.

### Alternative 3: Show Per-PR Languages

**Deferred**: Could analyze and display languages for each individual PR in the table, but this adds complexity and clutter. Focus on aggregate language contributions across all PRs in the summary card.

## Dependencies

- Existing `github-pull-request-collection` spec (extends PR collection)
- Existing `web-user-interface` spec (extends report display)
- No new external dependencies required

## Success Criteria

- [x] Web reports display PR size categories ("One Liner", "Small", "Medium", "Large", "Huge", "Massive") for each PR
- [x] CLI output displays PR size categories in PR table
- [x] Web summary card shows total lines added, deleted, and changed files count
- [x] CLI summary shows aggregate code statistics
- [x] Web reports show contributor role at repository level (OWNER, MEMBER, CONTRIBUTOR)
- [x] CLI output shows contributor role badges in repository sections
- [x] Web summary card displays language breakdown with percentages (top 10 languages with bar graphs)
- [x] CLI summary displays language breakdown with percentages (top 5 languages)
- [x] Language detection works for common file extensions (.py, .js, .go, .java, .rb, etc.)
- [x] File lists are fetched efficiently with caching to minimize rate limit impact
- [x] Visual presentation is clean and professional in both web and CLI (not cluttered)
- [x] Existing reports continue to work with new optional fields in both interfaces
