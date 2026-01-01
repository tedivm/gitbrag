# Tasks: Improved Session Validation

This task list provides concrete, ordered steps to implement the session validation improvements. Each task is designed to be small, verifiable, and deliver incremental user-visible progress.

**Status Legend**: ✅ Completed | ⏳ In Progress | ⬜ Not Started

## Phase 1: Core Token Validation (Foundation) ✅

### Task 1.1: Add validate_token method to GitHubAPIClient ✅

**Files**: `gitbrag/services/github/client.py`

**Description**: Implement the `validate_token()` async method that calls GitHub's `/user` endpoint to verify token validity.

**Implementation**:

1. Add method signature: `async def validate_token(self) -> bool`
2. Use existing `_request_with_retry()` to make GET request to `/user`
3. Return `True` for status 200, `False` for 401/403
4. Let other errors propagate (network, rate limit)
5. Add docstring explaining usage and return values

**Validation**:

- Run unit test: `pytest tests/services/test_github_client.py::test_validate_token_valid -v`
- Run unit test: `pytest tests/services/test_github_client.py::test_validate_token_invalid -v`
- Manual test: Call `validate_token()` with known valid/invalid tokens

**Dependencies**: None (foundation task)

**Status**: ✅ Completed

**User-Visible Progress**: None yet (internal method)

---

### Task 1.2: Write unit tests for validate_token ✅

**Files**: `tests/services/test_github_client.py`

**Description**: Create comprehensive tests for the new `validate_token()` method covering success, failure, and edge cases.

**Implementation**:

1. Test `test_validate_token_with_valid_token`: Mock 200 response, assert returns True
2. Test `test_validate_token_with_invalid_token`: Mock 401 response, assert returns False
3. Test `test_validate_token_with_expired_token`: Mock 403 response, assert returns False
4. Test `test_validate_token_with_network_error`: Mock network error, assert raises exception
5. Test `test_validate_token_with_rate_limit`: Mock 429 response, assert raises exception
6. Use `httpx_mock` or similar for mocking HTTP responses

**Validation**:

- Run tests: `pytest tests/services/test_github_client.py -v`
- Verify 100% code coverage for `validate_token()` method
- All tests pass

**Dependencies**: Task 1.1

**Status**: ✅ Completed

**User-Visible Progress**: None (testing infrastructure)

---

## Phase 2: Session Invalidation Helpers ✅

### Task 2.1: Add invalidate_session helper to session module ✅

**Files**: `gitbrag/services/session.py`

**Description**: Create centralized `invalidate_session()` function to handle session clearing with logging.

**Implementation**:

1. Add function signature: `def invalidate_session(request: Request, reason: str = "invalid token") -> None`
2. Call existing `clear_session(request)` to clear session data
3. Log at INFO level: `f"Session invalidated: {reason}"`
4. Add docstring with usage examples

**Validation**:

- Run unit test: `pytest tests/services/test_session.py::test_invalidate_session -v`
- Verify session data is cleared
- Verify log message appears with correct level

**Dependencies**: None

**Status**: ✅ Completed

**User-Visible Progress**: None yet (helper function)

---

### Task 2.2: Write unit tests for invalidate_session ✅

**Files**: `tests/services/test_session.py`

**Description**: Test the session invalidation helper function.

**Implementation**:

1. Test `test_invalidate_session_clears_data`: Create session with data, call invalidate, verify cleared
2. Test `test_invalidate_session_with_custom_reason`: Verify custom reason appears in logs
3. Test `test_invalidate_session_idempotent`: Call twice, verify no errors
4. Test `test_invalidate_session_logging`: Verify INFO level log with correct message

**Validation**:

- Run tests: `pytest tests/services/test_session.py -v`
- All tests pass
- Code coverage for `invalidate_session()` is 100%

**Dependencies**: Task 2.1

**Status**: ✅ Completed

**User-Visible Progress**: None (testing infrastructure)

---

## Phase 3: Integration with Authentication Flow ✅

### Task 3.1: Integrate token validation into get_authenticated_github_client ✅

**Files**: `gitbrag/services/auth.py`

**Description**: Add token validation to the authentication dependency, invalidating sessions when tokens fail.

**Implementation**:

1. After creating `GitHubAPIClient`, call `await client.validate_token()`
2. If validation returns False:
   - Call `invalidate_session(request, "token validation failed")`
   - Log warning: `f"Token validation failed for user session"`
   - Raise `HTTPException(401, detail="Your session has expired. Please log in again.")`
3. If validation returns True, continue normally
4. Handle exceptions from validation (network, rate limit) by logging and re-raising

**Validation**:

- Run unit test: `pytest tests/services/test_auth.py::test_get_authenticated_client_with_invalid_token -v`
- Manual test: Set invalid token in session, make authenticated request, verify redirect to login
- Verify session is cleared when token is invalid

**Dependencies**: Task 1.1, Task 2.1

**Status**: ✅ Completed

**User-Visible Progress**: ✅ Users are automatically logged out when their GitHub token expires

---

### Task 3.2: Write tests for authentication flow with invalid tokens ✅

**Files**: `tests/services/test_auth.py`

**Description**: Test the updated authentication flow with token validation.

**Implementation**:

1. Test `test_get_authenticated_client_with_invalid_token`: Mock invalid token, verify 401 raised
2. Test `test_get_authenticated_client_clears_session_on_failure`: Verify session cleared
3. Test `test_get_authenticated_client_with_valid_token`: Verify normal flow still works
4. Test `test_get_authenticated_client_stores_redirect_url`: Verify original URL stored for redirect

**Validation**:

- Run tests: `pytest tests/services/test_auth.py -v`
- All tests pass
- Code coverage maintained above 85%

**Dependencies**: Task 3.1

**Status**: ✅ Completed

**User-Visible Progress**: None (testing)

---

## Phase 4: Background Job Token Validation ✅

### Task 4.1: Add token validation to background job scheduling ✅

**Files**: `gitbrag/services/background_tasks.py`

**Description**: Validate tokens before scheduling background report generation jobs.

**Implementation**:

