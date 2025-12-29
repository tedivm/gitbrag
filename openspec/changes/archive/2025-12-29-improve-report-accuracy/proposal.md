# Change: Improve Report Accuracy for Longer Time Periods

## Why

Reports for longer time periods (2 years, 5 years, all time) are missing significant "lines changed" data compared to 1-year reports due to silent failures in concurrent PR file fetching operations.

## What Changes

- Add comprehensive logging throughout PR collection to diagnose failures
- Implement retry logic for transient errors during file fetching
- Make concurrency limits configurable with conservative defaults (reduce from 10 to 5)
- Add collection statistics tracking to report success/failure rates
- Enhance error handling to distinguish fatal from transient errors

## Impact

- Affected specs: `github-pull-request-collection`
- Affected code: `gitbrag/services/github/pullrequests.py`, `gitbrag/services/reports.py`, `gitbrag/conf/github.py`

---

## Summary

Improve the accuracy and reliability of contribution report generation, particularly for longer time periods (2 years, 5 years, all time), by enhancing logging, error handling, and configurability of concurrent operations.

## Problem

Reports for longer time periods (2 years, 5 years, all time) are missing significant amounts of "lines changed" data compared to the 1-year report. The current implementation:

- Uses a semaphore limit of 10 concurrent requests for PR file fetching
- Silently returns empty data (`([], 0, 0, 0)`) when errors occur during file fetching
- Lacks comprehensive logging to diagnose why data is missing
- Has no retry logic in the `fetch_pr_metrics` function
- Doesn't track success/failure rates for concurrent operations

This results in incomplete reports where users see their PR counts but missing or inaccurate code metrics (additions, deletions, changed files).

## Hypothesis

High concurrency combined with insufficient error handling is causing lookup failures that silently drop data. As the number of PRs increases with longer time periods, the probability of encountering rate limits or transient errors increases, leading to more data loss.

## Solution

1. **Enhanced Logging** - Add comprehensive logging throughout the PR collection and file fetching pipeline to track:
   - Success/failure rates for file fetching operations
   - Rate limit encounters and wait times
   - Individual PR file fetch failures with reasons
   - Overall collection statistics

2. **Improved Error Resilience** - Enhance error handling to:
   - Distinguish between fatal errors (must propagate) and recoverable errors (can retry)
   - Add retry logic at the PR metrics fetching level
   - Track and report partial failures vs complete failures

3. **Configurable Concurrency** - Make concurrency limits configurable with sensible defaults:
   - Reduce default semaphore from 10 to 5 for better stability
   - Allow environment variable configuration for different deployment scenarios
   - Add separate limits for different operation types (file fetching vs repo descriptions)

4. **Statistics and Monitoring** - Add report generation statistics to:
   - Track success rates for each phase of collection
   - Provide visibility into partial failures
   - Enable better debugging and optimization

## Related Specs

- `github-pull-request-collection` - Core PR collection functionality being enhanced
- `contribution-report-cli` - CLI that generates reports using this functionality
- `web-user-interface` - Web interface that displays these reports

## Related Changes

None - this is a new proposal

## Dependencies

None - enhances existing functionality

## Risks

- Additional logging may impact performance slightly (mitigated by using appropriate log levels)
- Lower concurrency may increase report generation time (mitigated by background job support)
- Changes to error handling behavior could surface previously hidden issues (benefit: better visibility)

## Alternatives Considered

1. **Increase concurrency instead of decreasing** - Rejected because the issue appears to be errors at high concurrency, not slowness
2. **Remove concurrency entirely** - Rejected because sequential fetching would be too slow for users with many PRs
3. **Add caching only** - Already exists; doesn't solve the accuracy problem for initial fetches

