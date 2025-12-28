# github-authentication Specification

## Purpose
TBD - created by archiving change add-github-contribution-collection. Update Purpose after archive.
## Requirements
### Requirement: Support Personal Access Token Authentication

The system MUST support authentication to the GitHub API using Personal Access Tokens (PAT), enabling developers to securely access GitHub resources using their individual credentials.

#### Scenario: Authenticate with PAT from environment variable

**Given** the user has set the `GITHUB_TOKEN` environment variable with a valid PAT
**And** the user has set `GITHUB_AUTH_TYPE` to `pat` (or left it as default)
**When** the system initializes the GitHub client
**Then** the client authenticates successfully using the PAT
**And** all subsequent API calls use the authenticated session

#### Scenario: Authenticate with PAT from CLI option

**Given** the user has a valid PAT
**And** the user has not set the `GITHUB_TOKEN` environment variable
**When** the user runs a command with `--token <pat>` option
**Then** the system uses the provided token for authentication
**And** the token overrides any environment variable setting

#### Scenario: Handle invalid PAT

**Given** the user provides an invalid or expired PAT
**When** the system attempts to authenticate
**Then** the system raises a clear authentication error
**And** the error message explains the token is invalid or expired
**And** the error message provides guidance on obtaining a valid token

#### Scenario: Handle missing PAT when required

**Given** the authentication type is set to PAT
**And** no token is provided via environment variable or CLI option
**When** the system attempts to authenticate
**Then** the system raises a configuration error
**And** the error message explains which environment variable to set
**And** the error message references the documentation

### Requirement: Support GitHub App OAuth Authentication

The system MUST support authentication using GitHub App OAuth flow, where the app acts on behalf of the user to access their pull requests and repositories. **This requirement is modified to support both CLI and web-based OAuth flows.**

**Changes**: Extended OAuth flow to support persistent web-based authentication in addition to the existing CLI flow.

#### Scenario: Complete OAuth flow and obtain user access token (CLI)

**Given** the OAuth flow has been initiated for CLI usage
**And** the user authorizes the app in their browser
**When** GitHub redirects back with an authorization code to the local callback server
**Then** the system exchanges the code for a user access token
**And** the access token is returned to the CLI command
**And** the CLI command uses the token for its operations
**And** the token is not persisted (single-use flow)

#### Scenario: Complete OAuth flow and obtain user access token (Web)

**Given** the OAuth flow has been initiated for web usage
**And** the user authorizes the app in their browser
**When** GitHub redirects back with an authorization code to `/auth/callback`
**Then** the system exchanges the code for a user access token
**And** the access token is stored in the user's session
**And** the session is persisted in Redis
**And** all subsequent web requests use this session token
**And** the user is redirected to their originally requested page

### Requirement: Secure credential storage

The system MUST store all authentication credentials securely, preventing accidental exposure through logging, error messages, or serialization.

#### Scenario: Store PAT as secret string

**Given** a user provides a PAT through any input method
**When** the system stores the token in settings
**Then** the token is wrapped in Pydantic SecretStr
**And** the token cannot be accidentally printed or logged
**And** accessing the token requires explicit `.get_secret_value()` call

#### Scenario: Store GitHub App client secret as secret string

**Given** a user provides a GitHub App client secret
**When** the system stores the client secret in settings
**Then** the client secret is wrapped in Pydantic SecretStr
**And** the client secret cannot be accidentally printed or logged
**And** accessing the secret requires explicit `.get_secret_value()` call

#### Scenario: Store OAuth user access token securely

**Given** the system receives a user access token from OAuth flow
**When** the system stores the token for future use
**Then** the token is stored in a secure location (e.g., keyring or encrypted file)
**And** the token is wrapped in SecretStr when in memory
**And** the token cannot be accidentally exposed in logs or error messages

#### Scenario: Prevent credential exposure in logs

**Given** the system is logging authentication operations
**When** an authentication attempt occurs
**Then** no credentials appear in log messages
**And** log entries use placeholders like `***` for sensitive values
**And** only authentication success/failure status is logged

### Requirement: Provide rate limit information

The system MUST provide visibility into GitHub API rate limit status, helping users understand their API usage and avoid rate limit errors.

#### Scenario: Check rate limit status

**Given** an authenticated GitHub client
**When** the user requests rate limit information
**Then** the system returns current rate limit status
**And** the status includes remaining requests
**And** the status includes reset time
**And** the status includes total limit

#### Scenario: Handle rate limit exhaustion

**Given** an authenticated GitHub client
**And** the rate limit has been exceeded
**When** the system attempts an API call
**Then** the system raises a rate limit error
**And** the error message includes the reset time
**And** the error message suggests waiting until reset

### Requirement: Settings validation

The system MUST validate that authentication configuration is complete and consistent, preventing runtime errors from missing or conflicting settings.

#### Scenario: Validate PAT authentication settings

