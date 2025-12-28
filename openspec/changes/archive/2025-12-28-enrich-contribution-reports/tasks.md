# Implementation Tasks

## Phase 1: Data Model Extensions

- [x] Extend `PullRequestInfo` dataclass in `gitbrag/services/github/models.py`:
  - [x] Add `additions: int | None = None` - Number of lines added
  - [x] Add `deletions: int | None = None` - Number of lines deleted
  - [x] Add `changed_files: int | None = None` - Number of files changed
  - [x] Add `author_association: str | None = None` - Contributor relationship (OWNER, MEMBER, CONTRIBUTOR, etc.)

## Phase 2: PR File List Fetching and Aggregation

- [x] Create helper function in `gitbrag/services/github/pullrequests.py`:
  - [x] Implement `fetch_pr_files(owner, repo, number)` to get file list
  - [x] Extract file names and per-file metrics (additions, deletions) from files API response
  - [x] Calculate aggregate `additions` by summing file additions
  - [x] Calculate aggregate `deletions` by summing file deletions
  - [x] Calculate `changed_files` by counting files
  - [x] Handle API errors gracefully (return empty list and None for aggregates)
  - [x] Add caching layer for file lists with 6-hour TTL (configurable, intermediate cache)
  - [x] Note: Final computed metrics stored permanently as part of report data

- [x] Update `PullRequestCollector.collect_user_prs()`:
  - [x] Extract `author_association` from search API response (item\["author_association"\])
  - [x] After collecting PRs from search API, fetch file lists for each PR
  - [x] Calculate aggregate additions, deletions, and changed_files from file data
  - [x] Use semaphore to limit concurrent API calls (max 10 parallel)
  - [x] Respect rate limits with wait_for_rate_limit parameter
  - [x] Map file lists and calculated aggregates to `PullRequestInfo` fields
  - [x] Handle missing/null values gracefully with None defaults

## Phase 3: Language Detection Utility

- [x] Create `gitbrag/services/language_analyzer.py`:
  - [x] Create comprehensive extension-to-language mapping dictionary
  - [x] Include common extensions: .py, .js, .ts, .go, .java, .rb, .php, .c, .cpp, .rs, .swift, etc.
  - [x] Implement `detect_language_from_extension(filename)` function
  - [x] Implement `calculate_language_percentages(pr_list)` function that:
    - [x] Accepts list of PRs with file lists
    - [x] Extracts extensions from all file names across all PRs
    - [x] Maps extensions to languages using the dictionary
    - [x] Calculates percentage contribution for each language
    - [x] Returns top N languages with percentages
  - [x] Handle edge cases (no extension, unknown extensions, hidden files)

## Phase 4: PR Size Categorization Utility

- [x] Create `gitbrag/services/pr_size.py`:
  - [x] Implement `categorize_pr_size(additions, deletions)` function
  - [x] Define size categories with thresholds:
    - [x] "One Liner": 1 line
    - [x] "Small": 2-100 lines
    - [x] "Medium": 101-500 lines
    - [x] "Large": 501-1500 lines
    - [x] "Huge": 1501-5000 lines
    - [x] "Massive": 5000+ lines
  - [x] Handle None values gracefully (return None or "-")
  - [x] Add size category to color mapping for consistent styling

## Phase 5: Report Data Aggregation and Permanent Storage

- [x] Update `generate_report_data()` in `gitbrag/services/reports.py`:
  - [x] Calculate `total_additions` across all PRs
  - [x] Calculate `total_deletions` across all PRs
  - [x] Calculate `total_changed_files` across all PRs
  - [x] Calculate size category for each PR using PR size utility
  - [x] Call language analyzer to get language breakdown
  - [x] Determine repository-level author_association (from most recent PR per repo)
  - [x] Add new metrics to returned report data dictionary
  - [x] Ensure all computed metrics stored permanently with report (never expire)
  - [x] Ensure backward compatibility with existing cached reports

## Phase 6: Template Updates - Summary Card

- [x] Update `gitbrag/templates/components/summary_card.html`:
  - [x] Add stat item for total additions (with green styling, +5,234)
  - [x] Add stat item for total deletions (with red styling, -1,876)
  - [x] Add stat item for files changed (342 files)
  - [x] Add language breakdown display (Python 45% • JavaScript 30% • Go 15%)
  - [x] Maintain responsive grid layout (wrap to multiple rows on mobile)
  - [x] Style code metrics distinctly from PR counts

## Phase 7: Template Updates - Repository Headers

- [x] Update `gitbrag/templates/user_report.html` repository sections:
  - [x] Add repository-level role badge in repo header
  - [x] Display role next to repository name (OWNER, MEMBER, CONTRIBUTOR)
  - [x] Use color-coded badges matching role (purple, blue, green)
  - [x] Handle missing role data gracefully (hide badge or show neutral)

