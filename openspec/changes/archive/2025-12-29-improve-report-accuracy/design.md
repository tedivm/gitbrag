# Design Document: Improve Report Accuracy

## Problem Analysis

### Root Cause Investigation

The current implementation has several issues that contribute to data loss in longer time period reports:

1. **Silent Failures**: The `fetch_pr_files` function returns empty tuples `([], 0, 0, 0)` on any error without distinguishing between:
   - Transient errors (timeouts, rate limits) that could be retried
   - Fatal errors (404, 401) that should not be retried
   - Actual empty PRs (legitimate zero changes)

2. **High Concurrency**: A semaphore limit of 10 concurrent requests may be too aggressive for:
   - Accounts with many PRs (100+)
   - Rate-limited API scenarios
   - Longer time periods that fetch more data

3. **Insufficient Visibility**: Limited logging makes it impossible to:
   - Identify which PRs are failing
   - Understand failure rates
   - Diagnose rate limiting issues
   - Correlate errors with time periods

### Why Longer Time Periods Are Affected More

- **More PRs = More Opportunities for Failure**: A 5-year report may have 5x the PRs of a 1-year report, so even a 5% failure rate compounds
- **Rate Limiting**: More API calls means higher chance of hitting rate limits
- **Transient Errors**: Longer-running operations have more exposure to temporary network issues
- **Cache Misses**: Older data is less likely to be cached, requiring more API calls

## Architectural Decisions

### 1. Logging Strategy

**Decision**: Multi-level logging with structured information

**Rationale**:

- DEBUG: Individual operation details (cache hits, per-PR fetches)
- INFO: Summary statistics (total PRs, success rates, timing)
- WARNING: Recoverable issues (retries, partial failures <10%)
- ERROR: Critical issues (persistent failures, failure rate >10%)

**Tradeoffs**:

- ✅ Enables diagnosis without overwhelming logs
- ✅ Production-ready logging levels
- ⚠️ Slight performance impact from logging (negligible)

### 2. Error Handling Strategy

**Decision**: Categorize errors and apply appropriate strategies

**Rationale**:

- Transient errors (timeout, rate limit) → Retry with backoff
- Fatal errors (404, 401) → Fail fast, don't waste retries
- Unknown errors → Retry conservatively (better safe than sorry)

**Tradeoffs**:

- ✅ Maximizes data completeness
- ✅ Avoids wasting time on unrecoverable errors
- ⚠️ Retries add latency (mitigated by background jobs)

**Implementation Pattern**:

```python
def categorize_error(error: Exception) -> str:
    """Return 'transient' or 'fatal'"""
    if isinstance(error, httpx.TimeoutException):
        return "transient"
    if isinstance(error, httpx.HTTPStatusError):
        if error.response.status_code in (404, 401, 422):
            return "fatal"
        if error.response.status_code in (429, 503):
            return "transient"
    return "transient"  # Conservative default
```

### 3. Concurrency Configuration

**Decision**: Make limits configurable with conservative defaults

**Rationale**:

- Current default of 10 is too aggressive
- New default of 5 balances speed and reliability
- Configuration allows tuning for different scenarios:
  - Production: lower limit (5) for stability
  - Development: higher limit (8-10) for faster iteration
  - Background jobs: moderate limit (6-8) for throughput

**Tradeoffs**:

- ✅ Flexibility for different deployments
- ✅ Conservative defaults prevent issues
- ⚠️ Users must understand tradeoffs to tune effectively (mitigated by documentation)

**Configuration Schema**:

```python
class GitHubSettings(BaseSettings):
    github_pr_file_fetch_concurrency: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Concurrent PR file fetch operations (1-20, lower is more reliable)",
    )
    github_repo_desc_fetch_concurrency: int = Field(
        default=10,
        ge=1,
        le=20,
        description="Concurrent repo description fetches (1-20)",
    )
```

### 4. Statistics Tracking

**Decision**: Track detailed statistics during collection

**Rationale**:

- Provides visibility into data completeness
- Enables alerting on high failure rates
- Helps users understand report quality

**Data Structure**:

```python
@dataclass
class CollectionStats:
    total_prs: int = 0
    file_fetch_success: int = 0
    file_fetch_failed: int = 0
    file_fetch_cached: int = 0
    failed_prs: list[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        total_attempts = self.file_fetch_success + self.file_fetch_failed
        if total_attempts == 0:
            return 1.0
        return self.file_fetch_success / total_attempts
```

**Tradeoffs**:

- ✅ Minimal memory overhead
- ✅ Simple to track and report
- ⚠️ Stats collection adds trivial overhead (acceptable)

### 5. Retry Strategy

**Decision**: 3 retries with exponential backoff for transient errors

**Rationale**:

- Most transient issues resolve within 3 attempts
- Exponential backoff (1s, 2s, 4s) with jitter prevents thundering herd
- Jitter (±25% randomness) distributes retries when multiple requests fail simultaneously
- 7 seconds max retry time is acceptable for background jobs
- Existing `GitHubAPIClient` already has retry logic; add another layer for operation-level retries