**Given** the authentication type is set to PAT
**When** the settings are validated
**Then** the system checks that a token is provided
**And** validation fails if the token is missing
**And** validation succeeds if the token is present

#### Scenario: Validate GitHub App OAuth authentication settings

**Given** the authentication type is set to GitHub App
**When** the settings are validated
**Then** the system checks that client ID is provided
**And** the system checks that client secret is provided
**And** validation fails if any required field is missing
**And** validation succeeds if all required fields are present

#### Scenario: Validate OAuth callback configuration

**Given** the authentication type is set to GitHub App
**When** the system prepares for OAuth flow
**Then** the system validates it can bind to a local port for callback
**And** the system validates the callback URL matches GitHub App settings
**And** validation fails if callback cannot be established
**And** the error message provides guidance on port configuration

#### Scenario: Default to PAT authentication

**Given** the user has not specified an authentication type
**When** the settings are loaded
**Then** the authentication type defaults to PAT
**And** the system validates PAT configuration requirements

### Requirement: Token encryption for stored credentials

The system MUST encrypt all OAuth access tokens before storing them in Redis to protect credentials even if the database is compromised.

#### Scenario: Encrypt token before storing in session

**Given** a user completes web OAuth flow
**And** the system receives an access token from GitHub
**When** the system stores the token in Redis
**Then** the token is encrypted using the cryptography library (Fernet symmetric encryption)
**And** the encryption key is derived from the session_secret_key setting
**And** only the encrypted blob is stored in Redis
**And** the plaintext token is never stored unencrypted

#### Scenario: Decrypt token when retrieving from session

**Given** a user has an active session with an encrypted OAuth token
**And** the user makes a request requiring GitHub API access
**When** the system retrieves the token from Redis
**Then** the system decrypts the token using the same encryption key
**And** the decrypted token is used to create a GitHubClient
**And** the plaintext token is only held in memory temporarily
**And** the token is wrapped in SecretStr for secure handling

#### Scenario: Handle decryption failure gracefully

**Given** a user has a session with an encrypted token
**And** the encryption key has changed (e.g., session_secret_key rotated)
**When** the system attempts to decrypt the token
**Then** the decryption fails
**And** the system clears the invalid session
**And** the system redirects to `/auth/login`
**And** the user is prompted to re-authenticate

#### Scenario: Use vetted cryptography library, not custom encryption

**Given** the system needs to encrypt OAuth tokens
**When** implementing encryption
**Then** the system uses the `cryptography` library (Fernet)
**And** the system does NOT implement custom encryption algorithms
**And** the system follows cryptography library best practices
**And** encryption keys are properly derived using PBKDF2 or similar

### Requirement: Web-based OAuth callback endpoint

The system MUST provide a persistent OAuth callback endpoint for web-based authentication, distinct from the CLI's temporary local server.

#### Scenario: Handle OAuth callback at web endpoint

**Given** a user is in the web OAuth flow
**And** the user has authorized the application on GitHub
**When** GitHub redirects to `/auth/callback?code=abc123&state=xyz789`
**Then** the system receives the callback at the web endpoint
**And** the system validates the state parameter matches the session
**And** the system exchanges the authorization code for an access token
**And** the callback endpoint remains available for future OAuth flows

#### Scenario: Reject callback with invalid parameters

**Given** a user attempts to access `/auth/callback` directly
**And** required parameters (code, state) are missing or invalid
**When** the callback endpoint processes the request
**Then** the system rejects the callback
**And** the system displays an error page
**And** no access token is stored

#### Scenario: Handle callback timeout gracefully

**Given** a user initiates OAuth flow but never completes authorization
**When** the user returns to the site later
**Then** the stored state parameter has expired (e.g., 15-minute TTL)
**And** attempting to use the callback fails gracefully
**And** the user is prompted to restart the OAuth flow

### Requirement: Session-based token storage for web

The system MUST store OAuth access tokens in server-side sessions for web users, maintaining authentication state across multiple requests.

#### Scenario: Store OAuth token in session after authentication

**Given** a user completes web OAuth flow
**And** the system receives an access token from GitHub
**When** the system stores the token
**Then** the token is stored in Redis with the session ID as key
**And** the session ID is stored in a secure cookie in the user's browser
**And** the token is wrapped in SecretStr for secure handling
**And** the session data includes token expiration time

#### Scenario: Retrieve token from session for API requests

**Given** a user has an active authenticated session
**And** the user makes a request to a protected endpoint
**When** the system needs to make a GitHub API call
**Then** the system retrieves the access token from the session
**And** the system creates a GitHubClient authenticated with the session token
**And** the GitHub API request uses the user's token and rate limit

#### Scenario: Handle missing session on protected endpoint

**Given** a user's session has expired or doesn't exist
**And** the user attempts to access a protected endpoint
**When** the system checks for authentication
**Then** the system detects no valid session exists
**And** the system redirects to the login page
**And** the original requested URL is preserved for post-login redirect

### Requirement: OAuth state parameter for CSRF protection

