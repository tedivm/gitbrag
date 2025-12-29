# username-normalization Specification

## Purpose
TBD - created by archiving change polish-ux-improvements. Update Purpose after archive.
## Requirements
### Requirement: Web interface URL routing and user report display

The system MUST normalize GitHub usernames to lowercase in all cache keys and URLs to prevent duplicate cache entries and ensure consistent URL sharing.

#### Scenario: Redirect uppercase usernames to lowercase URLs

**Given** a user visits `/user/github/TedIVM`
**And** the username contains uppercase characters
**When** the route handler processes the request
**Then** the system returns a 301 permanent redirect to `/user/github/tedivm`
**And** all query parameters are preserved (e.g., `?period=1_year&force=true`)
**And** the redirect uses the `RedirectResponse` with `status_code=301`

#### Scenario: Accept lowercase usernames without redirect

**Given** a user visits `/user/github/tedivm`
**And** the username is already lowercase
**When** the route handler processes the request
**Then** the system proceeds normally without redirect
**And** the report is generated or served from cache

#### Scenario: Cache keys use lowercase usernames

**Given** the system needs to generate a cache key for user "TedIVM"
**When** `generate_cache_key(username="TedIVM", period="1_year")` is called
**Then** the cache key uses lowercase username: `report:tedivm:1_year:{params_hash}`
**And** subsequent requests for "tedivm", "TEDIVM", or "TedIVM" use the same cache key

#### Scenario: User profile cache keys use lowercase usernames

**Given** the system needs to cache or retrieve a user profile
**When** `get_or_fetch_user_profile(username="TedIVM")` is called
**Then** the profile cache key uses lowercase username: `profile:tedivm`
**And** the system fetches from GitHub API using the original case (GitHub is case-preserving)
**And** the cache stores the response for future requests regardless of input case

#### Scenario: Mixed case usernames in bookmarks resolve consistently

**Given** multiple users have bookmarked different case variants of the same username
**When** any user visits `/user/github/TEDIVM`, `/user/github/TedIVM`, or `/user/github/tedivm`
**Then** all requests redirect to or serve `/user/github/tedivm`
**And** all requests use the same cached data
**And** no duplicate cache entries are created

