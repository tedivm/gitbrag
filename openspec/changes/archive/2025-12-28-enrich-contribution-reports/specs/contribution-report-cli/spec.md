# contribution-report-cli Specification Delta

This document describes modifications to the contribution-report-cli capability to support enriched contribution reports with code statistics, language analysis, and repository roles.

## MODIFIED Requirements

### Requirement: Output formatting and visualization

**Changes**: Added code statistics (additions, deletions, files changed), language breakdown, and repository-level role indicators to CLI output.

The system MUST format pull request information in a clear, readable, and visually appealing terminal output using Rich library for enhanced display, including code change metrics and programming languages.

#### Scenario: Display PR size categories in formatted table

**Given** a successful query returning PRs with code metrics
**When** the system formats the output
**Then** PRs are displayed in a Rich table with all standard columns
**And** the table includes a "Size" column showing PR size category (e.g., "Small", "Medium", "Large")
**And** size categories are color-coded: blue/green for smaller, orange/red for larger
**And** categories are displayed as concise badges ("One Liner", "Small", "Medium", "Large", "Huge", "Massive")
**And** the table adjusts column widths to accommodate size badges
**And** size is calculated from additions + deletions (files changed not included)

#### Scenario: Display language breakdown in summary section

**Given** a successful query returning PRs from multiple repositories
**And** language data has been calculated from PR file extensions
**When** the system formats the output
**Then** the CLI displays a summary section before the PR table
**And** the summary includes total additions, total deletions, and total files changed
**And** the summary displays a "Languages" breakdown showing top languages with percentages
**And** language breakdown shows top 3-5 languages (e.g., "Python 45% • JavaScript 30% • Go 15%")
**And** languages are color-coded if the terminal supports colors
**And** the summary is visually separated from the PR table

#### Scenario: Display repository-level roles in repository headers

**Given** a successful query returning PRs from multiple repositories
**And** repository role data (author_association) is available from GitHub
**When** the system formats the output grouped by repository
**Then** each repository header includes the user's role badge (e.g., "OWNER", "MEMBER", "CONTRIBUTOR")
**And** role badges are color-coded: purple for OWNER, blue for MEMBER, green for CONTRIBUTOR
**And** role badges are displayed next to the repository name
**And** role is determined from the most recent PR in the time period for that repository

#### Scenario: Handle missing code metrics gracefully

**Given** a PR without code metrics (additions/deletions/files are None)
**When** the system formats the output
**Then** the Size column displays "-" or "N/A" for that PR
**And** the PR is still included in the table
**And** aggregate totals in the summary exclude PRs with missing metrics
**And** no errors occur due to missing data

#### Scenario: Hide size categories when unavailable

**Given** a query returning PRs without code metrics or language data
**When** the system formats the output
**Then** the Size column is omitted from the table if all PRs lack metrics
**And** the language breakdown is omitted from the summary if no language data exists
**And** the standard PR table is displayed without enrichment
**And** no errors or warnings are shown about missing data

## ADDED Requirements

### Requirement: PR size categorization

The system MUST categorize each PR by size based on total lines changed (additions + deletions) using consistent, predefined categories to provide intuitive understanding of PR scope in a compact CLI display format.

**Size Categories** (based on additions + deletions):

- **One Liner**: 1 line changed
- **Small**: 2-100 lines changed
- **Medium**: 101-500 lines changed
- **Large**: 501-1500 lines changed
- **Huge**: 1501-5000 lines changed
- **Massive**: 5000+ lines changed

#### Scenario: Display size categories with Rich formatting

**Given** a successful query returning PRs with various sizes
**When** the system formats the output
**Then** size categories are displayed as styled badges using Rich
**And** "One Liner" displays with cyan/blue styling
**And** "Small" displays with green styling
**And** "Medium" displays with yellow/orange styling
**And** "Large" displays with magenta styling
**And** "Huge" displays with red styling
**And** "Massive" displays with bold red styling
**And** all categories are visually distinct and readable in terminal