The system MUST use the OAuth state parameter to prevent CSRF attacks in the web OAuth flow.

#### Scenario: Generate and store state parameter on login

**Given** a user initiates web OAuth flow by clicking "Login with GitHub"
**When** the system redirects to GitHub's authorization page
**Then** the system generates a cryptographically secure random state parameter
**And** the system stores the state parameter in the user's session
**And** the state parameter is included in the authorization URL
**And** the state parameter is unique for each OAuth flow

#### Scenario: Validate state parameter on callback

**Given** a user has authorized the application
**And** GitHub redirects back to `/auth/callback?code=abc&state=xyz`
**When** the callback endpoint processes the request
**Then** the system retrieves the expected state from the user's session
**And** the system compares the callback state with the stored state
**And** the system only proceeds if the states match exactly
**And** the system rejects the callback if states don't match

#### Scenario: Prevent state reuse

**Given** a user completes OAuth flow with a specific state parameter
**When** the OAuth flow completes successfully
**Then** the system removes the state parameter from the session
**And** attempting to reuse the same state parameter fails
**And** each new OAuth flow requires a fresh state parameter

### Requirement: Separate OAuth implementations for CLI and web

The system MUST maintain separate OAuth flow implementations for CLI and web contexts to avoid breaking changes and maintain appropriate behavior for each environment.

#### Scenario: CLI uses GitHubOAuthFlow

**Given** a CLI command requires authentication with OAuth
**When** the CLI initiates the OAuth flow
**Then** the system uses the GitHubOAuthFlow class
**And** the flow starts a temporary local HTTP server
**And** the flow opens the user's browser to GitHub
**And** the flow waits for the callback and returns the token
**And** the local server shuts down after receiving the callback

#### Scenario: Web uses WebOAuthFlow

**Given** a web user initiates OAuth by visiting `/auth/login`
**When** the web application processes the login request
**Then** the system uses a WebOAuthFlow class (or equivalent FastAPI route logic)
**And** the flow uses the persistent `/auth/callback` endpoint
**And** the flow stores the token in the user's session
**And** the flow maintains session state across requests

#### Scenario: Both implementations use same credentials

**Given** GitHub App credentials are configured in settings
**When** either CLI or web initiates OAuth
**Then** both use the same GitHub App client ID and client secret
**And** both request minimal OAuth scopes (read:user for read-only public access)
**And** both follow the same OAuth protocol with GitHub
**And** neither requests write scopes or excessive permissions

### Requirement: Session expiration and renewal

The system MUST enforce session expiration policies and handle token renewal or re-authentication when sessions expire.

#### Scenario: Set session expiration on creation

**Given** a user completes web OAuth flow
**When** the system creates the session
**Then** the session is stored in Redis with a TTL of 24 hours
**And** the session data includes an expiration timestamp
**And** the session cookie includes Max-Age attribute

#### Scenario: Check session validity on each request

**Given** a user makes a request with a session cookie
**When** the system validates authentication
**Then** the system checks the session exists in Redis
**And** the system checks the session timestamp hasn't exceeded TTL
**And** the system marks the session as valid or invalid accordingly

#### Scenario: Handle expired session gracefully

**Given** a user's session expired 1 hour ago
**And** the user attempts to access a protected page
**When** the system validates authentication
**Then** the system detects the session is expired
**And** the system removes the expired session from Redis
**And** the system redirects to `/auth/login`
**And** the system displays a message indicating session expired
**And** the system preserves the original URL for post-login redirect

#### Scenario: Allow logout to explicitly end session

**Given** a user has an active session
**When** the user visits `/auth/logout`
**Then** the system immediately deletes the session from Redis
**And** the system clears the session cookie
**And** the user is redirected to the home page
**And** subsequent requests are unauthenticated

### Requirement: Minimal OAuth scope requests

The system MUST request only the minimal OAuth scopes necessary for functionality, reducing risk if tokens are exposed.

#### Scenario: Request read:user scope for web OAuth

**Given** a user initiates web OAuth flow
**When** the system builds the GitHub authorization URL
**Then** the system requests only the `read:user` scope
**And** the system does NOT request `public_repo` scope (more permissive than needed)
**And** the system does NOT request `repo` scope (includes private access)
**And** the system does NOT request any write scopes

#### Scenario: Verify read:user scope is sufficient for public data

**Given** a user has authenticated with read:user scope
**And** the user's OAuth token is stored in session
**When** the system fetches public pull requests for any user
**Then** the GitHub API allows the request
**And** public repositories and PRs are accessible
**And** no additional scopes are needed

#### Scenario: Minimize damage if token is exposed

**Given** an OAuth token with only read:user scope
**And** the token is somehow exposed (despite encryption)
**When** an attacker attempts to use the token
**Then** the attacker can only read public data
**And** the attacker cannot modify repositories
**And** the attacker cannot access private repositories
**And** the attacker cannot create or delete resources
**And** damage is minimized compared to broader scopes

