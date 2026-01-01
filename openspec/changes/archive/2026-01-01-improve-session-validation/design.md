# Design: Improved Session Validation

## Overview

This design introduces proactive token validation to detect expired or invalid GitHub OAuth tokens early, preventing cascading failures and improving user experience. The approach centers on three key mechanisms:

1. **Token Validation API**: A new method to verify token validity with GitHub
2. **Automatic Session Invalidation**: Clear sessions when tokens fail validation
3. **Fail-Fast Background Jobs**: Validate tokens before starting expensive operations

## Architecture Components

### 1. Token Validation Layer

Add a new `validate_token()` method to `GitHubAPIClient` that performs a lightweight API call to GitHub's `/user` endpoint to verify token validity.

**Implementation Location**: `gitbrag/services/github/client.py`

**Method Signature**:

```python
async def validate_token(self) -> bool:
    """Validate that the current token is valid with GitHub API.

    Returns:
        True if token is valid, False if expired/invalid
    """
```

**Behavior**:

- Makes a GET request to `https://api.github.com/user`
- Returns `True` for 200 status
- Returns `False` for 401/403 status (expired/invalid token)
- Raises exceptions for other errors (network, rate limit)
- Uses existing retry logic from `_request_with_retry()`

**Why `/user` endpoint?**

- Minimal response payload (lightweight)
- Requires authentication (fails immediately for invalid tokens)
- Standard endpoint available to all OAuth tokens
- No side effects (read-only operation)

### 2. Session Validation Integration

Integrate token validation into the authentication flow to automatically detect and handle invalid sessions.

**Implementation Locations**:

- `gitbrag/services/auth.py` - `get_authenticated_github_client()`
- `gitbrag/services/session.py` - Add `invalidate_session()`

**Flow**:


1. User makes request to authenticated route
2. get_authenticated_github_client() called
3. Check is_authenticated() (session cookie exists)
4. Decrypt token from session
5. Create GitHubAPIClient with token
6. Call validate_token() to verify with GitHub
7a. If valid: return client, proceed with request
7b. If invalid:
    - Call invalidate_session(request)
    - Log warning about expired token
    - Raise 401 HTTPException with redirect to /auth/login


**Design Decision: When to Validate**

We validate tokens at the boundary of authenticated operations:

- **For Web Requests**: In `get_authenticated_github_client()` dependency
- **For Background Jobs**: Before starting `generate_report_background()`

This approach provides:

- Early detection before expensive operations
- Centralized validation logic
- Minimal performance impact (single API call per request/job)

**Performance Considerations**:

- Token validation adds one API call per authenticated request
- Caching could reduce calls, but risks serving with invalid tokens
- Decision: No caching for validation (favor correctness over performance)
- The `/user` endpoint is fast (~50-100ms) and acceptable overhead

### 3. Background Job Token Validation

Background jobs must validate tokens before starting work to avoid wasting resources on operations that will fail.

**Implementation Location**: `gitbrag/services/background_tasks.py`

**Modified Flow**:


