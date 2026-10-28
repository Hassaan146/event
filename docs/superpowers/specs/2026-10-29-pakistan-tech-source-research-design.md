# Pakistan Tech-Event Source Research Design

## Goal

Expand Fieldnotes' Islamabad/Pakistan tech-event discovery sources using the
user's supplied leads and additional research. Test candidate sites against
real public access and the app's supported crawling methods before enabling
them.

## Scope

- Research Pakistani event publishers, technology organizations, developer
  communities, universities, incubators, tech media, and relevant global
  platforms that list events open to people in Pakistan.
- Include official organizer and institutional publisher pages as discovery
  leads; never contact organizers or bypass access controls.
- Record each candidate's name, canonical URL, source type, Pakistan/Islamabad
  relevance, evidence links, and live-check outcome.
- Test robots policy, HTTP access, redirects, public feed or supported event
  metadata, and the actual crawler result. Do not equate an accessible but
  empty source with a failed source.
- Enable only candidates with a public, robots-permitted path supported by
  the crawler. Remove failed/unsupported candidates from the active registry;
  document exclusions and reasons in the research record.
- Run all active sources after changes. Report attempted, successful-with-
  items, successful-empty, and failed/blocked counts, plus saved events.

## Approaches

1. Add every suggested domain without checking it: broad but misleading.
2. Research, live-check, enable only compliant crawler-compatible sources,
   then run the full registry: selected for useful coverage and honest status.
3. Build custom integrations for every platform: potentially broadest, but
   outside this research pass and unsafe to assume where APIs or terms are
   unclear.

## Design and boundaries

- Start with user-provided leads, then search for additional Pakistan-focused
  sources; retain verifiable URLs and supporting evidence.
- Check the exact source URL and robots policy before using the existing
  bounded crawler. Follow its supported RSS/Atom and public-page discovery
  behavior; do not spider arbitrary paths, scrape login-only/social pages, or
  evade blocks.
- Preserve the distinction between inaccessible, unsupported, robots-denied,
  redirected, valid-empty, and event-bearing results.
- Keep only evidence-grounded event details. Existing event filtering remains
  in force: technical event, future date, Islamabad/ICT or qualifying online
  relevance, and registration not confirmed closed.
- Do not add credentials, paid services, or unrelated frontend changes.

## Deliverables

- Updated active source registry and focused tests.
- Research record listing retained sources and excluded candidates with
  live-check evidence/reasons.
- Full source refresh results and any qualifying events found.

## Verification

- Run backend tests and Ruff; run frontend lint/build if shared interfaces or
  UI change.
- Execute the crawler against the full final registry and reconcile every
  configured source against its recorded attempt and outcome.
- Confirm registry contains no failed/unsupported candidates and that empty
  results remain visible as checked-but-empty, not silently deleted.
