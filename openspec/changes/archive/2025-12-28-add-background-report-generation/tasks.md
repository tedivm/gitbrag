# Implementation Tasks

## Phase 1: Foundation - Task Tracking Infrastructure

### Task 1.1: Create task tracking service module

- [x] Create `gitbrag/services/task_tracking.py`
- [x] Implement `is_task_active(task_id: str) -> bool`
- [x] Implement `start_task(task_id: str, metadata: dict) -> bool` using Redis SET NX
- [x] Implement `complete_task(task_id: str) -> None`
- [x] Implement `get_reported_user_active_tasks(reported_username: str) -> list[str]`
- [x] Implement `can_start_reported_user_task(reported_username: str) -> bool` with rate limit check
- [x] Add comprehensive docstrings and type hints
- [x] Set appropriate Redis TTLs (300s) for auto-cleanup
- [x] Note: Rate limiting is per reported GitHub username (the subject of the report), not per authenticated user

**Validation**: Unit tests verify all functions work correctly with Redis

**Dependencies**: None

### Task 1.2: Add task tracking configuration

- [x] Add task tracking settings to `gitbrag/conf/settings.py`:
  - `TASK_TIMEOUT_SECONDS` (default: 300)
  - `MAX_REPORTED_USER_CONCURRENT_TASKS` (default: 1)
- [x] Document settings in `docs/dev/settings.md`
- [x] Add validation for settings values
- [x] Note: Rate limiting is per reported GitHub username, not per authenticated user

**Validation**: Settings can be loaded and validated

**Dependencies**: None

### Task 1.3: Write unit tests for task tracking

- [x] Create `tests/services/test_task_tracking.py`
- [x] Test `start_task` succeeds for new task
- [x] Test `start_task` fails for duplicate task (atomic operation)
- [x] Test `is_task_active` returns correct status
- [x] Test `complete_task` cleans up Redis keys
- [x] Test `can_start_reported_user_task` enforces per-reported-user limits
- [x] Test Redis TTL expiration (using fakeredis or real Redis)
- [x] Test concurrent task registration (race conditions)
- [x] Test different reported users can have concurrent tasks
- [x] Test same reported user cannot have concurrent tasks

**Validation**: All tests pass with >90% coverage

**Dependencies**: Task 1.1

## Phase 2: Background Task Management

### Task 2.1: Create background task manager module

- [x] Create `gitbrag/services/background_tasks.py`
- [x] Implement `schedule_report_generation()` function
- [x] Implement `generate_report_background()` function
- [x] Add error handling with try/finally for task cleanup
- [x] Add structured logging for task lifecycle events
- [x] Import and use task tracking functions from Phase 1

**Validation**: Functions can be called and execute without errors

**Dependencies**: Task 1.1, 1.2

### Task 2.2: Add helper function for params hash generation

- [x] Add `generate_params_hash()` to `gitbrag/services/reports.py`
- [x] Function should create consistent hash from show_star_increase and other params
- [x] Use same hash algorithm as `generate_cache_key()` for consistency
- [x] Add docstring explaining hash purpose and format

**Validation**: Hash is consistent for same parameters, different for different parameters

**Dependencies**: None

### Task 2.3: Write unit tests for background task manager

- [x] Create `tests/services/test_background_tasks.py`
- [x] Test `schedule_report_generation` registers task and schedules background work
- [x] Test `schedule_report_generation` returns False for duplicate tasks
- [x] Test `schedule_report_generation` respects per-reported-user limits (same GitHub username)
- [x] Test `schedule_report_generation` allows concurrent tasks for different reported users
- [x] Test `generate_report_background` updates cache on success
- [x] Test `generate_report_background` cleans up task on failure
- [x] Test `generate_report_background` handles GitHub API errors gracefully

**Validation**: All tests pass with >85% coverage

**Dependencies**: Task 2.1, 2.2

## Phase 3: Request Handler Modifications

### Task 3.1: Update user_report handler to use background tasks

- [x] Modify `gitbrag/www.py` - `user_report()` function
- [x] Add `background_tasks: BackgroundTasks` parameter
- [x] Implement cache state checking (age, staleness)
- [x] Implement task active checking with `is_task_active()`
- [x] Add logic to decide when to schedule background regeneration
- [x] Call `schedule_report_generation()` when appropriate
- [x] Pass task state to template context (is_regenerating, is_stale, cache_age)
- [x] Remove synchronous report generation for authenticated users with cache

**Validation**: Handler compiles and runs without errors

**Dependencies**: Task 2.1, 2.2

### Task 3.2: Update get_or_generate_report to support background context

- [x] Modify `gitbrag/services/reports.py` - `get_or_generate_report()`
- [x] Simplify function to focus on cache retrieval and metadata
- [x] Remove regeneration logic (moved to background task)
- [x] Keep stale cache detection logic
- [x] Return cache state information (age, staleness)

**Validation**: Function returns correct cache state

**Dependencies**: Task 3.1

**Note**: Function was unused after refactoring - removed entirely

## Phase 4: Template and UI Updates

### Task 4.1: Update user_report template with regeneration indicators

