## Purpose

Define the supported time periods for contribution reports and how they are normalized, calculated, and displayed.

## Requirements

### Requirement: Three-year period is accepted and normalized
The system SHALL accept `3_years` as a valid period string in `normalize_period()` and return it unchanged.

#### Scenario: Valid three-year period normalization
- **WHEN** `normalize_period("3_years")` is called
- **THEN** the result is `"3_years"`

### Requirement: Three-year date range calculation
The system SHALL calculate a 1095-day date range for the `3_years` period in `calculate_date_range()`.

#### Scenario: Three-year date range
- **WHEN** `calculate_date_range("3_years")` is called
- **THEN** the returned `since` datetime is 1095 days before the current UTC time

### Requirement: Cached date range is displayed accurately
When serving a cached report, the displayed date range SHALL reflect the actual `since` and `until` dates stored in cache metadata, not a recalculated range from "now".

#### Scenario: Stale cached report shows original dates
- **WHEN** a report is served from cache with `cached_meta` containing `since` and `until` fields
- **THEN** the displayed `since_date` and `until_date` match those cached values formatted as `%Y-%m-%d`

#### Scenario: Missing cache metadata falls back to calculated range
- **WHEN** a report is served but `cached_meta` is missing or lacks `since`/`until` fields
- **THEN** the displayed date range is calculated from `calculate_date_range(period)`

### Requirement: Three-year period appears in the period selector
The user report page SHALL display a "3 Years" link in the period selector between the "2 Years" and "5 Years" options.

#### Scenario: Three-year link in selector
- **WHEN** a user views a report at `/user/github/{username}`
- **THEN** the period selector contains a link with text "3 Years" and href `/user/github/{username}?period=3_years`

### Requirement: Three-year active state in selector
The "3 Years" link SHALL have the `active` class when the current period is `3_years`.

#### Scenario: Active three-year link
- **WHEN** a user views a report with `?period=3_years`
- **THEN** the "3 Years" link has the `active` CSS class

### Requirement: Three-year period description text
The period description SHALL display "Past 3 years" when the period is `3_years`.

#### Scenario: Three-year description
- **WHEN** a user views a report with `?period=3_years`
- **THEN** the period description reads "Past 3 years"

### Requirement: Home page mentions three-year period
The home page SHALL include "3yr" in its period options marketing copy.

#### Scenario: Home page period listing
- **WHEN** a user views the home page
- **THEN** the period options text includes "3yr" alongside "1yr", "2yr", "5yr", and "all time"
