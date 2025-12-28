# Technical Design

## Overview

This change enriches contribution reports by capturing and displaying code change statistics (additions, deletions, changed files) and analyzing programming languages from file extensions. Additionally, it shows the developer's contributor role at the repository level. The design uses a two-tier caching strategy: (1) intermediate API data (file lists) cached with 6-hour TTL to enable efficient generation of overlapping reports, and (2) final report data stored permanently to allow public viewing without requiring re-generation.

## Architecture

### Data Flow

```
GitHub Search API Response (basic PR data + author_association)
    ↓
Fetch PR File Lists (per PR, with 6-hour TTL cache - intermediate layer)
    ↓
PullRequestCollector (extract file names, calculate aggregate code metrics)
    ↓
PullRequestInfo (extended model with additions/deletions/changed_files/file_list)
    ↓
Language Analyzer (file extensions → language percentages)
    ↓
generate_report_data() (aggregate code metrics + languages + repo roles)
    ↓
Report Data Dictionary (PERMANENT CACHE - never expires)
    ↓
Jinja2 Templates (render enriched display)
    ↓
HTML Report (publicly viewable from permanent cache)
```

### Key Design Decisions

#### 1. Calculate Code Metrics from Files Endpoint

**Decision**: Fetch file lists from `/repos/{owner}/{repo}/pulls/{number}/files` and calculate aggregate code statistics by summing per-file additions, deletions, and counting files.

**Rationale**:

- Files endpoint provides per-file `additions`, `deletions`, and `changes` which can be summed for aggregates
- Same endpoint provides filenames needed for language detection
- Eliminates need for separate full PR details API call (N API calls instead of 2N)
- These metrics are critical for showcasing technical impact and scope
- Search API provides author_association without additional calls
- More efficient than fetching both PR details and files separately

**Trade-off**: Requires N API calls (one per PR for file lists). Mitigated by:

- Time-limited caching with 6-hour TTL for file lists
- Cache enables reuse when users generate multiple reports (1 year, 2 years, all time)
- Parallel fetching with semaphore (max 10 concurrent)
- Rate limit awareness and waiting
- High cache hit rate for subsequent time period expansions

#### 2. Two-Tier Caching Strategy: Intermediate vs Final Data

**Decision**: Use 6-hour TTL cache for intermediate API data (file lists) but permanent cache for final report data (aggregated metrics, language percentages, rendered reports).

**Rationale**:

- **Intermediate Layer (6-hour TTL)**: Raw file lists from GitHub API
  - Enables efficient generation when users request overlapping time periods
  - Example: Generate 1-year report, then 2-year report reuses cached file lists from first year
  - TTL prevents indefinite growth of raw API response data
  - Configurable TTL (default 6 hours) balances freshness vs API efficiency

- **Final Layer (Permanent)**: Fully computed report data with all aggregations
  - **Critical requirement**: Reports must remain viewable indefinitely for public access
  - Users can view reports without authentication once generated
  - Includes all computed fields: additions, deletions, changed_files, language percentages
  - Stored as complete PullRequestInfo objects with all metrics calculated
  - Never expires - reports are historical snapshots that should not disappear

**Implementation**:

- File lists: `cache_pr_files(owner, repo, number, ttl=6*3600)`
- Report data: `cache_report(username, period, data, ttl=None)` (permanent)
- PullRequestInfo objects in reports: Include all computed metrics, stored permanently

#### 3. Optional Fields with Graceful Degradation

**Decision**: All new fields in `PullRequestInfo` are optional (typed as `Type | None = None`).

**Rationale**:

- Backward compatibility with existing code and cached data
- Handles missing data from API gracefully (GitHub sometimes omits fields)
- Templates can check for None and display "N/A" or hide the field
- Aggregate calculations performed from intermediate cached file data when available

**Implementation**:

```python
@dataclass
class PullRequestInfo:
    # Existing required fields
    number: int
    title: str
    # ... other required fields

    # New optional fields
    additions: int | None = None
    deletions: int | None = None
    changed_files: int | None = None
    author_association: str | None = None
```

