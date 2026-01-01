# improve-session-validation

## Problem Statement

Currently, when a user's GitHub OAuth token expires, the system fails to detect this condition promptly, leading to several user experience and system reliability issues:

1. **Misleading Authentication State**: The UI shows users as "logged in" even though their token no longer works with the GitHub API, creating a confusing experience where authenticated actions fail.

2. **Silent Background Job Failures**: Background jobs for automatic report regeneration start executing with invalid tokens, failing slowly without proper error handling, potentially running until timeout without producing useful results.

3. **Poor Error Feedback**: When tokens fail during operations, users receive generic error messages rather than clear guidance to re-authenticate.

4. **Resource Waste**: Invalid background jobs consume system resources (CPU, memory, API calls to GitHub that return 401) unnecessarily before eventually failing.

5. **Cascading Failures**: A single expired token can trigger multiple failed background jobs as the system attempts to regenerate reports, leading to degraded system performance.

## Goals

This change aims to make session management more resilient and user-friendly by:

1. **Proactive Token Validation**: Validate GitHub tokens before initiating expensive operations (especially background jobs) to fail fast and provide clear feedback.

2. **Accurate Session State**: Ensure the UI accurately reflects authentication status by automatically invalidating sessions when tokens are detected as expired or invalid.

3. **Fail-Fast Background Jobs**: Stop background job execution immediately upon detecting invalid tokens, rather than allowing them to run until timeout.

4. **Clear User Feedback**: Provide explicit guidance to users when their session expires, prompting re-authentication with clear messaging.

5. **Improved System Reliability**: Reduce wasted resources and prevent cascading failures from invalid token operations.

## User Impact

**For End Users:**

- More accurate authentication status in the UI (no false "logged in" state)
- Faster failure detection with clearer error messages
- Automatic redirect to re-authentication when tokens expire
- Background report generation won't waste time on invalid tokens

**For System Operations:**

- Reduced resource consumption from failed background jobs
- Fewer spurious error logs from token validation failures
- Better system performance during high load
- Clearer observability into authentication-related issues

## Scope

This change encompasses three primary capabilities:

1. **Proactive Token Validation** (`specs/proactive-token-validation/`)
   - Add token validation check before starting background jobs
   - Validate tokens early in request processing for authenticated routes
   - Add GitHub API `/user` endpoint call to verify token validity

2. **Automatic Session Invalidation** (`specs/automatic-session-invalidation/`)
   - Clear session data when token validation fails
   - Update `is_authenticated()` to reflect actual token validity
   - Handle 401 responses from GitHub API as session invalidation triggers

3. **Background Job Resilience** (`specs/background-job-resilience/`)
   - Add token validation before starting report generation
   - Implement early termination on authentication errors during execution
   - Improve error logging and cleanup for failed jobs

## Non-Goals

- Automatic token refresh (OAuth tokens don't support refresh in current flow)
- Token expiration prediction or warnings before expiration
- Changes to OAuth flow or token acquisition process
- Changes to UI design or layout (only behavioral changes)
- Handling network errors unrelated to authentication

## Dependencies

- Extends `github-authentication` spec
- Modifies behavior in `web-user-interface` (session management)
- Updates `gitbrag.services.session` module
- Updates `gitbrag.services.auth` module
- Updates `gitbrag.services.background_tasks` module
- Updates `gitbrag.services.github.client` module

## Affected Specs

This change modifies requirements in:

- `github-authentication` - Adds token validation requirement
- `web-user-interface` - Updates session management behavior

## Related Changes

None (this is a new change)
