# github-pull-request-collection Spec Delta

## MODIFIED Requirements

### Requirement: Pull request metadata collection

The system MUST collect comprehensive pull request information including code change statistics and contributor relationships to enable rich contribution reports that showcase developer technical impact.

#### Scenario: Fetch file lists and calculate code change statistics

**Given** a user requests a report with `collect_user_prs(username="octocat")`
**And** the search API returns basic PR data
**When** the system processes each PR
**Then** the system fetches file lists from `/repos/{owner}/{repo}/pulls/{number}/files`
**And** each file includes `additions`, `deletions`, and `filename` fields
**And** aggregate `additions` is calculated by summing additions across all files
**And** aggregate `deletions` is calculated by summing deletions across all files
**And** `changed_files` is calculated by counting the number of files
**And** code change statistics are stored as integers or None if unavailable
**And** the system handles API errors gracefully without failing the entire report

#### Scenario: Capture contributor relationship data

**Given** a user requests a report with `collect_user_prs(username="octocat")`
**And** the GitHub search API returns PR data including author_association
**When** the system processes the search results
**Then** each PullRequestInfo object includes `author_association` field
**And** author_association contains values like "OWNER", "MEMBER", "CONTRIBUTOR", etc.
**And** the field is None if the association data is missing
**And** the value is stored exactly as returned by GitHub API

#### Scenario: Extract file names for language detection

**Given** a user requests a report with `collect_user_prs(username="octocat")`
**And** the system has fetched file lists for PRs
**When** the system processes file lists for language analysis
**Then** file names are extracted from each file entry
**And** file extensions are available for language mapping
**And** file lists are cached with 6-hour TTL alongside aggregate metrics
**And** the system handles missing file data gracefully

#### Scenario: Cache file lists with TTL to balance efficiency and freshness

**Given** a PR's file list has been fetched previously
**And** the file list is stored in cache with 6-hour TTL
**When** the same PR is requested again within 6 hours (same repo, same PR number)
**Then** the system retrieves file list from cache
**And** no additional API call is made to GitHub
**And** cached data includes per-file metrics and filenames
**And** aggregate statistics are recalculated from cached file data
**And** cache expires after 6 hours enabling reuse across multiple report time periods
**And** expired cache triggers a fresh fetch on next request

#### Scenario: Handle rate limit efficiently when fetching file lists

**Given** a report requires fetching file lists for 50 PRs
**And** the GitHub API has rate limits
**When** the system fetches file lists
**Then** the system respects rate limits and waits if necessary
**And** the system uses parallel fetching with a semaphore to limit concurrency
**And** the system logs rate limit status for monitoring
**And** cached file lists are used whenever possible to reduce API calls

#### Scenario: Maintain backward compatibility with existing data

**Given** existing code that uses PullRequestInfo objects
**When** new optional fields are added (additions, deletions, changed_files)
**Then** existing code continues to work without modification
**And** old PullRequestInfo instances without new fields have None defaults
**And** serialization and deserialization handle missing fields gracefully
**And** no breaking changes are introduced to the data model

## ADDED Requirements

### Requirement: Extended pull request data model with code metrics

The system MUST provide a PullRequestInfo data model with optional fields for code change statistics to support technical impact reporting.

#### Scenario: Instantiate PullRequestInfo with code change data

**Given** PR data from GitHub full PR API includes code change statistics
**When** creating a PullRequestInfo object
**Then** the object accepts `additions` as an optional integer parameter (lines added)
**And** the object accepts `deletions` as an optional integer parameter (lines deleted)
**And** the object accepts `changed_files` as an optional integer parameter
**And** all fields default to None if not provided
**And** the fields are accessible via dot notation (pr.additions, pr.deletions, pr.changed_files)

#### Scenario: Calculate total code changes for a PR

**Given** a PullRequestInfo object with additions=150 and deletions=30
**When** calculating total code changes
**Then** the total can be computed as additions + deletions = 180
**And** the net change can be computed as additions - deletions = 120
**And** both metrics are useful for different reporting purposes

#### Scenario: Serialize PullRequestInfo with code metrics

**Given** a PullRequestInfo object with code change fields populated
**When** the object is serialized (for caching or transmission)
**Then** all code change fields are included in the serialization
**And** None values are preserved in the serialization
**And** the serialized format is compatible with existing cache structures
**And** deserialization recreates the object with all fields intact