#### 4. Aggregate and Store Final Metrics Permanently

**Decision**: Calculate summary metrics (total additions/deletions/files, language percentages, repo-level roles) during report generation and store them permanently as part of the report data.

**Rationale**:

- Keeps business logic out of templates
- Makes testing easier
- Computed metrics stored permanently with the report
- Templates receive ready-to-display data from permanent cache
- Reports remain viewable indefinitely without re-computation
- All PullRequestInfo objects in cached reports include computed metrics

**Implementation**:

```python
# In generate_report_data()
total_additions = sum(pr.additions or 0 for pr in prs)
total_deletions = sum(pr.deletions or 0 for pr in prs)
total_changed_files = sum(pr.changed_files or 0 for pr in prs)

# Language analysis (using separate utility)
from gitbrag.services.language_analyzer import calculate_language_percentages
language_breakdown = calculate_language_percentages(prs)

# Repository-level roles (from most recent PR per repo)
repo_roles = {}
for repo_name, repo_prs in repos.items():
    # Most recent PR in time period
    most_recent = max(repo_prs, key=lambda pr: pr.created_at)
    repo_roles[repo_name] = most_recent.author_association
```

#### 5. Incremental Template Enhancement

**Decision**: Add new metrics strategically without overwhelming the display.

**Rationale**:

- Avoid cluttering the report with too much information
- Maintain readability, especially on mobile
- Focus on technical impact over engagement metrics

**Priority Order**:

1. Code change statistics in summary card (additions, deletions, files)
2. Language breakdown in summary card (top 3-5 languages with %)
3. Repository-level role badges in repository headers
4. PR size category in PR table ("Small", "Medium", "Large", etc.)

#### 6. PR Size Categorization for Compact Display

**Decision**: Display PR size as a category ("One Liner", "Small", "Medium", "Large", "Huge", "Massive") instead of raw additions/deletions in the PR table. Focus aggregate statistics in summary sections.

**Rationale**:

- Keeps PR table compact and scannable
- Size categories provide intuitive understanding of PR scope
- Raw numbers in summary provide exact totals
- Categories remain consistent across all reports (standardized thresholds)
- Single concise column instead of multiple numeric columns

**Size Categories** (based on additions + deletions):

- **One Liner**: 1 line changed
- **Small**: 2-100 lines changed
- **Medium**: 101-500 lines changed
- **Large**: 501-1500 lines changed
- **Huge**: 1501-5000 lines changed
- **Massive**: 5000+ lines changed

**Implementation**:

```python
def categorize_pr_size(additions: int, deletions: int) -> str:
    """Categorize PR size based on total lines changed."""
    total_lines = additions + deletions
    if total_lines <= 1:
        return "One Liner"
    elif total_lines <= 100:
        return "Small"
    elif total_lines <= 500:
        return "Medium"
    elif total_lines <= 1500:
        return "Large"
    elif total_lines <= 5000:
        return "Huge"
    else:
        return "Massive"
```

#### 7. Visual Hierarchy for Code Metrics and Roles

**Decision**: Use color coding for PR size categories and badges for repository-level roles.

**Rationale**:

- Size categories can be color-coded for visual scanning
- Repository-level role badges show authority without cluttering PR table
- Compact formatting keeps tables readable

**CSS Pattern**:

```css
.pr-size {
    font-size: 0.75rem;
    font-weight: 600;
    padding: 2px 6px;
    border-radius: 3px;
    white-space: nowrap;
}

.size-one-liner { background: #e1f5fe; color: #01579b; }
.size-small { background: #e8f5e9; color: #1b5e20; }
.size-medium { background: #fff3e0; color: #e65100; }
.size-large { background: #fce4ec; color: #880e4f; }
.size-huge { background: #f3e5f5; color: #4a148c; }
.size-massive { background: #ffebee; color: #b71c1c; }

.role-badge {
    font-size: 0.7rem;
    padding: 2px 6px;
    border-radius: 3px;
}

.role-owner { background: #6f42c1; color: white; }
.role-member { background: #0366d6; color: white; }
.role-contributor { background: #28a745; color: white; }
```