**Implementation Approach**:

```python
import random

max_retries = 3
base_delays = [1, 2, 4]  # exponential backoff base

for attempt in range(max_retries + 1):
    try:
        result = await fetch_pr_files(...)
        stats.file_fetch_success += 1
        return result
    except Exception as e:
        error_type = categorize_error(e)
        if error_type == "fatal" or attempt == max_retries:
            logger.error(f"Failed after {attempt + 1} attempts: {e}")
            stats.file_fetch_failed += 1
            stats.failed_prs.append(f"{owner}/{repo}#{number}")
            return ([], 0, 0, 0)

        # Add jitter: ±25% randomness to prevent thundering herd
        base_delay = base_delays[attempt]
        jitter = random.uniform(-0.25, 0.25) * base_delay
        wait_time = base_delay + jitter
        logger.warning(f"Transient error (attempt {attempt + 1}/{max_retries}), retrying in {wait_time:.2f}s: {e}")
```

**Tradeoffs**:

- ✅ Handles transient issues effectively
- ✅ Doesn't waste time on fatal errors
- ⚠️ Adds latency on failures (acceptable for background jobs)

## Integration Points

### 1. Settings System

The concurrency configuration integrates with existing Pydantic Settings:

- Settings loaded via environment variables
- Validation handled by Pydantic Field constraints
- Settings accessible throughout codebase via `get_github_settings()`

### 2. Caching System

No changes to caching behavior, but enhanced logging shows:

- Cache hit/miss rates
- Cache effectiveness per time period
- Identifies when cache warming would help

### 3. Background Tasks

Background task system benefits most from these changes:

- Better reliability means fewer partial failures
- Statistics can be stored with task metadata
- Users can see why their background report might be incomplete

### 4. Web Interface

Web interface can display collection quality:

- Show success rate badge on reports
- Indicate if data might be incomplete
- Link to documentation for troubleshooting

## Validation Strategy

### Unit Tests

- Error categorization logic
- Statistics tracking
- Retry logic with mocked failures
- Configuration validation

### Integration Tests

- End-to-end PR collection with mock GitHub API
- Verify retry behavior with transient failures
- Verify concurrency limits are applied
- Verify statistics are accurate

### Manual Testing

- Test with real GitHub accounts (multiple sizes)
- Compare 1-year vs 5-year report completeness
- Verify logs provide useful information
- Tune concurrency and observe behavior

## Rollout Plan

### Phase 1: Foundation (Low Risk)

- Add configuration settings
- Add statistics tracking structures
- Add logging (DEBUG level by default)

**Risk**: Minimal, no behavior changes

### Phase 2: Error Handling (Medium Risk)

- Add error categorization
- Add retry logic
- Add data validation

**Risk**: Changes error behavior, but strictly improvements

### Phase 3: Integration (Low Risk)

- Use configured concurrency
- Log summary statistics
- Update documentation

**Risk**: Minimal, configuration is backward compatible

### Phase 4: Validation (No Risk)

- Add tests
- Manual testing
- Documentation updates

**Risk**: None, tests only

## Success Metrics

### Technical Metrics

- **Success Rate**: Target >95% for PR file fetching
- **Retry Rate**: <5% of operations require retries
- **Fatal Error Rate**: <0.1% of operations have fatal errors
- **Cache Hit Rate**: Track but don't mandate (depends on workload)

### User-Facing Metrics

- **Data Completeness**: Lines changed should be consistent across time periods for same PRs
- **Report Generation Time**: Should not increase significantly (<10% regression acceptable)
- **User-Reported Issues**: Reduction in "missing data" reports

### Observability

- Clear logs enable diagnosis
- Statistics provide health visibility
- Configuration enables tuning

## Future Enhancements

### 1. Auto-tuning

Automatically adjust concurrency based on error rates:

- Start with configured limit
- If error rate >10%, reduce by 1
- If error rate <1%, increase by 1 (up to max)
- Reset to default after each collection

### 2. Circuit Breaker

Prevent cascading failures:

- If failure rate >50% for 10 consecutive operations, stop collection
- Wait for cooldown period
- Resume with reduced concurrency

### 3. Metrics/Telemetry

Export metrics to monitoring systems:

- Prometheus metrics for success/failure rates
- Grafana dashboards for visualization
- Alerting on high failure rates

### 4. Partial Report Support

Allow reports to be generated with incomplete data:

- Show "X% complete" indicator
- List which PRs are missing data
- Provide "refresh" option to retry failed PRs

## References

- **Existing Spec**: `openspec/specs/github-pull-request-collection/spec.md`
- **PR Collection Code**: `gitbrag/services/github/pullrequests.py`
- **Report Generation**: `gitbrag/services/reports.py`
- **GitHub Client**: `gitbrag/services/github/client.py`
- **Settings**: `gitbrag/conf/github.py`
