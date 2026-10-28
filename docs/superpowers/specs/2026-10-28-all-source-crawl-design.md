# All-Source Crawl Design

## Problem

The registry lists 60 sources, but refresh currently skips every source with
`enabled: false`; only 12 connectors run. The interface distinguishes indexed
from auto-check sources, but a successful refresh message can still leave the
impression that the whole index was searched. The empty event list therefore
does not establish that all 60 sources lack future events.

## Goal

Attempt bounded, public discovery for every source whose configured access
policy permits it. Report each source's actual outcome. Never claim that a
source was searched when it was skipped, blocked, or lacks a usable parser.

## Approaches

1. **Hybrid discovery (selected):** Keep known RSS and directory connectors;
   add conservative public-page discovery for other reviewed sources. Honor
   robots rules, timeouts, response-size limits, host pacing, and access
   restrictions. Report a precise outcome for every registry entry.
2. **Hand-built connector per source:** More accurate extraction per site, but
   high maintenance and cannot make login-gated, blocked, or unstable sites
   crawlable.
3. **Keep the current 12 auto-check sources:** Lowest risk, but does not meet
   the request to attempt the other eligible sources.

## Design

- Separate source-index membership, crawl eligibility, connector capability,
  and latest crawl outcome. Each registry entry has a `crawl_policy` of
  `eligible`, `review_required`, or `disallowed`; a reference entry must not be
  presented as a successful crawl merely because it exists in the registry.
- Keep the known RSS and AllEvents connectors. Add a bounded discovery
  connector that checks robots policy before requests, follows no login or
  anti-bot challenge, discovers declared RSS/Atom feeds, and extracts
  schema.org `Event` records or conservative event cards from the configured
  public page. Do not spider arbitrary site paths.
- Use explicit source policy for known login-dependent, blocked, or
  compliance-review sources. Such sources receive a truthful status and are
  not fetched contrary to policy. HTTP 403, robots denial, unsupported formats,
  parsing failure, and a valid page with no event items are distinct outcomes.
- Store `crawl_status` as one of `pending`, `success`, `empty`,
  `robots_denied`, `forbidden`, `login_required`, `unsupported`,
  `parse_error`, `error`, `review_required`, or `disallowed`.
- Attempt eligible sources on each refresh with per-host delays, bounded
  concurrency, request timeouts, redirect validation, and response-size caps.
  One source failure must not stop other source attempts.
- Persist last attempted time, outcome, fetched-item count, accepted-event
  count, and a concise error/reason per source. Keep the existing event rules:
  technology relevance, future date, Islamabad relevance, and not-confirmed-
  closed registration. AI extraction remains optional and evidence-grounded.
- Return aggregate attempted/succeeded/empty/skipped/failed counts from refresh.
  Polling and completion copy use recorded per-source outcomes, not enabled
  count arithmetic.
- The source index and refresh panel explain which sites were fetched, which
  were not eligible, and why. A successful empty result must be distinct from
  sources that were never checked.

## Boundaries and safety

- No authentication, session cookies, CAPTCHA solving, proxying, or access
  restriction bypass.
- Check the configured URL and every redirect target against the allowed
  source host; reject private, loopback, link-local, and metadata destinations.
- Honor robots rules and configured per-host rate limits. Keep source terms
  and access policy explicit; uncertain sources remain review-required instead
  of being silently scraped.
- Fetched page text is untrusted. Do not execute scripts or use fetched text as
  instructions to an LLM. Preserve evidence and validate extraction output.

## Verification

- Unit tests cover feed autodiscovery, RSS/Atom and Event JSON-LD parsing,
  source-specific policy, redirect/host safety, bounded limits, and outcome
  mapping.
- Refresh integration tests prove all eligible registry entries are attempted,
  blocked/review-required sources are not fetched, source errors are isolated,
  and only qualifying events are stored.
- Frontend tests/build and accessibility checks verify truthful progress,
  per-source result states, and empty-results messaging.
- Live verification is limited to compliant public source URLs and records
  actual outcomes; tests must not depend on third-party availability.