## Data Mapping

### From GitHub APIs to PullRequestInfo

| GitHub API Field | Source API | PullRequestInfo Field | Type | Notes |
|------------------|------------|----------------------|------|-------|
| `item["author_association"]` | Search API | `author_association` | `str \| None` | OWNER, MEMBER, CONTRIBUTOR, etc. |
| Sum of file `additions` | Files API | `additions` | `int \| None` | Lines added (calculated) |
| Sum of file `deletions` | Files API | `deletions` | `int \| None` | Lines deleted (calculated) |
| Count of files | Files API | `changed_files` | `int \| None` | Number of files modified (calculated) |

### Language Detection from File Extensions

Comprehensive extension mappings (non-exhaustive, can be extended):

**Compiled/Static Languages**:

- `.c`, `.h` → C
- `.cpp`, `.cc`, `.cxx`, `.hpp`, `.hh`, `.hxx` → C++
- `.cs` → C#
- `.java` → Java
- `.kt`, `.kts` → Kotlin
- `.scala` → Scala
- `.go` → Go
- `.rs` → Rust
- `.swift` → Swift
- `.m`, `.mm` → Objective-C
- `.dart` → Dart
- `.zig` → Zig
- `.nim` → Nim

**Scripting/Dynamic Languages**:

- `.py`, `.pyw`, `.pyx` → Python
- `.js`, `.mjs`, `.cjs` → JavaScript
- `.jsx` → JavaScript (React)
- `.ts`, `.mts`, `.cts` → TypeScript
- `.tsx` → TypeScript (React)
- `.rb`, `.rake`, `.gemspec` → Ruby
- `.php`, `.phtml` → PHP
- `.pl`, `.pm` → Perl
- `.lua` → Lua
- `.r`, `.R` → R
- `.jl` → Julia
- `.groovy`, `.gradle` → Groovy

**Shell/Scripting**:

- `.sh`, `.bash`, `.zsh` → Shell
- `.ps1`, `.psm1` → PowerShell
- `.bat`, `.cmd` → Batch
- `.awk` → AWK
- `.sed` → Sed

**Web Technologies**:

- `.html`, `.htm` → HTML
- `.css` → CSS
- `.scss`, `.sass` → SCSS/Sass
- `.less` → Less
- `.vue` → Vue
- `.svelte` → Svelte
- `.astro` → Astro

**Functional Languages**:

- `.hs`, `.lhs` → Haskell
- `.ml`, `.mli` → OCaml
- `.fs`, `.fsx`, `.fsi` → F#
- `.clj`, `.cljs`, `.cljc` → Clojure
- `.ex`, `.exs` → Elixir
- `.erl`, `.hrl` → Erlang
- `.elm` → Elm

**Data/Config Formats**:

- `.json`, `.jsonc` → JSON
- `.yaml`, `.yml` → YAML
- `.toml` → TOML
- `.xml` → XML
- `.ini`, `.cfg`, `.conf` → INI/Config
- `.env` → Environment
- `.sql` → SQL
- `.graphql`, `.gql` → GraphQL
- `.proto` → Protocol Buffers

**Documentation/Markup**:

- `.md`, `.markdown` → Markdown
- `.rst` → reStructuredText
- `.tex`, `.latex` → LaTeX
- `.adoc`, `.asciidoc` → AsciiDoc

**Build/DevOps**:

- `.dockerfile`, `Dockerfile` → Dockerfile
- `.tf`, `.tfvars`, `.tofu` → Terraform
- `.bicep` → Bicep
- `.makefile`, `Makefile`, `.mk` → Makefile
- `.cmake` → CMake

**Mobile/Platform Specific**:

