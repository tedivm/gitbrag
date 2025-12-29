# README Rewrite Spec Delta

## ADDED Requirements

### Requirement: Project documentation and onboarding

The README MUST highlight the hosted web service at gitbrag.tedivm.com as the primary use case while maintaining comprehensive documentation for CLI usage.

#### Scenario: README leads with hosted service

**Given** a user opens the README.md file
**When** reading the first section after the title
**Then** the README prominently features gitbrag.tedivm.com
**And** includes a clear call-to-action link to the hosted service
**And** describes GitBrag's purpose and value proposition
**And** emphasizes the web interface as the easiest way to get started

#### Scenario: Web interface benefits are highlighted

**Given** the README describes available interfaces
**When** listing features and usage options
**Then** web interface advantages are clearly stated:

- No GitHub token setup required
- OAuth authentication flow
- Automatic caching and background generation
- Shareable URLs for reports
- Professional UI for viewing contributions
**And** these benefits appear before CLI documentation

#### Scenario: CLI documentation remains accessible

**Given** the README reorganization
**When** users need CLI information
**Then** CLI installation, usage, and options are still fully documented
**And** CLI documentation appears in a dedicated section
**And** CLI is presented as an alternative for power users or automation
**And** all existing CLI documentation is preserved

#### Scenario: README structure improves readability

**Given** the rewritten README
**When** users read through the document
**Then** sections follow a logical progression:

1. Project description and hosted service
2. Key features
3. Web interface quick start
4. CLI installation and usage
5. Configuration details
6. Development documentation
**And** each section has clear headings
**And** information is easy to scan

#### Scenario: Technical details are preserved

**Given** the README rewrite
**When** users need specific technical information
**Then** all existing content is retained:

- Installation instructions
- Environment variable configuration
- CLI options and examples
- Docker Compose setup
- Links to detailed documentation
**And** technical accuracy is maintained

#### Scenario: Call-to-action is clear and prominent

**Given** a new user visits the README
**When** deciding how to use GitBrag
**Then** a prominent link or button points to gitbrag.tedivm.com
**And** text encourages trying the service ("Try it now", "View your contributions", etc.)
**And** the call-to-action appears near the top of the README
**And** the value proposition is immediately clear

#### Scenario: README maintains professional tone

**Given** the rewritten README
**When** the content is reviewed
**Then** the tone is professional and welcoming
**And** the writing is clear and concise
**And** jargon is minimized or explained
**And** the README appeals to both new and experienced developers

## Cross-References

- Relates to `web-user-interface` spec (documenting primary interface)
- Relates to `contribution-report-cli` spec (documenting secondary interface)
- No functional code changes required