1. schedule_report_generation() called
2. Check task not already active
3. Check rate limits
4. **NEW: Validate token with GitHub**
5a. If invalid:
    - Log warning
    - Return False (don't schedule)
    - Clear any cached auth state
5b. If valid:
    - Register task start
    - Schedule background_task
    - Return True


**Fail-Fast During Execution**:

If a token becomes invalid mid-execution (unlikely but possible):


1. generate_report_background() catches HTTPStatusError
2. Check if status_code == 401 or 403
3. If auth error:
    - Log error with task_id
    - Call complete_task() with error status
    - Return early (don't retry)
4. If other error:
    - Log error
    - Implement existing retry/error handling


### 4. Session Invalidation Helper

Add a helper function to centralize session clearing logic.

**Implementation**: `gitbrag/services/session.py`

```python
def invalidate_session(request: Request) -> None:
    """Invalidate user session and clear all session data.

    Used when token validation fails or explicit logout requested.

    Args:
        request: FastAPI request object
    """
    clear_session(request)
    logger.info("Session invalidated due to invalid token")
```

This provides:

- Centralized invalidation logic
- Consistent logging
- Easy to test and maintain
- Can be extended for additional cleanup in future

## Error Handling Strategy

### User-Facing Errors

When token validation fails during a web request:

1. Clear session immediately
2. Raise `HTTPException(401, "Your session has expired. Please log in again.")`
3. Let existing exception handlers redirect to `/auth/login`
4. Store original URL for post-login redirect

### Background Job Errors

When token validation fails during background job:

1. Log clear error: `"Token invalid for task {task_id}, aborting report generation"`
2. Mark task as failed in task tracking
3. Return immediately (no retry)
4. Do not raise exception (background jobs should fail gracefully)

### Logging

All validation failures should log at WARNING level:

```python
logger.warning(f"Token validation failed for user session: {session_id}")
```

Include context:

- Session ID (for web requests)
- Task ID (for background jobs)
- HTTP status from GitHub (401, 403, etc.)
- Operation attempted (e.g., "report generation", "PR list")

## Migration Strategy

This is a backward-compatible change with no breaking API changes:

1. Add `validate_token()` method to `GitHubAPIClient`
2. Add `invalidate_session()` helper to `session.py`
3. Integrate validation into `get_authenticated_github_client()`
4. Update background job flow to validate before starting
5. Update error handling in background jobs to fail fast on auth errors

Existing behavior preserved:

- OAuth flow unchanged
- Token encryption unchanged
- Session middleware unchanged
- UI unchanged (behavior only)

## Testing Strategy

### Unit Tests

1. `test_services/test_github_client.py`:
   - Test `validate_token()` with valid token (200 response)
   - Test `validate_token()` with invalid token (401 response)
   - Test `validate_token()` with expired token (403 response)
   - Test `validate_token()` with network errors

2. `test_services/test_session.py`:
   - Test `invalidate_session()` clears session data
   - Test `invalidate_session()` logging

3. `test_services/test_auth.py`:
   - Test `get_authenticated_github_client()` with invalid token
   - Test session invalidation on token failure
   - Test redirect behavior after invalidation

4. `test_services/test_background_tasks.py`:
   - Test job scheduling rejected with invalid token
   - Test job fails fast on mid-execution auth error
   - Test task cleanup on auth failure

### Integration Tests

1. `test_integration/test_auth_flow.py`:
   - Test full request flow with expired token
   - Test background job with expired token
   - Test session invalidation triggers re-authentication

## Performance Impact

**Additional API Calls**:

- One `/user` call per authenticated web request
- One `/user` call per background job start

**Latency**:

- ~50-100ms per validation call (typical GitHub API response)
- Acceptable overhead for correctness guarantee

**Resource Savings**:

- Prevent failed background jobs from consuming resources
- Reduce spurious API calls with invalid tokens
- Fewer error logs and monitoring alerts

**Net Impact**: Positive (small overhead, large waste reduction)

## Security Considerations

**Token Exposure**:

- Validation doesn't expose tokens (sent in Authorization header only)
- Failed validation immediately clears token from session
- All token handling uses SecretStr

**Session Fixation**:

- Clearing session on token failure prevents session fixation
- User must re-authenticate after token expires

**Logging**:

- Never log token values
- Log session IDs and task IDs only
- Log validation failures at WARNING level

## Alternative Approaches Considered

### 1. Token Expiration Tracking

**Approach**: Store token expiration time from OAuth response, check before operations.

**Rejected Because**:

- OAuth response doesn't include expiration time
- Would require estimating expiration (unreliable)
- Doesn't handle manual token revocation
- Validation with GitHub is authoritative source

### 2. Validation Caching

**Approach**: Cache validation results for N minutes to reduce API calls.

**Rejected Because**:

- Risk of serving requests with invalid tokens during cache period
- Adds complexity without significant performance benefit
- `/user` endpoint is fast enough for inline validation
- Favor correctness over performance for authentication

### 3. Background Validation

**Approach**: Validate tokens in background, mark sessions as invalid asynchronously.

**Rejected Because**:

- Adds complexity with worker process
- Doesn't prevent initial request with invalid token
- Synchronous validation is fast enough
- Fails to achieve "fail fast" goal

## Future Enhancements

Potential future improvements outside this change:

1. **Token Refresh**: Implement token refresh flow if GitHub adds support
2. **Validation Metrics**: Track validation failure rates for monitoring
3. **Predictive Invalidation**: Warn users before tokens expire
4. **Rate Limit Integration**: Skip validation if rate limited (accept risk)
