# Implementation Tasks

## Phase 1: Foundation - Task Tracking Infrastructure

### Task 1.1: Create task tracking service module

- [ ] Create `gitbrag/services/task_tracking.py`
- [ ] Implement `is_task_active(task_id: str) -> bool`
- [ ] Implement `start_task(task_id: str, metadata: dict) -> bool` using Redis SET NX
- [ ] Implement `complete_task(task_id: str) -> None`
- [ ] Implement `get_reported_user_active_tasks(reported_username: str) -> list[str]`
- [ ] Implement `can_start_reported_user_task(reported_username: str) -> bool` with rate limit check
- [ ] Add comprehensive docstrings and type hints
- [ ] Set appropriate Redis TTLs (300s) for auto-cleanup
- [ ] Note: Rate limiting is per reported GitHub username (the subject of the report), not per authenticated user

**Validation**: Unit tests verify all functions work correctly with Redis

**Dependencies**: None

### Task 1.2: Add task tracking configuration

- [ ] Add task tracking settings to `gitbrag/conf/settings.py`:
  - `TASK_TIMEOUT_SECONDS` (default: 300)
  - `MAX_REPORTED_USER_CONCURRENT_TASKS` (default: 1)
- [ ] Document settings in `docs/dev/settings.md`
- [ ] Add validation for settings values
- [ ] Note: Rate limiting is per reported GitHub username, not per authenticated user

**Validation**: Settings can be loaded and validated

**Dependencies**: None

### Task 1.3: Write unit tests for task tracking

- [ ] Create `tests/services/test_task_tracking.py`
- [ ] Test `start_task` succeeds for new task
- [ ] Test `start_task` fails for duplicate task (atomic operation)
- [ ] Test `is_task_active` returns correct status
- [ ] Test `complete_task` cleans up Redis keys
- [ ] Test `can_start_reported_user_task` enforces per-reported-user limits
- [ ] Test Redis TTL expiration (using fakeredis or real Redis)
- [ ] Test concurrent task registration (race conditions)
- [ ] Test different reported users can have concurrent tasks
- [ ] Test same reported user cannot have concurrent tasks

**Validation**: All tests pass with >90% coverage

**Dependencies**: Task 1.1

## Phase 2: Background Task Management

### Task 2.1: Create background task manager module

- [ ] Create `gitbrag/services/background_tasks.py`
- [ ] Implement `schedule_report_generation()` function
- [ ] Implement `generate_report_background()` function
- [ ] Add error handling with try/finally for task cleanup
- [ ] Add structured logging for task lifecycle events
- [ ] Import and use task tracking functions from Phase 1

**Validation**: Functions can be called and execute without errors

**Dependencies**: Task 1.1, 1.2

### Task 2.2: Add helper function for params hash generation

- [ ] Add `generate_params_hash()` to `gitbrag/services/reports.py`
- [ ] Function should create consistent hash from show_star_increase and other params
- [ ] Use same hash algorithm as `generate_cache_key()` for consistency
- [ ] Add docstring explaining hash purpose and format

**Validation**: Hash is consistent for same parameters, different for different parameters

**Dependencies**: None

### Task 2.3: Write unit tests for background task manager

- [ ] Create `tests/services/test_background_tasks.py`
- [ ] Test `schedule_report_generation` registers task and schedules background work
- [ ] Test `schedule_report_generation` returns False for duplicate tasks
- [ ] Test `schedule_report_generation` respects per-reported-user limits (same GitHub username)
- [ ] Test `schedule_report_generation` allows concurrent tasks for different reported users
- [ ] Test `generate_report_background` updates cache on success
- [ ] Test `generate_report_background` cleans up task on failure
- [ ] Test `generate_report_background` handles GitHub API errors gracefully

**Validation**: All tests pass with >85% coverage

**Dependencies**: Task 2.1, 2.2

## Phase 3: Request Handler Modifications

### Task 3.1: Update user_report handler to use background tasks

