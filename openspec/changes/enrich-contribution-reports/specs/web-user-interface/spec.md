# web-user-interface Spec Delta

## MODIFIED Requirements

### Requirement: Two-section report layout

The system MUST display contribution reports in a structured format with an enhanced summary section showing code change statistics, language breakdown, and a detailed repository-by-repository breakdown with enriched PR information including repository-level roles and technical metrics.

#### Scenario: Display code change statistics in summary card

**Given** a user has authenticated and requests a report for "octocat"
**And** the report contains PRs with code change data
**And** total additions across all PRs is 5,234 lines
**And** total deletions across all PRs is 1,876 lines
**And** total files changed across all PRs is 342
**When** the report page renders
**Then** the summary card displays total lines added (+5,234)
**And** the summary card displays total lines deleted (-1,876)
**And** the summary card displays total files changed (342 files)
**And** code metrics are visually distinct with appropriate formatting
**And** the summary grid wraps naturally on mobile devices

#### Scenario: Display language breakdown in summary card

**Given** a user has authenticated and requests a report for "octocat"
**And** the report contains PRs modifying files in various languages
**And** 45% of changed files are Python (.py)
**And** 30% of changed files are JavaScript (.js)
**And** 15% of changed files are Go (.go)
**And** 10% of changed files are other languages
**When** the report page renders
**Then** the summary card displays top languages with percentages
**And** languages are shown as "Python 45% • JavaScript 30% • Go 15%"
**And** the display is compact and visually appealing
**And** only top 3-5 languages are shown to avoid clutter

#### Scenario: Display repository-level contributor role

**Given** a user has authenticated and requests a report for "octocat"
**And** the report contains PRs to multiple repositories
**And** user is OWNER of "octocat/repo1"
**And** user is MEMBER of "github/repo2"
**And** user is CONTRIBUTOR to "rails/rails"
**When** the report page renders
**Then** each repository section header displays the contributor role
**And** "octocat/repo1" shows "OWNER" badge
**And** "github/repo2" shows "MEMBER" badge
**And** "rails/rails" shows "CONTRIBUTOR" badge
**And** role badges use color coding (purple for OWNER, blue for MEMBER, green for CONTRIBUTOR)

#### Scenario: Display PR size category in PR table

**Given** a user has authenticated and requests a report for "octocat"
**And** PR #123 has 150 additions and 30 deletions (180 total lines, categorized as "Medium")
**And** PR #456 has 15 additions and 8 deletions (23 total lines, categorized as "Small")
**And** PR #789 has 2000 additions and 500 deletions (2500 total lines, categorized as "Huge")
**When** the report page renders
**Then** the PR table includes a "Size" column
**And** PR #123 shows "Medium" with appropriate color coding
**And** PR #456 shows "Small" with appropriate color coding
**And** PR #789 shows "Huge" with appropriate color coding
**And** size categories use consistent badge styling across all PRs
**And** color coding ranges from blue/green (smaller) to orange/red (larger)

#### Scenario: Handle missing enrichment data gracefully

**Given** a user has authenticated and requests a report for "octocat"
**And** some PRs lack code change data (None values)
**When** the report page renders
**Then** PRs without code change data show "-" or "N/A" in size column
**And** PRs without role data show "-" or hide the role badge
**And** the table layout remains consistent despite missing data
**And** no errors or broken display elements appear

#### Scenario: Maintain responsive layout with new columns

