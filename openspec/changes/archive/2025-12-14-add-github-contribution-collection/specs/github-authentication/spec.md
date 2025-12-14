# Spec: GitHub Authentication

## ADDED Requirements

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

The system MUST support authentication using GitHub App OAuth flow, where the app acts on behalf of the user to access their pull requests and repositories.

#### Scenario: Initiate OAuth flow for GitHub App

**Given** the user has set `GITHUB_AUTH_TYPE` to `github_app`
**And** the user has set `GITHUB_APP_CLIENT_ID` with the app's client ID
**And** the user has set `GITHUB_APP_CLIENT_SECRET` with the app's client secret
**When** the user runs a command requiring authentication
**And** no valid user access token exists
**Then** the system initiates the OAuth authorization flow
**And** the system opens the user's browser to GitHub's authorization page
**And** the system starts a local callback server to receive the authorization code

#### Scenario: Complete OAuth flow and obtain user access token

**Given** the OAuth flow has been initiated
**And** the user authorizes the app in their browser
**When** GitHub redirects back with an authorization code
**Then** the system exchanges the code for a user access token
**And** the access token is stored securely for future use
**And** all subsequent API calls use this user access token
**And** the token allows access to the user's data as if the user made the request

#### Scenario: Use cached user access token

**Given** the user has previously completed OAuth flow
**And** a valid user access token is stored
**When** the user runs a command requiring authentication
**Then** the system uses the cached access token
**And** no browser interaction is required
**And** the token is validated before use

#### Scenario: Handle expired OAuth token

**Given** the user has a stored access token
**And** the token has expired
**When** the system attempts to use the token
**Then** the system detects the token is invalid
**And** the system initiates a new OAuth flow
**And** the user is prompted to reauthorize the app

#### Scenario: Handle missing GitHub App OAuth credentials

**Given** the authentication type is set to GitHub App
**And** one or more required credentials are missing (client ID or secret)
**When** the system attempts to validate settings
**Then** the system raises a configuration error
**And** the error message lists all missing credentials
**And** the error message explains where to find these credentials in GitHub App settings

#### Scenario: Handle user denying OAuth authorization

**Given** the OAuth flow has been initiated
**When** the user denies authorization in their browser
**Then** the system receives the denial callback
**And** the system raises an authorization denied error
**And** the error message explains the user must authorize the app to proceed
**And** the system provides instructions for trying again

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