- [ ] Modify `gitbrag/www.py` - `user_report()` function
- [ ] Add `background_tasks: BackgroundTasks` parameter
- [ ] Implement cache state checking (age, staleness)
- [ ] Implement task active checking with `is_task_active()`
- [ ] Add logic to decide when to schedule background regeneration
- [ ] Call `schedule_report_generation()` when appropriate
- [ ] Pass task state to template context (is_regenerating, is_stale, cache_age)
- [ ] Remove synchronous report generation for authenticated users with cache

**Validation**: Handler compiles and runs without errors

**Dependencies**: Task 2.1, 2.2

### Task 3.2: Update get_or_generate_report to support background context

- [ ] Modify `gitbrag/services/reports.py` - `get_or_generate_report()`
- [ ] Simplify function to focus on cache retrieval and metadata
- [ ] Remove regeneration logic (moved to background task)
- [ ] Keep stale cache detection logic
- [ ] Return cache state information (age, staleness)

**Validation**: Function returns correct cache state

**Dependencies**: Task 3.1

### Task 3.3: Write integration tests for modified request handler

- [ ] Create `tests/integration/test_background_report_generation.py`
- [ ] Test authenticated user with stale cache → background task scheduled
- [ ] Test authenticated user with fresh cache → no background task
- [ ] Test unauthenticated user with stale cache → no background task
- [ ] Test authenticated user with no cache → background task scheduled
- [ ] Test force=true → always schedules background task
- [ ] Test concurrent requests → only one task scheduled (deduplication)
- [ ] Mock FastAPI BackgroundTasks to verify task scheduling

**Validation**: All integration tests pass

**Dependencies**: Task 3.1, 3.2

## Phase 4: Template and UI Updates

### Task 4.1: Update user_report template with regeneration indicators

- [ ] Modify `gitbrag/templates/user_report.html`
- [ ] Add "Regenerating" notice when `is_regenerating == True`
- [ ] Add "Login to Refresh" button when `is_stale and not authenticated`
- [ ] Add "Refresh Now" button when `is_stale and authenticated`
- [ ] Display cache age prominently when available
- [ ] Use conditional rendering with Jinja2 `{% if %}`

**Validation**: Template renders correctly for all states

**Dependencies**: Task 3.1

### Task 4.2: Add CSS for loading spinner and notices

- [ ] Create or update `gitbrag/static/css/reports.css`
- [ ] Add spinner animation CSS
- [ ] Add styling for regenerating notice (blue/info)
- [ ] Add styling for stale notice (yellow/warning)
- [ ] Ensure responsive design (mobile-friendly)

**Validation**: Styles display correctly in browser

**Dependencies**: Task 4.1

### Task 4.3: Add optional JavaScript for auto-refresh

- [ ] Create `gitbrag/static/js/report_refresh.js` (optional enhancement)
- [ ] Detect when `is_regenerating == true`
- [ ] Auto-refresh page every 5 seconds when regenerating
- [ ] Stop auto-refresh after 5 attempts or when regenerating completes
- [ ] Show countdown timer in UI
- [ ] Make feature opt-in or configurable

**Validation**: Auto-refresh works in browser without interfering with normal usage

**Dependencies**: Task 4.1, 4.2

**Note**: This task is optional and can be deferred

## Phase 5: Testing and Validation

### Task 5.1: Write E2E tests for complete user flows

- [ ] Create `tests/e2e/test_report_generation_flows.py`
- [ ] Test: User visits stale report → sees regenerating notice → refreshes → sees fresh data
- [ ] Test: Unauthenticated user sees stale cache with login prompt
- [ ] Test: Multiple users trigger same report → only one generation
- [ ] Test: User clicks "Refresh Now" → background task starts → cache updates
- [ ] Use real Redis instance (or docker-compose test environment)
- [ ] Verify cache keys and task keys are created and cleaned up

**Validation**: All E2E tests pass in test environment

**Dependencies**: Task 3.1, 3.2, 4.1

