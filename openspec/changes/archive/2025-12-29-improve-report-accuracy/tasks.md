# Implementation Tasks

## Phase 1: Foundational Improvements (Can be parallelized)

### Task 1.1: Add concurrency configuration settings

**Deliverable:** Settings for configurable concurrency limits

**Steps:**

1. Add `github_pr_file_fetch_concurrency` field to `GitHubSettings` in `gitbrag/conf/github.py`
2. Add `github_repo_desc_fetch_concurrency` field to `GitHubSettings`
3. Use `Field()` with `ge=1, le=20` validation and descriptive descriptions
4. Set defaults: `pr_file_fetch=5`, `repo_desc_fetch=10`
5. Update `.env.example` with new settings and explanatory comments

**Validation:**

- Settings load correctly with defaults
- Invalid values are rejected or clamped
- Test with various values in `.env` file

**Files affected:**

- `gitbrag/conf/github.py`
- `.env.example`

### Task 1.2: Add collection statistics tracking

**Deliverable:** Data structures to track success/failure rates during collection

**Steps:**

1. Create a `CollectionStats` dataclass in `gitbrag/services/github/pullrequests.py`
2. Include fields: `total_prs`, `file_fetch_success`, `file_fetch_failed`, `file_fetch_cached`, `failed_prs` (list of PR identifiers)
3. Add `stats` attribute to `PullRequestCollector` class
4. Initialize stats at the start of `collect_user_prs`
5. Pass stats to `fetch_pr_metrics` for tracking

**Validation:**

- Stats object is created and properly typed
- Stats are accessible after collection
- Type checking passes with mypy

**Files affected:**

- `gitbrag/services/github/pullrequests.py`

### Task 1.3: Enhance PR file fetch logging

**Deliverable:** Comprehensive logging in `fetch_pr_files` function

**Steps:**

1. Add INFO level log at start of `fetch_pr_files` with repo/PR identifier
2. Add DEBUG level log for cache hits with PR identifier
3. Add DEBUG level log for fresh fetches with TTL information
4. Add WARNING level log for 404 errors with context
5. Add ERROR level log for other HTTP errors with full context
6. Add ERROR level log with traceback for unexpected exceptions
7. Ensure all error logs include repo, PR number, and error details before returning empty tuple

**Validation:**

- Run tests and verify log output at different levels
- Trigger various error conditions and verify appropriate logs
- Verify cache hits and misses are logged correctly

**Files affected:**

- `gitbrag/services/github/pullrequests.py`

## Phase 2: Error Resilience (Depends on Phase 1)

### Task 2.1: Add error categorization

**Deliverable:** Function to categorize errors as transient or fatal

**Steps:**

1. Add `categorize_error` function in `gitbrag/services/github/pullrequests.py`
2. Return `"transient"` for timeouts, connection errors, 429, 503
3. Return `"fatal"` for 401, 404, 422
4. Return `"transient"` for unknown errors (conservative approach)
5. Add comprehensive docstring with examples
6. Add unit tests for error categorization

**Validation:**

- Unit tests cover all error categories
- Unknown errors default to transient
- Function is properly typed

**Files affected:**

- `gitbrag/services/github/pullrequests.py`
- `tests/services/test_pullrequests.py`

### Task 2.2: Add retry logic to fetch_pr_metrics

**Deliverable:** Retry wrapper for file fetching operations

**Steps:**

1. Update `fetch_pr_metrics` inner function in `PullRequestCollector.collect_user_prs`
2. Add retry loop with max 3 attempts for transient errors
3. Implement exponential backoff (1s, 2s, 4s)
4. Use `categorize_error` to determine if retry is appropriate
5. Log each retry attempt at WARNING level
6. Log final failure at ERROR level after retries exhausted
7. Update stats tracking for retries and final failures

**Validation:**

- Trigger transient errors and verify retries occur
- Trigger fatal errors and verify no retries
- Verify exponential backoff timing
- Verify stats are updated correctly

**Files affected:**

- `gitbrag/services/github/pullrequests.py`

### Task 2.3: Add data validation

**Deliverable:** Validation of fetched PR file data

**Steps:**

1. In `fetch_pr_files`, add validation after cache retrieval
2. Check tuple length, types of all elements
3. Check non-negative values for additions, deletions, changed_files
4. If cache validation fails, log WARNING and refetch from API
5. If API data has negative values, log WARNING and clamp to 0
6. Add unit tests for validation logic

**Validation:**

- Test with malformed cache data
- Test with negative values
- Verify refetch occurs on invalid cache data
- Unit tests pass

**Files affected:**

- `gitbrag/services/github/pullrequests.py`
- `tests/services/test_pullrequests.py`

## Phase 3: Integration and Statistics (Depends on Phase 2)

### Task 3.1: Use configured concurrency limits

**Deliverable:** Dynamic concurrency based on configuration

