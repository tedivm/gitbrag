# Social Media Expansion Spec Delta

## ADDED Requirements

### Requirement: User profile display in web interface

The system MUST display all available social media links from a user's GitHub profile, including Mastodon, LinkedIn, and Bluesky, by calling the GitHub `/users/{username}/social_accounts` API endpoint.

#### Scenario: Fetch social accounts from GitHub API

**Given** the system needs to display a user's profile
**When** `get_or_fetch_user_profile(username="tedivm", token="...")` is called
**Then** the system calls `GET /users/tedivm/social_accounts` on GitHub API
**And** the response contains an array of social account objects with `provider` and `url` fields
**And** the social accounts are merged into the user profile dictionary
**And** the combined profile data is cached with 1-hour TTL when authenticated

#### Scenario: Display Mastodon link in user profile

**Given** a user's GitHub profile includes a Mastodon account
**And** the social accounts API returns `{"provider": "mastodon", "url": "https://hachyderm.io/@tedivm"}`
**When** the user report template renders
**Then** the profile metadata section includes a Mastodon link
**And** the link uses an appropriate icon (🐘 or visual icon)
**And** the link opens in a new tab with `target="_blank"`
**And** the link text or accessible label indicates it's Mastodon

#### Scenario: Display LinkedIn link in user profile

**Given** a user's GitHub profile includes a LinkedIn account
**And** the social accounts API returns `{"provider": "linkedin", "url": "https://www.linkedin.com/in/roberthafner/"}`
**When** the user report template renders
**Then** the profile metadata section includes a LinkedIn link
**And** the link uses an appropriate icon (💼 or visual icon)
**And** the link opens in a new tab with `target="_blank"`
**And** the link text or accessible label indicates it's LinkedIn

#### Scenario: Display Bluesky link in user profile

**Given** a user's GitHub profile includes a Bluesky account
**And** the social accounts API returns `{"provider": "bluesky", "url": "https://bsky.app/profile/tedivm.com"}`
**When** the user report template renders
**Then** the profile metadata section includes a Bluesky link
**And** the link uses an appropriate icon (🦋 or visual icon)
**And** the link opens in a new tab with `target="_blank"`
**And** the link text or accessible label indicates it's Bluesky

#### Scenario: Continue displaying Twitter/X handle

**Given** a user's GitHub profile includes a Twitter username
**And** the user profile API returns `twitter_username: "tedivm"`
**When** the user report template renders
**Then** the profile metadata section includes a Twitter/X link
**And** the link format is `https://twitter.com/{twitter_username}`
**And** the link continues to use the existing icon (🐦)
**And** Twitter/X display is unchanged from current behavior

#### Scenario: Continue displaying blog URL

**Given** a user's GitHub profile includes a blog URL
**And** the user profile API returns `blog: "http://www.tedivm.com"`
**When** the user report template renders
**Then** the profile metadata section includes the blog link
**And** the link uses the existing icon (🔗)
**And** the link prepends `https://` if not already prefixed with `http://` or `https://`
**And** blog URL display is unchanged from current behavior

#### Scenario: Handle missing social accounts gracefully

**Given** a user's GitHub profile has no social accounts configured
**When** the social accounts API returns an empty array `[]`
**Then** the user report template renders without social media links (except Twitter and blog if present)
**And** no errors or warnings are displayed
**And** the profile layout remains consistent

#### Scenario: Handle social accounts API failure gracefully

**Given** the social accounts API call fails or times out
**When** `get_user_social_accounts()` raises an exception
**Then** the system logs the error with `logger.warning()`
**And** returns an empty list for social accounts
**And** the user profile is still cached with remaining data
**And** the report displays without social media links

#### Scenario: Cache social accounts with user profile

**Given** a user's profile and social accounts are fetched
**When** the profile is cached
**Then** social accounts are included in the cached profile dictionary
**And** the cache key remains `profile:{username}`
**And** the cache TTL is 1 hour when accessed by authenticated users
**And** subsequent requests use cached social accounts without additional API calls

## ADDED Requirements

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

## Cross-References

- Extends `web-user-interface` spec (user profile display)
- Extends `github-authentication` spec (API client capabilities)