- [x] Modify `gitbrag/templates/user_report.html`
- [x] Add "Regenerating" notice when `is_regenerating == True`
- [x] Add "Login to Refresh" button when `is_stale and not authenticated`
- [x] Add "Refresh Now" button when `is_stale and authenticated`
- [x] Display cache age prominently when available
- [x] Use conditional rendering with Jinja2 `{% if %}`

**Validation**: Template renders correctly for all states

**Dependencies**: Task 3.1

### Task 4.2: Add CSS for loading spinner and notices

- [x] Create or update `gitbrag/static/css/reports.css`
- [x] Add spinner animation CSS
- [x] Add styling for regenerating notice (blue/info)
- [x] Add styling for stale notice (yellow/warning)
- [x] Ensure responsive design (mobile-friendly)

**Validation**: Styles display correctly in browser

**Dependencies**: Task 4.1

### Task 4.3: Add optional JavaScript for auto-refresh

- [x] Create `gitbrag/static/js/report_refresh.js` (optional enhancement)
- [x] Detect when `is_regenerating == true`
- [x] Auto-refresh page every 5 seconds when regenerating
- [x] Stop auto-refresh after 5 attempts or when regenerating completes
- [x] Show countdown timer in UI
- [x] Make feature opt-in or configurable

**Validation**: Auto-refresh works in browser without interfering with normal usage

**Dependencies**: Task 4.1, 4.2

**Note**: This task is optional and can be deferred

## Phase 5: Testing and Validation

### Task 5.1: Manual testing and validation

- [x] Start local development environment with docker-compose
- [x] Test authenticated user flow with stale cache
- [x] Test unauthenticated user flow with stale cache
- [x] Test force refresh flow
- [x] Verify Redis keys are created and cleaned up correctly
- [x] Verify background tasks complete successfully
- [x] Check logs for proper lifecycle events
- [x] Test error scenarios (GitHub API errors, Redis connection loss)

**Validation**: All manual test scenarios work as expected

**Dependencies**: All previous tasks

## Phase 6: Documentation and Cleanup

### Task 6.1: Update developer documentation

- [x] Update `docs/dev/web.md` with background task architecture
- [x] Update `docs/dev/cache.md` with task tracking patterns
- [x] Create new `docs/dev/background-tasks.md` (if needed)
- [x] Document task tracking Redis key patterns
- [x] Document per-user rate limiting behavior
- [x] Add architecture diagrams (from design.md)

**Validation**: Documentation is clear and complete

**Dependencies**: Task 5.3

### Task 6.2: Update user-facing documentation

- [x] Update `README.md` with improved performance notes
- [x] Document new UI elements ("Regenerating" notice, refresh buttons)
- [x] Explain cache behavior and auto-refresh for stale reports
- [x] Add FAQ section for common questions

**Validation**: User documentation is accurate and helpful

**Dependencies**: Task 5.3

### Task 6.3: Add logging and monitoring

- [x] Ensure all background task lifecycle events are logged
- [x] Add structured logging with task_id, username, period
- [x] Log task scheduling, start, completion, failure
- [x] Log deduplication events
- [x] Add metrics collection points (optional, for future monitoring)

**Validation**: Logs are useful for debugging and monitoring

**Dependencies**: Task 2.1, 3.1

### Task 6.4: Code review and refactoring

- [x] Review all code for consistency with project conventions
- [x] Ensure all functions have proper type hints
- [x] Ensure all functions have docstrings
- [x] Check for proper error handling
- [x] Run linters (ruff, mypy)
- [x] Fix any linting issues
- [x] Ensure test coverage is >85% for new code

**Validation**: All linters pass, code review approved

**Dependencies**: All previous tasks

## Phase 7: Configuration and Documentation

### Task 7.1: Add configuration to environment

- [x] Add environment variables to `.env.example`
- [x] Document task tracking settings (TASK_TIMEOUT_SECONDS, MAX_REPORTED_USER_CONCURRENT_TASKS)
- [x] Verify Redis configuration supports task tracking (persistence, memory limits)

**Validation**: Configuration is properly documented

**Dependencies**: Task 6.1

## Summary

**Total Tasks**: 18 main tasks (2 moved to future E2E testing proposal)

**Completed Tasks**: 17/18 ✅

**Remaining Tasks**: 0 core tasks (1 optional task moved to future)

**Estimated Effort**:

- Phase 1: 2-3 hours ✅
- Phase 2: 3-4 hours ✅
- Phase 3: 4-5 hours ✅
- Phase 4: 2-3 hours ✅
- Phase 5: 2-3 hours ✅ (manual testing complete, E2E moved to future)
- Phase 6: 2-3 hours ✅
- Phase 7: 1 hour ✅

**Total Completed**: 17-20 hours

**Parallelizable Work**:

- Tasks 1.1, 1.2, 2.2 can be done in parallel ✅
- Tasks 4.1, 4.2 can be done in parallel with Phase 3 ✅
- Tasks 6.1, 6.2 can be done in parallel ✅

**Critical Path**: Phase 1 → Phase 2 → Phase 3 → Phase 5 ✅

**Optional Tasks**:

- Task 4.3 (JavaScript auto-refresh) ✅ Completed
- Task 3.2 (Refactor get_or_generate_report) ✅ Completed (removed unused function)

**Moved to Future (Separate E2E Testing Proposal)**:

- Task 3.3 (Integration tests for request handler)
- Task 5.1 (E2E tests for complete user flows)
