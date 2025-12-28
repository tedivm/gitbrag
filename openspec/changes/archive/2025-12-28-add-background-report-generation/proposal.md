# Proposal: Background Report Generation

## Overview

Improve user experience and application performance by moving report generation from synchronous request handlers to background tasks, allowing users to immediately see cached reports (or a loading message) while fresh reports are generated asynchronously.

## Problem Statement

Currently, when users visit a report page, the entire report generation process happens synchronously within the HTTP request handler. This creates several UX and performance issues:

1. **Poor initial load experience**: Users must wait for the full report generation to complete before seeing any content, which can take 10 seconds to several minutes for users with many contributions
2. **Redundant work**: Multiple users accessing the same report simultaneously trigger duplicate API calls and report generation
3. **Wasted resources**: The same report (same user, same period) is generated multiple times when it could be shared
4. **Timeout risk**: Long-running report generation can hit HTTP timeout limits
5. **No visual feedback**: Users don't know if the page is loading, frozen, or processing

## Proposed Solution

Implement asynchronous report generation using FastAPI's BackgroundTasks to decouple report display from report generation:

1. **Immediate response**: Serve cached reports instantly when available, with a notice that refresh is in progress if cache is stale
2. **Background regeneration**: Schedule report updates in the background without blocking the response
3. **Task deduplication**: Prevent multiple simultaneous generation tasks for the same report
4. **Per-reported-user rate limiting**: Allow only one report generation per reported user at a time to maximize cache benefits and reduce redundant API calls
5. **Progress indication**: Show users when reports are being regenerated with visual feedback

### Architecture Choice: FastAPI BackgroundTasks vs Celery

**Recommendation: FastAPI BackgroundTasks**

Rationale:

- **Simpler maintenance**: No separate worker process, queue management, or additional monitoring required
- **Consistent technology**: Leverages existing async/await patterns already used throughout the application
- **Sufficient for use case**: Report generation is non-critical and completion isn't time-sensitive
- **No new infrastructure**: Avoids adding message broker dependencies (though Redis is already available)
- **Lower operational complexity**: Single-process deployment remains viable for current scale
- **Natural fit**: Background tasks integrate seamlessly with FastAPI request lifecycle

Celery would be appropriate if:

- Multiple worker processes were needed for higher throughput
- Task distribution across multiple servers was required
- Complex task chains, retries, or scheduling were needed
- Current scale exceeded single-server capacity

For the current requirements (deduplication, user-level rate limiting, async generation), FastAPI BackgroundTasks provides the right balance of simplicity and functionality.

## Benefits

1. **Instant page loads**: Users see cached content immediately (if available)
2. **Better UX**: Clear visual feedback when reports are being updated
3. **Resource efficiency**: Eliminates duplicate API calls for the same report
4. **Improved reliability**: Requests complete quickly, avoiding timeout issues
5. **Performance optimization**: Per-reported-user task limiting allows sequential generation to benefit from shared cache (user profiles, repositories, etc.)
6. **Scalable caching**: Multiple users benefit from shared cached reports

## Scope

### In Scope

1. Task tracking system to prevent duplicate report generation
2. Background task scheduling for report regeneration
3. Modified request handler to return cached data immediately with background refresh
4. Visual indicators in templates showing when reports are being regenerated
5. Per-reported-user task limiting to ensure only one report generates at a time per reported GitHub username
6. Task status API for checking generation progress (optional enhancement)

### Out of Scope

1. Celery/RabbitMQ/Redis queue infrastructure
2. Distributed task processing across multiple workers
3. Real-time progress updates via WebSockets
4. Task retry logic (initial implementation)
5. Admin dashboard for task monitoring
6. Task scheduling/cron for automatic refresh

## Technical Approach

### Task Tracking

Use Redis to track active report generation tasks:

- Key pattern: `task:report:{username}:{period}:{params_hash}`
- Value: Task metadata (started_at, status, worker_id)
- TTL: Auto-expire after completion or timeout (e.g., 5 minutes)

### Deduplication Strategy

Before starting a background task:

