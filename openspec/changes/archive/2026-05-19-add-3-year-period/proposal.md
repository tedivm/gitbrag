## Why

The current period selector jumps from 2 years to 5 years, leaving a gap for users who want to see their contributions over a 3-year window — a common timeframe for promotion cycles, contract renewals, and career milestones.

## What Changes

- Add a "3 Years" option to the period selector on the user report page
- Extend the backend period normalization and date range calculation to support `3_years` (1095 days)
- Update the displayed date range to use actual cached dates instead of recalculating from "now"
- Update marketing copy on the home page to include 3 years
- Fix documentation to include all current periods (3 years, 5 years) and the cached date range behavior
- Update tests

## Capabilities

### New Capabilities

- `report-periods`: Support for configurable time period ranges in user reports, including the new 3-year option alongside existing 1, 2, and 5-year periods plus all-time

### Modified Capabilities

(none — no existing specs to modify)

## Impact

- `gitbrag/services/reports.py` — period normalization and date range calculation
- `gitbrag/www.py` — route docstring, cached date range display logic
- `gitbrag/templates/user_report.html` — period selector UI and description text
- `gitbrag/templates/home.html` — marketing copy
- `gitbrag/services/background_tasks.py` — docstring
- `docs/dev/web.md` — period filtering, query params, report template documentation (also adds missing 5_years)
- `tests/test_reports.py` — new tests for `normalize_period` and `calculate_date_range`
- `tests/test_www.py` — new tests for period rendering and cached date range display
