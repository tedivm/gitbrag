# Social Media Metadata Spec Delta

## ADDED Requirements

### Requirement: Basic HTML meta tags

The system MUST include standard HTML meta tags in the `<head>` section for search engines, browsers, and other tools that don't use Open Graph protocol.

#### Scenario: Display basic meta tags in base template

**Given** the base template is rendered for any page
**When** the HTML `<head>` section is generated
**Then** the following basic meta tags are included:

- `<meta name="description" content="{page_description}">`
- `<meta name="author" content="Robert Hafner">`
- `<meta name="keywords" content="github, open source, contributions, portfolio, performance review">`

**And** the description meta tag uses the same content as `og:description`
**And** the description is meaningful and under 160 characters for optimal display

#### Scenario: Override description in child templates

**Given** a child template defines a custom description
**When** the page is rendered
**Then** both the basic `<meta name="description">` and `<meta property="og:description">` use the custom description
**And** the description remains consistent across all meta tag types

### Requirement: Open Graph metadata for link previews

The system MUST include Open Graph meta tags in HTML pages to enable rich link previews when URLs are shared on social media platforms, messaging apps, and link aggregators.

#### Scenario: Display Open Graph metadata in base template

**Given** the base template is rendered for any page
**When** the HTML `<head>` section is generated
**Then** the following Open Graph meta tags are included:

- `<meta property="og:type" content="website">`
- `<meta property="og:site_name" content="git brag">`
- `<meta property="og:url" content="{current_page_url}">`
- `<meta property="og:title" content="{page_title}">`
- `<meta property="og:description" content="{page_description}">`
- `<meta property="og:image" content="{absolute_url_to_logo_image}">`

**And** the `og:url` uses the full absolute URL (including protocol and domain)
**And** the `og:image` uses an absolute URL to a static image file

#### Scenario: Override Open Graph metadata in child templates

**Given** a child template (e.g., `user_report.html`) extends the base template
**And** the child template defines custom `og_title` and `og_description` blocks
**When** the page is rendered
**Then** the custom title appears in `<meta property="og:title">`
**And** the custom description appears in `<meta property="og:description">`
**And** other Open Graph tags use base template defaults
**And** the page title in `<title>` also uses the custom title

#### Scenario: User report page displays username in Open Graph title

**Given** a user requests `/user/github/octocat`
**And** the report page is rendered successfully
**When** the Open Graph metadata is generated
**Then** `og:title` is set to "GitHub Contributions for @octocat - git brag"
**And** `og:description` includes summary statistics (e.g., "42 pull requests across 12 repositories")
**And** `og:url` includes the full URL with any query parameters (date range, options)
**And** `og:image` uses the user's GitHub profile picture URL from the report data
**And** `twitter:image` also uses the user's GitHub profile picture URL

#### Scenario: User report falls back to default image if profile picture unavailable

**Given** a user report is being rendered
**And** the user's GitHub profile picture URL is unavailable or returns an error
**When** the Open Graph metadata is generated
**Then** `og:image` falls back to `/static/images/og-image.png`
**And** the report still displays properly with the default branded image

#### Scenario: Validate Open Graph image requirements

**Given** the system includes an Open Graph image at `/static/images/og-image.png`
**When** the image is served
**Then** the image is at least 1200x630 pixels (optimal for most platforms)
**And** the image file size is under 1 MB for fast loading
**And** the image URL in meta tags is absolute (e.g., `https://gitbrag.com/static/images/og-image.png`)
**And** the image is served with appropriate cache headers (e.g., `max-age=86400`)

### Requirement: Twitter Card metadata for Twitter/X previews

The system MUST include Twitter Card meta tags in HTML pages to ensure optimal link previews specifically for Twitter/X platform.

#### Scenario: Display Twitter Card metadata in base template

**Given** the base template is rendered for any page
**When** the HTML `<head>` section is generated
**Then** the following Twitter Card meta tags are included:

- `<meta name="twitter:card" content="summary_large_image">`
- `<meta name="twitter:title" content="{page_title}">`
- `<meta name="twitter:description" content="{page_description}">`
- `<meta name="twitter:image" content="{absolute_url_to_logo_image}">`

**And** the `twitter:title` and `twitter:description` reuse the same Jinja2 blocks as Open Graph
**And** the `twitter:image` references the same image as `og:image`

#### Scenario: Twitter Card uses summary_large_image format

**Given** any page is rendered with Twitter Card metadata
**When** the meta tags are generated
**Then** `<meta name="twitter:card" content="summary_large_image">` is present
**And** the image referenced is suitable for large card display (1200x630px minimum)
**And** the card type supports prominent image display in Twitter feed

#### Scenario: Validate Twitter Card with Twitter Card Validator

**Given** a GitBrag page URL is entered into Twitter Card Validator (<https://cards-dev.twitter.com/validator>)
**When** the validator fetches and parses the page
**Then** no errors are reported
**And** the preview shows the correct title, description, and image
**And** the card type is displayed as "Summary Card with Large Image"
**And** all required fields are populated

### Requirement: Platform-agnostic metadata infrastructure

The system MUST implement metadata in a way that supports multiple platforms without duplication and allows easy extension for future platforms.

#### Scenario: Shared metadata blocks across platforms

**Given** the base template defines `og_title` and `og_description` Jinja2 blocks
**When** Open Graph and Twitter Card tags are rendered
**Then** both sets of tags reference the same Jinja2 blocks
**And** changes to title/description in child templates apply to both Open Graph and Twitter Card
**And** no duplication of metadata logic exists

#### Scenario: Default metadata for pages without custom overrides

**Given** a page (e.g., home page) does not override `og_title` or `og_description` blocks
**When** the page is rendered
**Then** `og:title` defaults to "git brag - GitHub Contribution Reports"
**And** `og:description` defaults to a general description of GitBrag's purpose
**And** all required metadata fields are populated with sensible defaults

#### Scenario: Test metadata with multiple platforms

**Given** a GitBrag report URL is shared on different platforms
**When** the URL is pasted into:

- Twitter/X
- LinkedIn
- Slack
- Facebook
- Discord

**Then** all platforms display a rich link preview
**And** the preview includes the page title, description, and image
**And** the preview is clickable and directs to the correct URL
**And** no platform shows broken images or missing metadata

## Related Specs

- **web-user-interface**: This change modifies the existing web interface spec by adding metadata requirements to HTML templates