- `.kt`, `.kts` → Kotlin (Android)
- `.swift` → Swift (iOS)
- `.dart` → Dart (Flutter)
- `.xaml` → XAML

**Assembly/Low-Level**:

- `.asm`, `.s` → Assembly
- `.wasm` → WebAssembly

**Special Handling**:

- Files without extensions: Attempt detection from filename (e.g., `Makefile`, `Dockerfile`)
- Hidden files (starting with `.`): Skip unless explicitly known (e.g., `.bashrc` → Shell)
- Multiple extensions (e.g., `.test.js`, `.spec.ts`): Use rightmost extension
- Unknown extensions: Group as "Other"

**Implementation**: File list is fetched from `/repos/{owner}/{repo}/pulls/{number}/files` API for each PR, cached with 6-hour TTL alongside PR details. Language analyzer uses comprehensive dictionary with case-insensitive matching.

### Author Association Values (Repository-Level)

GitHub returns these values for `author_association` (used to determine repository-level role):

- `OWNER` - Repository owner
- `MEMBER` - Organization member
- `COLLABORATOR` - Repository collaborator
- `CONTRIBUTOR` - Previously committed to repo
- `FIRST_TIME_CONTRIBUTOR` - First-time contributor
- `FIRST_TIMER` - First-time GitHub user
- `NONE` - No association

The system uses the author_association from the most recent PR in the time period to determine the developer's role for that repository.

## Display Design

### Summary Card Enhancement

Current layout (mobile-first grid):

```text
[Total PRs] [Merged] [Open] [Closed] [Repositories] [Stars Gained]
```

Enhanced layout:

```text
[Total PRs] [Merged] [Open] [Closed]
[Repositories] [Stars Gained] [Lines Added] [Lines Deleted]
[Files Changed] [Languages: Python 45% • JavaScript 30% • Go 15%]
```

Grid wraps naturally on mobile, showing 1-2 items per row. Language breakdown may span full width.

### Repository Header Enhancement

Current header:

```text
[Repository Name] [PR Count] [Stars]
```

Enhanced header:

```text
[Repository Name] [OWNER Badge] [PR Count] [Stars]
```

Role badge appears next to repository name, color-coded by relationship.

### PR Table Enhancement

Current columns:

```text
| PR # | Title | Status | Created |
```

Enhanced columns:

```text
| PR # | Title | Size | Status | Created |
```

Where:

- **Size**: Category badge showing PR scope ("Small", "Medium", "Large", etc.)
- Color coded by category: blues/greens for smaller, oranges/reds for larger
- Concise single word or two-word label
- Based on additions + deletions (files changed not included in size calculation)

### Mobile Considerations

On narrow screens (<768px):

- Hide "Created" column (least critical)
- Keep "Size" column visible (high value for technical showcase, very compact)
- Repository role badges remain visible (small, high signal)
- Language breakdown may stack vertically in summary card
- Maintain horizontal scrolling for table if needed

## Performance Impact

### Expected API Call Pattern

**Before**: 1 search API call + N stargazer calls (optional)

**After**: 1 search API call + N file list calls + N stargazer calls (optional)

- N additional API calls required (one per PR for file lists)
- File lists provide both code metrics (via calculation) and language data
- Mitigated by 6-hour TTL caching for file lists
- Cached file lists skip API calls within TTL window
- Cache enables reuse when users generate reports for expanding time periods
- Parallel fetching with semaphore limits concurrency
- Rate limit awareness prevents 403 errors

**Rate Limit Impact**: Significant on first generation or after cache expiry (N calls), minimal within cache TTL window

### Processing Overhead

- Fetching and processing file lists per PR: O(F) where F = files per PR
- Calculating aggregate code metrics from file data: O(F) where F = files per PR
- Language analysis from file extensions: O(n) where n = total files across all PRs
- Aggregate calculations: O(n) where n = number of PRs (already iterating)
- Repository role determination: O(m) where m = number of repositories
- Expected: 15-25% increase in first-time report generation (due to N API calls)
- Expected: <5% increase on cached reports (calculation only, no API calls)

