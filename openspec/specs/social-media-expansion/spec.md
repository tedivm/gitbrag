# social-media-expansion Specification

## Purpose
TBD - created by archiving change polish-ux-improvements. Update Purpose after archive.
## Requirements
### Requirement: GitHub API client social accounts support

The GitHub API client MUST provide a method to fetch a user's social accounts from the `/users/{username}/social_accounts` endpoint.

#### Scenario: Add get_user_social_accounts method to GitHubAPIClient

**Given** the GitHubAPIClient class needs to fetch social accounts
**When** `await client.get_user_social_accounts(username="tedivm")` is called
**Then** the method makes a GET request to `/users/tedivm/social_accounts`
**And** the method uses the same retry logic as other API calls
**And** the method returns a list of dictionaries with `provider` and `url` keys
**And** the method returns an empty list if the API returns 404 or empty array

#### Scenario: Social accounts API respects rate limiting

**Given** the GitHub API rate limit is reached
**When** `get_user_social_accounts()` is called
**Then** the method retries with exponential backoff like other API methods
**And** the method respects `X-RateLimit-Reset` header
**And** the method logs rate limit warnings

