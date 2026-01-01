# background-job-resilience Specification

## MODIFIED Requirements

### Requirement: Background jobs must validate tokens before starting

Background report generation jobs MUST validate GitHub tokens before initiating work to prevent wasting resources on operations that will fail due to authentication errors.

**Changes**: Updates background task scheduling to include token validation as a precondition.

**Rationale**: Prevents resource waste from background jobs running with invalid tokens until timeout.

#### Scenario: Reject background job scheduling with invalid token

**Given** a user has a session with an invalid or expired GitHub token
**And** a background job is about to be scheduled for report generation
**When** `schedule_report_generation()` is called
**Then** the system validates the token with GitHub before scheduling
**And** if the token is invalid, the job is not scheduled
**And** the function returns False to indicate scheduling was rejected
**And** a warning is logged: "Token invalid for user, not scheduling background job"

#### Scenario: Schedule background job only after successful token validation

**Given** a user has a session with a valid GitHub token
**And** a background job is about to be scheduled
**When** `schedule_report_generation()` is called
**Then** the system validates the token with GitHub
**And** if the token is valid, rate limiting is checked
**And** if rate limits allow, the task is registered and scheduled
**And** the function returns True to indicate successful scheduling

#### Scenario: Token validation happens before rate limit checks

**Given** a background job is about to be scheduled
**When** `schedule_report_generation()` performs pre-scheduling checks
**Then** token validation happens first
**And** if token is invalid, no rate limit checks are performed
**And** no task registration occurs
**And** system resources for rate limiting are not consumed

**Rationale**: Fail as early as possible in the scheduling pipeline to avoid unnecessary work.

### Requirement: Background jobs must fail fast on authentication errors during execution

If a token becomes invalid during background job execution (unlikely but possible), the job MUST terminate immediately rather than running until timeout.

**Changes**: Adds explicit authentication error handling to background job execution.

**Rationale**: Minimizes resource waste and provides faster failure detection.

#### Scenario: Abort background job on 401 error during execution

**Given** a background job is executing report generation
**And** the job makes an API call to GitHub
**When** GitHub returns a 401 status code
**Then** the job catches the HTTPStatusError
**And** the job checks if status_code == 401
**And** if true, the job logs "Authentication error in background job {task_id}, aborting"
**And** the job calls `complete_task(task_id, error=True)`
**And** the job returns immediately without further API calls

#### Scenario: Abort background job on 403 error indicating invalid token

**Given** a background job is executing report generation
**And** the job makes an API call to GitHub
**When** GitHub returns a 403 status code with rate limit headers showing it's NOT a rate limit
**Then** the job treats this as an authentication error
**And** the job logs "Authorization error in background job {task_id}, aborting"
**And** the job calls `complete_task(task_id, error=True)`
**And** the job returns immediately without retry

**Note**: 403 can indicate either rate limiting or authorization errors. The job must check `X-RateLimit-Remaining` header to distinguish.

#### Scenario: Continue normal error handling for non-auth errors

**Given** a background job is executing report generation
**And** the job encounters a network error or 500 error
**When** the error is caught
**Then** the job checks if it's an authentication error (401/403)
**And** if it's NOT an authentication error, normal error handling continues
**And** the job may retry according to existing retry logic
**And** the job follows normal timeout behavior

#### Scenario: Clean up task tracking on authentication failure

**Given** a background job encounters an authentication error
**When** the job terminates early
**Then** the job calls `complete_task(task_id)` to clear task tracking
**And** the task is marked as completed (failed) in the tracking system
**And** rate limit tracking for the reported user is decremented
**And** future jobs for the same user can be scheduled

**Rationale**: Proper cleanup ensures the system doesn't get stuck with stale task state.

## ADDED Requirements

### Requirement: Background job logging for authentication failures

Background jobs MUST log authentication failures with clear context to aid debugging and monitoring.

**Rationale**: Clear logs help operators identify authentication issues and distinguish them from other job failures.

#### Scenario: Log warning when background job rejected due to invalid token

**Given** a background job is about to be scheduled
**And** token validation fails
**When** the job scheduling is rejected
**Then** a log entry is created at WARNING level
**And** the log message includes the username (subject of report)
**And** the log message includes the task parameters (period, params_hash)
**And** the log message indicates "Token validation failed, not scheduling job"

#### Scenario: Log error when background job aborts due to authentication error

**Given** a background job is executing and encounters a 401 error
**When** the job terminates early
**Then** a log entry is created at ERROR level
**And** the log message includes the task_id
**And** the log message includes the HTTP status code (401 or 403)
**And** the log message indicates "Background job aborted due to authentication error"

#### Scenario: Distinguish authentication errors from rate limit errors in logs

**Given** a background job encounters a 403 error
**When** the error is logged
**Then** if `X-RateLimit-Remaining` is "0", the log indicates "Rate limit exceeded"
**And** if `X-RateLimit-Remaining` is not "0", the log indicates "Authorization error"
**And** operators can distinguish between rate limiting and auth failures

### Requirement: Token validation does not block background job queue

Token validation MUST be fast enough to not significantly impact background job scheduling throughput.

**Rationale**: The background job queue should remain responsive even with validation overhead.

#### Scenario: Token validation completes within reasonable timeout

**Given** a background job is being scheduled
**When** token validation is performed
**Then** the validation completes within 5 seconds
**And** if validation times out, it's treated as a temporary failure
**And** the job is not scheduled if validation times out
**And** a log entry indicates "Token validation timeout"

#### Scenario: Token validation failures do not prevent other users' jobs

**Given** User A has an invalid token and tries to schedule a job
**And** User B has a valid token and tries to schedule a job
**When** both jobs are processed
**Then** User A's job is rejected quickly due to invalid token
**And** User B's job is scheduled successfully
**And** User A's validation failure does not delay User B's job

#### Scenario: Multiple background jobs can validate tokens concurrently

**Given** multiple background jobs are being scheduled simultaneously
**When** each job performs token validation
**Then** validations happen concurrently without blocking each other
**And** the async nature of validation allows parallel execution
**And** system throughput is not significantly impacted
