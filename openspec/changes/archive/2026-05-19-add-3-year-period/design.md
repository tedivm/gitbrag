# Design: add-3-year-period

## Context

The report generation pipeline uses a period string that flows from a URL query parameter through normalization, date range calculation, cache keying, background task execution, and template rendering. The existing periods are `1_year` (365d), `2_years` (730d), `5_years` (1825d), and `all_time` (since 2008). The period string is validated in `normalize_period()`, converted to datetimes in `calculate_date_range()`, and displayed in `user_report.html` via Jinja conditionals. No new data models, services, or external dependencies are needed.

## Goals / Non-Goals

**Goals:**

- Add `3_years` (1095 days) as a valid period option
- Display "3 Years" in the period selector between "2 Years" and "5 Years"
- Update home page marketing copy to include 3 years
- Display the actual cached date range (start → end) instead of recalculating from "now"

**Non-Goals:**

- Adding other time periods (e.g., 6 months, 4 years)
- Changing the ordering or layout of the period selector beyond inserting the new option
- Modifying CLI behavior (the CLI uses `--since`/`--until` directly, not period names)
- Changing the cache metadata format beyond using existing fields

## Decisions

### D1: `3_years` uses 1095 days (3 × 365)

**Decision:** Follow the existing convention of `365 × N` days rather than a calendar-aware calculation. The existing `2_years` uses 730 days and `5_years` uses 1825 days, so `3_years` uses 1095 days for consistency.

```python
# gitbrag/services/reports.py
# In calculate_date_range(), add between 2_years and 5_years:
elif period == "3_years":
    since = until - timedelta(days=1095)
```

**Alternative considered:** Calendar-aware subtraction using `dateutil.relativedelta`. Rejected — existing periods use fixed day counts, and maintaining consistency matters more than leap year precision.

### D2: `3_years` sits between `2_years` and `5_years` in the UI

**Decision:** Insert the new link between the 2-year and 5-year options in the period selector, maintaining ascending chronological order.

```html
<!-- gitbrag/templates/user_report.html -->
<a href="/user/github/{{ username }}?period=3_years"
  class="period-link {% if period == '3_years' %}active{% endif %}">3 Years</a>
```

**Alternative considered:** Placing it at the end. Rejected — ascending order is more intuitive for users scanning options.

### D3: No changes to repository sorting logic

**Decision:** The `all_time` period has special sorting behavior (by PR count instead of star increase). The `3_years` period should use the standard star-increase sorting, same as `1_year` and `2_years`.

**Rationale:** The special `all_time` sorting exists because star accumulation over 15+ years is a better signal than recent star velocity. Three years is close enough to the 1 and 2 year windows that star increase remains the appropriate sort metric.

### D4: Use cached date range for display instead of recalculating from "now"

**Decision:** When serving cached data, use the `since` and `until` values stored in the cache metadata (`cached_meta`) rather than recalculating them from `calculate_date_range()`. The cache metadata is already populated by both `reports.py` and `background_tasks.py` with the actual date range used during generation.

Current behavior in `www.py:538`:
```python
# Always recalculates from "now" — shows a moving end date even for stale cached data
since, until = calculate_date_range(period)
```

New behavior — use cached metadata when available:
```python
# Use cached dates if available, otherwise fall back to calculated
if cached_meta and "since" in cached_meta and "until" in cached_meta:
    since = datetime.fromisoformat(cached_meta["since"])
    until = datetime.fromisoformat(cached_meta["until"])
else:
    since, until = calculate_date_range(period)
```

**Rationale:** The current approach always shows "today" as the end date, even when serving stale cached data from days or weeks ago. This misleads users about what data is actually in the report. The cache metadata already stores the real dates used during generation, so using them is a low-cost fix with no schema changes.

**Alternative considered:** Always pass `since`/`until` in the cached report data itself. Rejected — the metadata key already exists and contains the fields, no schema migration needed.

## Implementation Detail

### `gitbrag/services/reports.py`

Two changes in existing functions:

1. `normalize_period()` — add `"3_years"` to the allowed tuple (line 40)
2. `calculate_date_range()` — add `elif period == "3_years"` branch with `timedelta(days=1095)` (between lines 62-63)

### `gitbrag/templates/user_report.html`

Two changes:

1. Period description block — add `{% elif period == "3_years" %}Past 3 years` between the 2-year and 5-year branches
2. Period selector — add the "3 Years" link between the 2-year and 5-year links

### `gitbrag/templates/home.html`

Update the marketing copy line that lists available periods from "1yr, 2yr, 5yr" to "1yr, 2yr, 3yr, 5yr".

### `gitbrag/www.py`

Two changes:

1. Update the docstring for the `period` query parameter to include `3_years`.
2. Use cached `since`/`until` from `cached_meta` for display instead of recalculating from "now" (replacing line 538's `calculate_date_range(period)` call).

### `gitbrag/services/background_tasks.py`

Update the docstring for the `period` parameter to include `3_years`.

### `docs/dev/web.md`

Update the period filtering documentation to include 3 years.

## Testing Philosophy

### Date range display accuracy

Verify that when serving cached data, the displayed date range matches the actual `since`/`until` stored in cache metadata — not a recalculated range from "now". Test with stale cached data where the end date should be in the past.

### Period normalization

Verify that `3_years` is accepted by `normalize_period()` and returns `"3_years"` unchanged. Confirm that invalid periods still fall back to `1_year`.

### Date range calculation

Verify that `calculate_date_range("3_years")` returns a date range of approximately 1095 days.

### UI rendering

Test that the `3_years` period renders the correct description text ("Past 3 years") and that the "3 Years" link appears in the period selector with the correct `?period=3_years` query parameter.

### End-to-end report generation

Test the full flow with `period=3_years` through the background task to ensure PRs are collected for the correct 3-year date range.

## Risks / Trade-offs

### Period selector crowding

**Risk:** With five options, the period selector flex row may wrap on narrower screens.

**Mitigation:** The existing CSS uses `flex-wrap: wrap` — the extra item should wrap naturally. If needed, the font size or spacing can be adjusted, but this is unlikely to be an issue given the current viewport targets.