1. Check if task key exists in Redis
2. If exists and recent (< 5 min old), skip scheduling new task
3. If not exists, set task key and schedule background task
4. On task completion, remove task key

### Per-Reported-User Rate Limiting

Track active tasks per reported GitHub username:

- Key pattern: `task:user:{reported_username}:active`
- Value: List of active task identifiers for this reported user
- Limit: Maximum 1 active task per reported username (e.g., only one report for "tedivm" generating at a time)
- Rationale: Sequential generation for the same user allows cache reuse for user profiles, repositories, and PR data
- Behavior: Queue additional requests or skip if already generating

### Request Flow

**Authenticated User Request:**

1. Check for cached report
2. If cache exists and fresh (<24h), serve immediately
3. If cache exists but stale (≥24h), serve cached + schedule background refresh
4. If no cache, return "generating" message + schedule background task
5. Background task generates report and updates cache

**Unauthenticated User Request:**

1. Check for cached report
2. If cache exists (any age), serve immediately with age indicator
3. If cache stale, show "Login to refresh" prompt
4. If no cache, show "Login to generate" prompt

## Implementation Tasks

See [tasks.md](./tasks.md) for detailed implementation checklist.

## Testing Strategy

1. Unit tests for task tracking functions (set, check, clear)
2. Unit tests for deduplication logic
3. Integration tests for background task execution
4. E2E tests for request flow with background tasks
5. Load tests for concurrent requests to same report
6. Tests for per-user rate limiting

## Implementation Plan

1. Implement task tracking infrastructure
2. Add background task support to report generation service
3. Update request handler to use background tasks
4. Update templates with regeneration indicators
5. Test thoroughly in development environment
6. Document behavior in user-facing docs

## Alternatives Considered

### Alternative 1: Celery + Redis Queue

**Pros**: Battle-tested, robust retry logic, distributed workers, monitoring tools
**Cons**: Additional complexity, separate worker process, more infrastructure to maintain
**Decision**: Deferred - implement if FastAPI BackgroundTasks proves insufficient

### Alternative 2: Server-Sent Events (SSE) for Progress

**Pros**: Real-time progress updates to users
**Cons**: Increases complexity, requires connection management
**Decision**: Out of scope - can be added later if needed

### Alternative 3: Synchronous Generation with Longer Timeouts

**Pros**: Simplest - no architectural changes
**Cons**: Doesn't solve UX issues, still blocks requests, duplicates work
**Decision**: Rejected - doesn't address core problems

## Risks and Mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Background tasks fail silently | Users see stale data indefinitely | Add comprehensive logging and task timeout cleanup |
| Task tracking keys not cleaned up | Redis memory leak | Set TTL on all task keys (300s auto-expire) |
| Race conditions in task deduplication | Multiple tasks for same report | Use Redis SET NX commands for atomic task locking |
| Users don't understand "refreshing" state | Confusion about data freshness | Clear UI messaging and visual indicators |

## Success Metrics

- Report page load time: < 2 seconds (from 10 seconds to several minutes)
- Cache hit rate: > 80% for popular reports
- Duplicate report generation: < 5% of requests
- User satisfaction: Measured via feedback/support tickets
- GitHub API usage: Reduced by 50-70% via better caching

## Future Enhancements

1. Task status API endpoint for checking generation progress
2. Real-time updates via WebSockets or SSE
3. Scheduled/automatic cache refresh for popular reports
4. Admin dashboard for task monitoring and management
5. Task retry logic with exponential backoff
6. Migration to Celery if scale requires distributed workers

## Related Changes

- Extends existing caching infrastructure (no changes to cache specs)
- Modifies web-user-interface specification (see spec deltas)
- May require new background-task-management capability spec

## References

- [FastAPI Background Tasks Documentation](https://fastapi.tiangolo.com/tutorial/background-tasks/)
- Current implementation: [gitbrag/www.py](../../../gitbrag/www.py) line 373
- Report generation: [gitbrag/services/reports.py](../../../gitbrag/services/reports.py) line 337
- Cache documentation: [docs/dev/cache.md](../../../docs/dev/cache.md)