### Cache Considerations

**Intermediate Layer (6-hour TTL, configurable)**:

- File lists cached: ~1-5KB per PR (depends on file count, includes per-file metrics)
- For 100 PRs: ~100-500KB intermediate cache storage
- TTL prevents indefinite growth of raw API data
- Cache automatically expires after 6 hours (configurable)
- Enables efficient overlapping report generation (1 year → 2 years → all time)

**Final Layer (Permanent, never expires)**:

- Complete report data with all computed metrics: ~50-100 bytes per PR base + file metadata
- Includes fully populated PullRequestInfo objects with additions, deletions, changed_files
- Includes aggregate statistics: total lines changed, language percentages, repo roles
- For 100 PRs: ~100-500KB permanent report storage
- **Critical**: Reports must remain accessible indefinitely for public viewing
- Users can share and view reports without authentication
- Historical snapshots should never disappear

**Cache Reuse Pattern**:

1. User generates 1-year report: File lists cached (6hr TTL), report stored permanently
2. User generates 2-year report within 6 hours: Reuses cached file lists from year 1, fetches only new PRs
3. User generates all-time report: High cache hit rate for recent PRs
4. Public user views any generated report: Served from permanent cache, no API calls

## Error Handling

### Missing Field Handling

```python
# Safe extraction from search API
author_association = item.get("author_association", None)

# Safe extraction and calculation from files API
async def fetch_pr_files_and_calculate(owner, repo, number):
    try:
        files = await client.get_pr_files(owner, repo, number)
        additions = sum(f.get("additions", 0) for f in files)
        deletions = sum(f.get("deletions", 0) for f in files)
        changed_files = len(files)
        return {
            "additions": additions,
            "deletions": deletions,
            "changed_files": changed_files,
            "files": files,
        }
    except httpx.HTTPStatusError as e:
        logger.warning(f"Failed to fetch files for PR {owner}/{repo}#{number}: {e}")
        return {"additions": None, "deletions": None, "changed_files": None, "files": []}
```

### Template Null Checks

```jinja2
{# Repository-level role badge #}
{% if repo_role %}
  <span class="role-badge role-{{ repo_role.lower() }}">
    {{ repo_role }}
  </span>
{% endif %}

{# Code change display #}
{% if pr.additions is not none and pr.deletions is not none %}
  <span class="code-additions">+{{ pr.additions }}</span>
  <span class="code-deletions">-{{ pr.deletions }}</span>
{% else %}
  <span class="text-secondary">-</span>
{% endif %}
```

## Testing Strategy

### Unit Tests

- Model serialization with code metric fields
- Backward compatibility with old model instances
- Language detection from various file extensions
- Language percentage calculation accuracy
- Null handling in aggregation functions
- Repository role determination logic

### Integration Tests

- Mock full PR API responses including code metrics
- Test extraction and mapping logic
- Verify aggregate calculations (totals, percentages)
- Test caching layer for full PR details
- Test parallel fetching with rate limit simulation

### Manual Testing

- Generate reports for real users with various contribution patterns
- Verify language detection accuracy
- Test visual appearance in light/dark mode
- Verify responsive behavior on mobile
- Check performance with large PR counts (100+)
- Monitor rate limit consumption and caching effectiveness

## Future Enhancements

### Per-Repository Language Breakdown

- Currently shows aggregate languages across all PRs
- Could analyze languages contributed to each repository separately
- Show in repository headers or expandable sections
- Helps demonstrate breadth within specific projects

### Commit Count per PR

- Full PR API includes `commits` field
- Could display alongside code changes
- Helps distinguish small PRs from large refactors

### Code Review Metrics

- Full PR API includes `review_comments` (separate from regular comments)
- Could show review engagement as separate metric
- Requires careful distinction between comment types

### Per-Repository Language Breakdown

- Analyze languages contributed to each repository
- Show in repository headers or expandable sections
- Helps demonstrate breadth within specific projects