### Task 5.2: Perform load testing for deduplication

- [ ] Create `tests/performance/test_concurrent_requests.py`
- [ ] Simulate 50 concurrent requests to same report URL
- [ ] Verify only 1 background task is scheduled
- [ ] Measure deduplication rate (target: >95%)
- [ ] Verify all requests receive valid response
- [ ] Check Redis for task key count (should be 1)

**Validation**: Deduplication works under load

**Dependencies**: Task 3.1, 5.1

### Task 5.3: Manual testing and validation

- [ ] Start local development environment with docker-compose
- [ ] Test authenticated user flow with stale cache
- [ ] Test unauthenticated user flow with stale cache
- [ ] Test force refresh flow
- [ ] Verify Redis keys are created and cleaned up correctly
- [ ] Verify background tasks complete successfully
- [ ] Check logs for proper lifecycle events
- [ ] Test error scenarios (GitHub API errors, Redis connection loss)

**Validation**: All manual test scenarios work as expected

**Dependencies**: All previous tasks

## Phase 6: Documentation and Cleanup

### Task 6.1: Update developer documentation

- [ ] Update `docs/dev/web.md` with background task architecture
- [ ] Update `docs/dev/cache.md` with task tracking patterns
- [ ] Create new `docs/dev/background-tasks.md` (if needed)
- [ ] Document task tracking Redis key patterns
- [ ] Document per-user rate limiting behavior
- [ ] Add architecture diagrams (from design.md)

**Validation**: Documentation is clear and complete

**Dependencies**: Task 5.3

### Task 6.2: Update user-facing documentation

- [ ] Update `README.md` with improved performance notes
- [ ] Document new UI elements ("Regenerating" notice, refresh buttons)
- [ ] Explain cache behavior and auto-refresh for stale reports
- [ ] Add FAQ section for common questions

**Validation**: User documentation is accurate and helpful

**Dependencies**: Task 5.3

### Task 6.3: Add logging and monitoring

- [ ] Ensure all background task lifecycle events are logged
- [ ] Add structured logging with task_id, username, period
- [ ] Log task scheduling, start, completion, failure
- [ ] Log deduplication events
- [ ] Add metrics collection points (optional, for future monitoring)

**Validation**: Logs are useful for debugging and monitoring

**Dependencies**: Task 2.1, 3.1

### Task 6.4: Code review and refactoring

- [ ] Review all code for consistency with project conventions
- [ ] Ensure all functions have proper type hints
- [ ] Ensure all functions have docstrings
- [ ] Check for proper error handling
- [ ] Run linters (ruff, mypy)
- [ ] Fix any linting issues
- [ ] Ensure test coverage is >85% for new code

**Validation**: All linters pass, code review approved

**Dependencies**: All previous tasks

## Phase 7: Configuration and Documentation

### Task 7.1: Add configuration to environment

- [ ] Add environment variables to `.env.example`
- [ ] Document task tracking settings (TASK_TIMEOUT_SECONDS, MAX_REPORTED_USER_CONCURRENT_TASKS)
- [ ] Verify Redis configuration supports task tracking (persistence, memory limits)

**Validation**: Configuration is properly documented

**Dependencies**: Task 6.1

## Summary

**Total Tasks**: 20 main tasks

**Estimated Effort**:

- Phase 1: 2-3 hours
- Phase 2: 3-4 hours
- Phase 3: 4-5 hours
- Phase 4: 2-3 hours
- Phase 5: 4-5 hours
- Phase 6: 2-3 hours
- Phase 7: 1 hour

**Total**: 18-22 hours

**Parallelizable Work**:

- Tasks 1.1, 1.2, 2.2 can be done in parallel
- Tasks 4.1, 4.2 can be done in parallel with Phase 3
- Tasks 6.1, 6.2 can be done in parallel

**Critical Path**: Phase 1 → Phase 2 → Phase 3 → Phase 5

**Optional Tasks**:

- Task 4.3 (JavaScript auto-refresh)