**Given** a user views a report on a mobile device (viewport width < 768px)
**And** the PR table has additional columns (Size)
**When** the page renders on mobile
**Then** the most important columns remain visible (PR#, Title, Size, Status)
**And** less critical columns adapt (e.g., Created date may hide)
**And** the table remains horizontally scrollable if needed
**And** size category badges remain readable on small screens
**And** text remains readable without excessive zooming

## ADDED Requirements

### Requirement: PR size categorization

The system MUST categorize each PR by size based on total lines changed (additions + deletions) using consistent, predefined categories to provide intuitive understanding of PR scope in a compact display format.

#### Scenario: Calculate PR size from additions and deletions

**Given** PR #123 has 150 additions and 30 deletions
**When** the system calculates PR size
**Then** total lines changed = 180 (150 + 30)
**And** files changed count is not included in size calculation
**And** the calculation handles None values gracefully (treating as 0)

#### Scenario: Categorize PR as "One Liner"

**Given** a PR has 1 addition and 0 deletions (1 total line)
**When** the system categorizes the PR
**Then** the PR is categorized as "One Liner"
**And** the category threshold is exactly 1 total line changed

#### Scenario: Categorize PR as "Small"

**Given** a PR has 30 additions and 15 deletions (45 total lines)
**When** the system categorizes the PR
**Then** the PR is categorized as "Small"
**And** the category threshold is 2-100 total lines changed

#### Scenario: Categorize PR as "Medium"

**Given** a PR has 250 additions and 100 deletions (350 total lines)
**When** the system categorizes the PR
**Then** the PR is categorized as "Medium"
**And** the category threshold is 101-500 total lines changed

#### Scenario: Categorize PR as "Large"

**Given** a PR has 800 additions and 300 deletions (1100 total lines)
**When** the system categorizes the PR
**Then** the PR is categorized as "Large"
**And** the category threshold is 501-1500 total lines changed

#### Scenario: Categorize PR as "Huge"

**Given** a PR has 2000 additions and 500 deletions (2500 total lines)
**When** the system categorizes the PR
**Then** the PR is categorized as "Huge"
**And** the category threshold is 1501-5000 total lines changed

#### Scenario: Categorize PR as "Massive"

**Given** a PR has 10000 additions and 2000 deletions (12000 total lines)
**When** the system categorizes the PR
**Then** the PR is categorized as "Massive"
**And** the category threshold is 5000+ total lines changed

#### Scenario: Display size category with color coding

**Given** various PRs with different size categories
**When** the PR table renders
**Then** "One Liner" displays with light blue background (#e1f5fe)
**And** "Small" displays with light green background (#e8f5e9)
**And** "Medium" displays with light orange background (#fff3e0)
**And** "Large" displays with light pink background (#fce4ec)
**And** "Huge" displays with light purple background (#f3e5f5)
**And** "Massive" displays with light red background (#ffebee)
**And** all badges have appropriate dark text color for contrast

#### Scenario: Handle PRs without code metrics

**Given** a PR has no additions or deletions data (None values)
**When** the system attempts to categorize the PR
**Then** the PR size is displayed as "-" or "N/A"
**And** no size badge is shown, or a neutral badge is displayed
**And** the table layout remains consistent

### Requirement: Code change statistics display

The system MUST display aggregate code change statistics (total additions, total deletions, total files changed) in the summary card to showcase the overall technical scope and scale of developer contributions.

#### Scenario: Show code changes per PR in table

**REMOVED** - Replaced by PR size categorization

#### Scenario: Display aggregate code statistics in summary

**Given** a report is generated with multiple PRs
**And** total additions across all PRs is 5,234
**And** total deletions across all PRs is 1,876
**And** total files changed is 342
**When** the summary card renders
**Then** total additions are displayed prominently (+5,234)
**And** total deletions are displayed prominently (-1,876)
**And** total files changed is displayed (342 files)
**And** metrics are visually balanced with other summary stats
**And** the net change can be calculated by viewers (additions - deletions)

#### Scenario: Format large numbers for readability

**Given** code change statistics with large numbers
**And** a PR has 12,345 additions
**When** the statistics are displayed
**Then** numbers use thousands separators (+12,345)
**And** very large numbers may use abbreviated format (e.g., +12.3k)
**And** formatting is consistent across the report
**And** numbers remain accurate (no rounding that loses information)

### Requirement: Language contribution analysis

The system MUST analyze file extensions from changed files to determine programming languages and display language expertise breakdown in the summary card.

#### Scenario: Extract file extensions from PR data

**Given** a PR modifies files: "app.py", "utils.py", "index.js", "README.md"
**When** the system analyzes the PR
**Then** file extensions are extracted: [".py", ".py", ".js", ".md"]
**And** extensions are normalized to lowercase
**And** files without extensions are tracked separately
**And** the extraction handles edge cases (hidden files, multiple dots)

#### Scenario: Map file extensions to programming languages

**Given** extracted extensions include .py, .js, .go, .java, .rb
**When** the system maps extensions to languages
**Then** .py maps to "Python"
**And** .js maps to "JavaScript"
**And** .go maps to "Go"
**And** .java maps to "Java"
**And** .rb maps to "Ruby"
**And** common extensions are supported (comprehensive mapping)
**And** unknown extensions map to "Other" or are excluded

#### Scenario: Calculate language contribution percentages

**Given** a report with 100 total changed files
**And** 45 files are Python (.py)
**And** 30 files are JavaScript (.js)
**And** 15 files are Go (.go)
**And** 10 files are other languages
**When** language percentages are calculated
**Then** Python is 45% of contributions
**And** JavaScript is 30% of contributions
**And** Go is 15% of contributions
**And** Other is 10% of contributions
**And** percentages sum to 100%

#### Scenario: Display top languages in summary card

**Given** language contributions have been calculated
**And** top languages are Python (45%), JavaScript (30%), Go (15%)
**When** the summary card renders
**Then** top 3-5 languages are displayed
**And** format is concise: "Python 45% • JavaScript 30% • Go 15%"
**And** languages are sorted by percentage descending
**And** very small percentages (<5%) may be grouped as "Other"
**And** the display is visually distinct from other metrics

#### Scenario: Handle reports with no language data

**Given** a report where code change data is unavailable
**And** file extensions cannot be determined
**When** the summary card renders
**Then** the language section shows "N/A" or is hidden
**And** no errors occur
**And** other summary statistics display normally
**And** the layout adjusts gracefully

### Requirement: Repository-level role indication

The system MUST display the developer's contributor role (OWNER, MEMBER, CONTRIBUTOR) at the repository level to showcase their relationship and authority within each project.

#### Scenario: Determine repository role from PRs

**Given** a report includes 5 PRs to repository "octocat/repo1"
**And** all 5 PRs have author_association "OWNER"
**When** the repository role is determined
**Then** the repository is assigned role "OWNER"
**And** the role is derived from the most recent PR in the time period
**And** if PRs have different roles, the most recent takes precedence
**And** if no role data is available, the role is None

#### Scenario: Display role badge in repository header

**Given** a repository section is rendered
**And** the repository has assigned role "OWNER"
**When** the repository header displays
**Then** a role badge is shown next to the repository name
**And** the badge displays "OWNER" with purple background
**And** the badge is visually distinct and prominent
**And** the badge matches the styling of status badges elsewhere

#### Scenario: Color code role badges by relationship

**Given** multiple repositories with different roles
**And** "repo1" has role OWNER
**And** "repo2" has role MEMBER
**And** "repo3" has role CONTRIBUTOR
**When** repository headers render
**Then** OWNER badge has purple background (#6f42c1)
**And** MEMBER badge has blue background (#0366d6)
**And** CONTRIBUTOR badge has green background (#28a745)
**And** all badges have white text for contrast
**And** colors work in both light and dark modes

#### Scenario: Handle repositories without role data

**Given** a repository's PRs lack author_association data
**When** the repository header renders
**Then** no role badge is displayed, or a neutral badge shows "CONTRIBUTOR" as default
**And** the absence of role data doesn't break the layout
**And** other repository information displays normally
**And** the system logs when role data is missing for diagnostics
