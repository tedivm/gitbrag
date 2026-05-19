## 1. Backend Period Logic

- [x] 1.1 Add `3_years` to the allowed periods in `normalize_period()` in `gitbrag/services/reports.py`
- [x] 1.2 Add `3_years` date range branch (1095 days) in `calculate_date_range()` in `gitbrag/services/reports.py`
- [x] 1.3 Use cached `since`/`until` from `cached_meta` for display in `gitbrag/www.py` (with fallback to `calculate_date_range`)
- [x] 1.4 Update the `period` parameter docstring in `gitbrag/www.py` (line 391)
- [x] 1.5 Update the `period` parameter docstring in `gitbrag/services/background_tasks.py` (line 57)

## 2. Template Changes

- [x] 2.1 Add "3 Years" link to the period selector in `gitbrag/templates/user_report.html` (between 2-year and 5-year links)
- [x] 2.2 Add "Past 3 years" description branch in `gitbrag/templates/user_report.html`
- [x] 2.3 Update home page marketing copy to include "3yr" in `gitbrag/templates/home.html` (line 80)

## 3. Documentation

- [x] 3.1 Update period filtering in `docs/dev/web.md` (line 10: add 3 and 5 years), query params (line 206: add 3_years, 5_years), and report template section (line 253)

## 4. Tests

- [x] 4.1 Add new test for `normalize_period("3_years")` in `tests/test_reports.py`
- [x] 4.2 Add new test for `calculate_date_range("3_years")` in `tests/test_reports.py`
- [x] 4.3 Add test for `3_years` period rendering (selector link and description text) in `tests/test_www.py`
- [x] 4.4 Add test for cached date range display using `cached_meta` in `tests/test_www.py`
- [x] 4.5 Add test for date range fallback when `cached_meta` is missing in `tests/test_www.py`

## 5. Verification

- [x] 5.1 Run `make tests` to ensure all tests pass
- [x] 5.2 Run `make chores` to ensure formatting is correct
