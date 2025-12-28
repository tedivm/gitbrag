# Implementation Tasks

## Phase 1: Data Model Extensions

- [ ] Extend `PullRequestInfo` dataclass in `gitbrag/services/github/models.py`:
  - [ ] Add `additions: int | None = None` - Number of lines added
  - [ ] Add `deletions: int | None = None` - Number of lines deleted
  - [ ] Add `changed_files: int | None = None` - Number of files changed
  - [ ] Add `author_association: str | None = None` - Contributor relationship (OWNER, MEMBER, CONTRIBUTOR, etc.)

## Phase 2: PR File List Fetching and Aggregation

- [ ] Create helper function in `gitbrag/services/github/pullrequests.py`:
  - [ ] Implement `fetch_pr_files(owner, repo, number)` to get file list
  - [ ] Extract file names and per-file metrics (additions, deletions) from files API response
  - [ ] Calculate aggregate `additions` by summing file additions
  - [ ] Calculate aggregate `deletions` by summing file deletions
  - [ ] Calculate `changed_files` by counting files
  - [ ] Handle API errors gracefully (return empty list and None for aggregates)
  - [ ] Add caching layer for file lists with 6-hour TTL (configurable, intermediate cache)
  - [ ] Note: Final computed metrics stored permanently as part of report data

- [ ] Update `PullRequestCollector.collect_user_prs()`:
  - [ ] Extract `author_association` from search API response (item\["author_association"\])
  - [ ] After collecting PRs from search API, fetch file lists for each PR
  - [ ] Calculate aggregate additions, deletions, and changed_files from file data
  - [ ] Use semaphore to limit concurrent API calls (max 10 parallel)
  - [ ] Respect rate limits with wait_for_rate_limit parameter
  - [ ] Map file lists and calculated aggregates to `PullRequestInfo` fields
  - [ ] Handle missing/null values gracefully with None defaults

## Phase 3: Language Detection Utility

- [ ] Create `gitbrag/services/language_analyzer.py`:
  - [ ] Create comprehensive extension-to-language mapping dictionary
  - [ ] Include common extensions: .py, .js, .ts, .go, .java, .rb, .php, .c, .cpp, .rs, .swift, etc.
  - [ ] Implement `detect_language_from_extension(filename)` function
  - [ ] Implement `calculate_language_percentages(pr_list)` function that:
    - [ ] Accepts list of PRs with file lists
    - [ ] Extracts extensions from all file names across all PRs
    - [ ] Maps extensions to languages using the dictionary
    - [ ] Calculates percentage contribution for each language
    - [ ] Returns top N languages with percentages
  - [ ] Handle edge cases (no extension, unknown extensions, hidden files)

## Phase 4: PR Size Categorization Utility

- [ ] Create `gitbrag/services/pr_size.py`:
  - [ ] Implement `categorize_pr_size(additions, deletions)` function
  - [ ] Define size categories with thresholds:
    - [ ] "One Liner": 1 line
    - [ ] "Small": 2-100 lines
    - [ ] "Medium": 101-500 lines
    - [ ] "Large": 501-1500 lines
    - [ ] "Huge": 1501-5000 lines
    - [ ] "Massive": 5000+ lines
  - [ ] Handle None values gracefully (return None or "-")
  - [ ] Add size category to color mapping for consistent styling

## Phase 5: Report Data Aggregation and Permanent Storage

- [ ] Update `generate_report_data()` in `gitbrag/services/reports.py`:
  - [ ] Calculate `total_additions` across all PRs
  - [ ] Calculate `total_deletions` across all PRs
  - [ ] Calculate `total_changed_files` across all PRs
  - [ ] Calculate size category for each PR using PR size utility
  - [ ] Call language analyzer to get language breakdown
  - [ ] Determine repository-level author_association (from most recent PR per repo)
  - [ ] Add new metrics to returned report data dictionary
  - [ ] Ensure all computed metrics stored permanently with report (never expire)
  - [ ] Ensure backward compatibility with existing cached reports

## Phase 6: Template Updates - Summary Card

- [ ] Update `gitbrag/templates/components/summary_card.html`:
  - [ ] Add stat item for total additions (with green styling, +5,234)
  - [ ] Add stat item for total deletions (with red styling, -1,876)
  - [ ] Add stat item for files changed (342 files)
  - [ ] Add language breakdown display (Python 45% • JavaScript 30% • Go 15%)
  - [ ] Maintain responsive grid layout (wrap to multiple rows on mobile)
  - [ ] Style code metrics distinctly from PR counts

## Phase 7: Template Updates - Repository Headers

