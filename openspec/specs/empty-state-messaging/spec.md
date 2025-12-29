# empty-state-messaging Specification

## Purpose
TBD - created by archiving change polish-ux-improvements. Update Purpose after archive.
## Requirements
### Requirement: User report display when no pull requests found

The system MUST display an encouraging message when no pull requests are found for a given period, promoting a positive user experience.

#### Scenario: Display encouraging message when no PRs found

**Given** a user report is generated for a period
**And** no pull requests are found for the specified time range
**When** the user report template renders the empty state
**Then** the system displays an encouraging message instead of neutral text
**And** the message acknowledges that everyone starts somewhere
**And** the message suggests taking action (contributing to open source)
**And** the message maintains a professional tone
**And** the message is brief (1-2 sentences)

#### Scenario: Empty state message example

**Given** no pull requests are found
**When** the empty state section renders
**Then** the message could be: "No pull requests found for this period. Every open source journey starts somewhere—your next contribution is waiting! 🚀"
**Or** a similar encouraging message with positive, actionable tone
**And** the message includes an emoji or visual element for friendliness
**And** the message avoids being overly casual or discouraging

#### Scenario: Empty state styling remains consistent

**Given** the empty state message is displayed
**When** the user report page renders
**Then** the empty state section uses existing page styling
**And** the message appears where repository list would normally display
**And** the page layout and other elements (profile, summary, filters) remain unchanged
**And** the message is visually distinct but not distracting

#### Scenario: Empty state respects user context

**Given** different users may have different time ranges with no PRs
**When** the empty state displays
**Then** the message is general enough to apply to any user
**And** the message doesn't assume the user is a beginner
**And** the message doesn't imply the user has done something wrong
**And** the message maintains encouragement regardless of the period selected