**Steps:**

1. Update `fetch_pr_metrics` in `collect_user_prs` to read concurrency from settings
2. Get settings via `get_github_settings()`
3. Use `settings.github_pr_file_fetch_concurrency` for semaphore
4. Log the concurrency limit being used at INFO level
5. Update repository description fetching in `generate_report_data` similarly
6. Use `settings.github_repo_desc_fetch_concurrency` for that semaphore

**Validation:**

- Test with different concurrency values
- Verify semaphore limits match configuration
- Verify logs show correct limits
- Test with missing config (should use defaults)

**Files affected:**

- `gitbrag/services/github/pullrequests.py`
- `gitbrag/services/reports.py`

### Task 3.2: Log collection summary statistics

**Deliverable:** Summary logs at INFO/WARNING/ERROR levels

**Steps:**

1. After all file fetching completes in `collect_user_prs`, calculate stats
2. Log total PRs, successful fetches, failed fetches at INFO level
3. Calculate and log success rate percentage
4. If failure rate > 10%, log at ERROR level
5. If failure rate > 0% but <= 10%, log at WARNING level
6. If any failures, log the count and suggest remediation
7. List up to 5 failed PR identifiers for investigation

**Validation:**

- Run with various success/failure scenarios
- Verify appropriate log levels
- Verify percentage calculations
- Integration test with real GitHub data

**Files affected:**

- `gitbrag/services/github/pullrequests.py`

### Task 3.3: Add collection timing logs

**Deliverable:** Performance visibility for collection phases

**Steps:**

1. Add start time tracking at beginning of `collect_user_prs`
2. Add timing for GitHub search query completion
3. Add timing for file fetching completion
4. Add timing for star increase collection (if enabled)
5. Log each phase duration at INFO level
6. Log total collection time at INFO level

**Validation:**

- Verify timing logs appear
- Verify times are reasonable
- Check timing accuracy with manual measurement

**Files affected:**

- `gitbrag/services/github/pullrequests.py`

### Task 3.4: Update documentation

**Deliverable:** User-facing documentation for new features

**Steps:**

1. Update `docs/dev/settings.md` with new concurrency settings
2. Explain tradeoffs: speed vs reliability
3. Provide guidance on tuning for different scenarios
4. Add troubleshooting section for missing data issues
5. Update `docs/dev/github-api.md` with error handling improvements
6. Document the logging output and how to interpret it

**Validation:**

- Documentation builds without errors
- Settings are accurately described
- Examples are clear and helpful

**Files affected:**

- `docs/dev/settings.md`
- `docs/dev/github-api.md`

## Phase 4: Testing and Validation

### Task 4.1: Add integration tests

**Deliverable:** Tests verifying end-to-end behavior

**Steps:**

1. Add integration test for complete PR collection with real-ish data
2. Test concurrency configuration is applied
3. Test retry logic with mock transient failures
4. Test statistics tracking and logging
5. Test validation catches malformed data

**Validation:**

- All new integration tests pass
- Coverage of new code is >80%
- Tests are reliable and not flaky

**Files affected:**

- `tests/integration/test_pr_collection_accuracy.py` (new file)

### Task 4.2: Run manual testing with real data

**Deliverable:** Verified improved accuracy with real GitHub data

**Steps:**

1. Test with a user having many PRs (100+)
2. Generate reports for 1 year, 2 years, 5 years, all time
3. Verify code metrics (additions/deletions) are consistent and complete
4. Review logs for any errors or warnings
5. Compare success rates across different time periods
6. Verify concurrency settings can be tuned

**Validation:**

- Reports show complete data across all time periods
- Success rate is >95% (or failures are explained)
- Logs provide clear visibility into collection process
- Tuning concurrency affects performance as expected

**Files affected:**

- N/A (manual testing)

### Task 4.3: Update test fixtures and mocks

**Deliverable:** Test infrastructure supports new functionality

**Steps:**

1. Update existing test mocks to include new logging
2. Add mock responses for retry scenarios
3. Update fixtures for error conditions
4. Ensure tests don't break due to new logging output

**Validation:**

- All existing tests still pass
- New mocks are reusable
- Test output is clean

**Files affected:**

- `tests/conftest.py`
- `tests/services/test_pullrequests.py`
- `tests/test_reports.py`

## Dependencies Between Tasks

- Tasks in Phase 1 can be done in parallel
- Phase 2 tasks depend on 1.2 and 1.3
- Phase 3 tasks depend on all Phase 2 tasks
- Phase 4 can begin after Phase 3

## Parallelization Opportunities

- Task 1.1, 1.2, 1.3 can be done simultaneously
- Task 2.1, 2.2, 2.3 can be done by different developers
- Documentation (3.4) can start early and be updated throughout
- Testing (4.1, 4.3) can begin as soon as relevant implementation tasks complete