- [ ] Update `gitbrag/templates/user_report.html` repository sections:
  - [ ] Add repository-level role badge in repo header
  - [ ] Display role next to repository name (OWNER, MEMBER, CONTRIBUTOR)
  - [ ] Use color-coded badges matching role (purple, blue, green)
  - [ ] Handle missing role data gracefully (hide badge or show neutral)

## Phase 8: Template Updates - PR Table

- [ ] Update `gitbrag/templates/user_report.html` PR table:
  - [ ] Add "Size" column showing PR size category
  - [ ] Display category badge ("One Liner", "Small", "Medium", "Large", "Huge", "Massive")
  - [ ] Use color-coded badges: blue/green for smaller, orange/red for larger
  - [ ] Ensure table remains readable on mobile (consider column priority)
  - [ ] Handle missing code change data (show "-" or "N/A")

## Phase 9: CSS Styling

- [ ] Update `gitbrag/static/css/styles.css`:
  - [ ] Add styles for PR size category badges with color coding
  - [ ] Add styles for aggregate code statistics in summary (green/red for additions/deletions)
  - [ ] Add styles for role badges at repository level (same colors as before)
  - [ ] Add styles for language breakdown in summary card
  - [ ] Ensure number formatting for large values (thousands separators)
  - [ ] Ensure styles work in both light and dark modes
  - [ ] Add responsive styles for new columns on mobile

## Phase 10: CLI Enhancement

- [ ] Update `gitbrag/cli.py` list command output:
  - [ ] Add \"Size\" column to PR table using Rich library
  - [ ] Display size category badges with color coding
  - [ ] Add summary section with aggregate code statistics (total additions, deletions, files)
  - [ ] Add language breakdown to summary (top 3-5 languages with percentages)
  - [ ] Add repository-level role badges in repository sections
  - [ ] Use Rich styling for size categories (cyan for One Liner, green for Small, yellow for Medium, etc.)
  - [ ] Ensure consistent categorization with web interface
  - [ ] Handle missing data gracefully

## Phase 11: Testing

- [ ] Add unit tests for PR size categorization:
  - [ ] Test size categorization function with various line counts
  - [ ] Test thresholds for all categories (One Liner through Massive)
  - [ ] Test handling of None values

- [ ] Add unit tests for model changes:
  - [ ] Test `PullRequestInfo` with new code change fields
  - [ ] Test serialization/deserialization with new fields
  - [ ] Test backward compatibility (old data without new fields)

- [ ] Add unit tests for language detection:
  - [ ] Test extension mapping for common languages
  - [ ] Test percentage calculation with various distributions
  - [ ] Test edge cases (no files, unknown extensions)

- [ ] Add integration tests for PR collection:
  - [ ] Test fetching full PR details
  - [ ] Test extraction of code change fields
  - [ ] Test handling of missing/null values
  - [ ] Mock GitHub API responses with full PR data

- [ ] Add tests for report generation:
  - [ ] Test calculation of aggregate code metrics
  - [ ] Test language analysis integration
  - [ ] Test repository role determination
  - [ ] Test report data structure with new fields

- [ ] Manual testing:
  - [ ] Generate reports for various users and verify display
  - [ ] Test responsive layout on mobile devices
  - [ ] Test light/dark mode appearance
  - [ ] Verify performance with large PR counts (100+)
  - [ ] Check API rate limit handling

## Phase 12: Documentation

- [ ] Update developer documentation in `docs/dev/`:
  - [ ] Document new PullRequestInfo fields
  - [ ] Document PR size categorization thresholds and logic
  - [ ] Document language detection approach and extension mapping
  - [ ] Document full PR fetching strategy and caching
  - [ ] Note performance considerations and rate limit impact

- [ ] Update README.md if user-facing changes warrant mention

## Phase 13: Cache Management and Configuration

- [ ] Verify two-tier caching implementation:
  - [ ] Confirm intermediate file list cache uses TTL (default 6 hours, configurable)
  - [ ] Confirm final report data cache is permanent (no TTL)
  - [ ] Test that public users can view cached reports without authentication
  - [ ] Test overlapping time period generation (1yr → 2yr → all time) reuses cache
  - [ ] Verify intermediate cache expires after TTL
  - [ ] Verify final report cache never expires
  - [ ] Document cache configuration settings

## Phase 14: Final Documentation and Review

- [ ] Review all documentation for accuracy
- [ ] Update user-facing documentation with new features
- [ ] Create migration guide if needed for existing users
- [ ] Review and update API documentation if relevant

## Optional Enhancements (Future)

- [ ] Add filtering UI by language
- [ ] Add filtering UI by PR size category
- [ ] Show per-repository language breakdown
- [ ] Add sorting options by code change magnitude
- [ ] Display commit count per PR
- [ ] Add PR size distribution chart/visualization
- [ ] Show review comment counts alongside code metrics