#### Scenario: Calculate size consistently with web interface

**Given** a PR has 150 additions and 30 deletions
**When** the CLI calculates PR size
**Then** total lines changed = 180 (additions + deletions)
**And** the PR is categorized as "Medium"
**And** the categorization uses the same thresholds as the web interface
**And** files changed count is not included in size calculation

### Requirement: Code statistics summary display

The system MUST display aggregate code change statistics in the CLI summary section, showing totals across all PRs in the query.

#### Scenario: Display aggregate code metrics in summary

**Given** a successful query returning multiple PRs with code metrics
**When** the system generates the summary section
**Then** the summary displays "Total Lines Added: X"
**And** the summary displays "Total Lines Deleted: Y"
**And** the summary displays "Total Files Changed: Z"
**And** metrics are displayed in a visually distinct section using Rich formatting
**And** values are formatted with thousand separators for readability (e.g., "1,234")

#### Scenario: Calculate aggregate totals correctly

**Given** a query returning 5 PRs with the following metrics:

- PR1: +100 -20 (3 files)
- PR2: +50 -10 (2 files)
- PR3: +200 -50 (5 files)
- PR4: None (missing metrics)
- PR5: +75 -30 (4 files)

**When** the system calculates aggregate totals
**Then** Total Lines Added = 425 (100+50+200+75)
**And** Total Lines Deleted = 110 (20+10+50+30)
**And** Total Files Changed = 14 (3+2+5+4)
**And** PR4 with missing metrics is excluded from totals

### Requirement: Language contribution analysis display

The system MUST analyze and display programming language contributions in the CLI, calculated from file extensions across all PRs.

#### Scenario: Display language breakdown with percentages

**Given** a successful query returning PRs touching files with various extensions
**And** files include: 10 .py files, 5 .js files, 3 .go files, 2 .md files
**When** the system calculates language contributions
**Then** the summary displays "Languages: Python 50% • JavaScript 25% • Go 15% • Markdown 10%"
**And** languages are sorted by percentage descending
**And** percentages are calculated from file counts across all PRs
**And** languages are displayed using Rich formatting with colors

#### Scenario: Limit language display to top languages

**Given** a query returning PRs touching files in 15 different languages
**When** the system displays the language breakdown
**Then** only the top 5 languages by file count are shown
**And** remaining languages are grouped as "Other X%"
**And** the display remains concise and readable

#### Scenario: Handle PRs without language data

**Given** a query returning PRs without file extension data
**When** the system attempts to display language breakdown
**Then** the language section is omitted from the summary
**And** no errors occur
**And** the rest of the output displays normally

### Requirement: Repository-level role indication

The system MUST display the user's repository-level role (author_association) for each repository in the CLI output.

#### Scenario: Display role badges in repository grouping

**Given** a query returning PRs from 3 repositories
**And** user is OWNER of repo1, MEMBER of repo2, and CONTRIBUTOR of repo3
**When** the system groups PRs by repository
**Then** repo1 header shows "OWNER" badge in purple
**And** repo2 header shows "MEMBER" badge in blue
**And** repo3 header shows "CONTRIBUTOR" badge in green
**And** badges are visually distinct using Rich styling

#### Scenario: Determine role from most recent PR

**Given** a repository with multiple PRs in the time period
**And** PRs have author_association values: "CONTRIBUTOR" (oldest), "MEMBER" (newest)
**When** the system determines the repository role
**Then** the role displayed is "MEMBER" (from most recent PR)
**And** the logic uses the PR with the latest created_at timestamp

#### Scenario: Handle missing role data

**Given** a PR without author_association field (None)
**When** the system displays repository information
**Then** no role badge is displayed for that repository
**And** the repository header displays normally without the badge
**And** no errors occur due to missing role data

## Dependencies

This specification delta depends on:

- `github-pull-request-collection` spec delta: PR file fetching and code metrics
- Rich library for terminal formatting and colors
- Existing CLI command structure and Typer framework
- Language analysis utility (file extension mapping)