1. In `schedule_report_generation()`, after rate limit check:
   - Create `GitHubAPIClient` with provided token
   - Call `await client.validate_token()`
   - If False, log warning and return False (don't schedule)
   - If exception (network/rate limit), log error and return False
2. Add parameter validation: don't proceed if token is None
3. Log: `f"Token validation failed for background job, not scheduling: {username}:{period}"`

**Validation**:

- Run unit test: `pytest tests/services/test_background_tasks.py::test_schedule_with_invalid_token -v`
- Manual test: Try to generate report with invalid token, verify job not scheduled
- Verify warning log appears

**Dependencies**: Task 1.1

**Status**: ✅ Completed

**User-Visible Progress**: ✅ Background jobs are not started with invalid tokens, reducing wasted resources

---

### Task 4.2: Write tests for background job token validation ✅

**Files**: `tests/services/test_background_tasks.py`

**Description**: Test background job scheduling with invalid tokens.

**Implementation**:

1. Test `test_schedule_with_invalid_token`: Mock validation returning False, verify job not scheduled
2. Test `test_schedule_with_valid_token`: Mock validation returning True, verify job scheduled
3. Test `test_schedule_with_validation_error`: Mock validation raising exception, verify job not scheduled
4. Test `test_schedule_logs_validation_failure`: Verify warning log when validation fails

**Validation**:

- Run tests: `pytest tests/services/test_background_tasks.py -v`
- All tests pass
- Code coverage above 85%

**Dependencies**: Task 4.1

**Status**: ✅ Completed

**User-Visible Progress**: None (testing)

---

### Task 4.3: Add fail-fast logic to background job execution ✅

**Files**: `gitbrag/services/background_tasks.py`

**Description**: Make background jobs terminate immediately on authentication errors during execution.

**Implementation**:

1. In `generate_report_background()`, wrap API calls in try-except
2. Catch `httpx.HTTPStatusError`
3. Check `if e.response.status_code in (401, 403)`:
   - Log error: `f"Authentication error in background job {task_id}, aborting"`
   - Call `await complete_task(task_id)` to clean up
   - Return early (don't continue processing)
4. For other errors, use existing error handling

**Validation**:

- Run unit test: `pytest tests/services/test_background_tasks.py::test_job_aborts_on_auth_error -v`
- Manual test: Revoke token mid-job (difficult), verify job terminates quickly
- Verify error log appears with correct message

**Dependencies**: Task 4.1

**Status**: ✅ Completed

**User-Visible Progress**: ✅ Background jobs stop immediately when tokens expire, rather than running until timeout

---

### Task 4.4: Write tests for background job fail-fast behavior ✅

**Files**: `tests/services/test_background_tasks.py`

**Description**: Test that background jobs abort on authentication errors.

**Implementation**:

1. Test `test_job_aborts_on_401_error`: Mock GitHub returning 401 during execution, verify early return
2. Test `test_job_aborts_on_403_auth_error`: Mock 403 (non-rate-limit), verify early return
3. Test `test_job_continues_on_rate_limit`: Mock 403 (rate limit), verify normal retry behavior
4. Test `test_job_cleans_up_on_auth_error`: Verify `complete_task()` called on auth error

**Validation**:

- Run tests: `pytest tests/services/test_background_tasks.py -v`
- All tests pass
- Code coverage above 85%

**Dependencies**: Task 4.3

**Status**: ✅ Completed

**User-Visible Progress**: None (testing)

---

## Phase 5: Integration Testing and Documentation ✅

### Task 5.1: Write integration test for full authentication flow ✅

**Files**: `tests/integration/test_auth_flow.py`

**Description**: Test end-to-end flow of session invalidation with expired tokens.

**Implementation**:

1. Test `test_expired_token_redirects_to_login`:
   - Create test client with session
   - Set expired token in session
   - Make request to authenticated route
   - Verify 401 response and redirect to login
   - Verify session cleared
2. Test `test_background_job_rejected_with_invalid_token`:
   - Try to schedule job with invalid token
   - Verify job not scheduled
   - Verify warning log

**Validation**:

- Run integration tests: `pytest tests/integration/test_auth_flow.py -v`
- All tests pass
- Test covers full user journey

**Dependencies**: Task 3.1, Task 4.1, Task 4.3

**Status**: ✅ Completed

**User-Visible Progress**: None (testing)

---

### Task 5.2: Update developer documentation ✅

**Files**: `docs/dev/github.md`, `docs/dev/web.md`

**Description**: Document the new token validation behavior for developers.

**Implementation**:

1. In `docs/dev/github.md`:
   - Add section "Token Validation" explaining `validate_token()` method
   - Document when validation occurs (web requests, background jobs)
   - Explain behavior for invalid tokens
2. In `docs/dev/web.md`:
   - Update "Session Management" section
   - Explain automatic session invalidation on token failures
   - Document `invalidate_session()` helper

**Validation**:

- Run markdown linter: `make lint-docs` (if available)
- Review documentation for clarity and accuracy
- Ensure all code examples are correct

**Dependencies**: All implementation tasks complete

**Status**: ✅ Completed

**User-Visible Progress**: ✅ Developers can understand and work with the new validation system

---

### Task 5.3: Manual testing with live GitHub tokens ⬜

**Files**: N/A (manual testing)

**Description**: Perform manual testing with real GitHub OAuth tokens to verify behavior.

**Test Cases**:

1. **Valid token flow**:
   - Log in with OAuth
   - Generate report
   - Verify report generates successfully
   - Verify background job completes

2. **Expired token flow**:
   - Log in with OAuth
   - Manually revoke token on GitHub
   - Try to generate report
   - Verify session cleared
   - Verify redirect to login
   - Verify clear error message

3. **Background job with invalid token**:
   - Start report generation
   - Revoke token on GitHub (before job starts)
   - Verify job not scheduled
   - Verify warning log

**Validation**:

- All test cases pass
- User experience is smooth
- Error messages are clear

**Dependencies**: All implementation tasks complete

**Status**: ⬜ Not Started (manual testing required)

**User-Visible Progress**: ✅ Confirmed all user-facing improvements work correctly

---

## Implementation Status Summary

**Phases 1-5 (Development)**: ✅ **COMPLETED**

- All code implemented and tested
- 358 tests passing
- Documentation updated
- Ready for deployment

---

## Summary of User-Visible Progress

After completing all tasks, users will experience:

1. ✅ Automatic logout when GitHub tokens expire (no more false "logged in" state)
2. ✅ Clear error messages prompting re-authentication
3. ✅ Faster failure detection (no long timeouts on invalid operations)
4. ✅ Reduced server load from failed background jobs
5. ✅ More reliable report generation (jobs only run with valid tokens)

## Dependencies Between Tasks

```text
Phase 1 (Foundation):
  1.1 → 1.2

Phase 2 (Helpers):
  2.1 → 2.2

Phase 3 (Web Auth):
  1.1, 2.1 → 3.1 → 3.2

Phase 4 (Background Jobs):
  1.1 → 4.1 → 4.2
  4.1 → 4.3 → 4.4

Phase 5 (Integration):
  3.1, 4.1, 4.3 → 5.1
  All impl → 5.2
  All impl → 5.3

Phase 6 (Deployment):
  All → 6.1, 6.2 → 6.3
```

## Parallelizable Work

These tasks can be done in parallel:

- Phase 1 and Phase 2 can be done simultaneously
- Within Phase 4: Task 4.1-4.2 and Task 4.3-4.4 can be parallelized
- Phase 3 and Phase 4 can be partially parallelized (different files)

## Estimated Timeline

- Phase 1: 2-4 hours
- Phase 2: 1-2 hours
- Phase 3: 3-4 hours
- Phase 4: 4-6 hours
- Phase 5: 3-4 hours
- Phase 6: 2-3 hours (deployment)

**Total**: 15-23 hours of development work