## Phase 8: Template Updates - PR Table

- [x] Update `gitbrag/templates/user_report.html` PR table:
  - [x] Add "Size" column showing PR size category
  - [x] Display category badge ("One Liner", "Small", "Medium", "Large", "Huge", "Massive")
  - [x] Use color-coded badges: blue/green for smaller, orange/red for larger
  - [x] Ensure table remains readable on mobile (consider column priority)
  - [x] Handle missing code change data (show "-" or "N/A")

## Phase 9: CSS Styling

- [x] Update `gitbrag/static/css/styles.css`:
  - [x] Add styles for PR size category badges with color coding
  - [x] Add styles for aggregate code statistics in summary (green/red for additions/deletions)
  - [x] Add styles for role badges at repository level (same colors as before)
  - [x] Add styles for language breakdown in summary card
  - [x] Ensure number formatting for large values (thousands separators)
  - [x] Ensure styles work in both light and dark modes
  - [x] Add responsive styles for new columns on mobile

## Phase 10: CLI Enhancement

- [x] Update `gitbrag/cli.py` list command output:
  - [x] Add \"Size\" column to PR table using Rich library
  - [x] Display size category badges with color coding
  - [x] Add summary section with aggregate code statistics (total additions, deletions, files)
  - [x] Add language breakdown to summary (top 3-5 languages with percentages)
  - [x] Add repository-level role badges in repository sections
  - [x] Use Rich styling for size categories (cyan for One Liner, green for Small, yellow for Medium, etc.)
  - [x] Ensure consistent categorization with web interface
  - [x] Handle missing data gracefully

## Phase 11: Testing

- [x] Add unit tests for PR size categorization:
  - [x] Test size categorization function with various line counts
  - [x] Test thresholds for all categories (One Liner through Massive)
  - [x] Test handling of None values

- [x] Add unit tests for model changes:
  - [x] Test `PullRequestInfo` with new code change fields
  - [x] Test serialization/deserialization with new fields
  - [x] Test backward compatibility (old data without new fields)

- [x] Add unit tests for language detection:
  - [x] Test extension mapping for common languages
  - [x] Test percentage calculation with various distributions
  - [x] Test edge cases (no files, unknown extensions)

- [x] Add integration tests for PR collection:
  - [x] Test fetching full PR details
  - [x] Test extraction of code change fields
  - [x] Test handling of missing/null values
  - [x] Mock GitHub API responses with full PR data

- [x] Add tests for report generation:
  - [x] Test calculation of aggregate code metrics
  - [x] Test language analysis integration
  - [x] Test repository role determination
  - [x] Test report data structure with new fields

- [x] Add tests for CLI enhancements:
  - [x] Test _calculate_repo_roles function
  - [x] Test repo roles with most recent PR selection
  - [x] Test handling of None author_association

- [x] Add tests for formatter enhancements:
  - [x] Test Size column display
  - [x] Test summary statistics display
  - [x] Test repository roles display

- [x] Manual testing:
  - [x] Generate reports for various users and verify display
  - [x] Test responsive layout on mobile devices
  - [x] Test light/dark mode appearance
  - [x] Verify performance with large PR counts (100+)
  - [x] Check API rate limit handling

## Phase 12: Documentation

- [x] Update developer documentation in `docs/dev/`:
  - [x] Document new PullRequestInfo fields
  - [x] Document PR size categorization thresholds and logic
  - [x] Document language detection approach and extension mapping
  - [x] Document full PR fetching strategy and caching
  - [x] Note performance considerations and rate limit impact

- [x] Update README.md if user-facing changes warrant mention

## Phase 13: Cache Management and Configuration

- [x] Verify two-tier caching implementation:
  - [x] Confirm intermediate file list cache uses TTL (default 6 hours, configurable)
  - [x] Confirm final report data cache is permanent (no TTL)
  - [x] Test that public users can view cached reports without authentication
  - [x] Test overlapping time period generation (1yr → 2yr → all time) reuses cache
  - [x] Verify intermediate cache expires after TTL
  - [x] Verify final report cache never expires
  - [x] Document cache configuration settings

## Phase 14: Final Documentation and Review

- [x] Review all documentation for accuracy
- [x] Update user-facing documentation with new features
- [x] Create migration guide if needed for existing users
- [x] Review and update API documentation if relevant

## Optional Enhancements (Future)

- [ ] Add filtering UI by language
- [ ] Add filtering UI by PR size category
- [ ] Show per-repository language breakdown
- [ ] Add sorting options by code change magnitude
- [ ] Display commit count per PR
- [x] Add PR size distribution chart/visualization
- [ ] Show review comment counts alongside code metrics
