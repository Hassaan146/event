# All-Source Crawling Implementation Plan

> **For agentic workers:** Implement inline, task by task. Each task includes its own tests and commit.

**Goal:** Attempt bounded public discovery for every crawl-eligible registry source and report accurate per-source outcomes.

**Architecture:** Keep `RSSConnector` and `EventDirectoryConnector`, add conservative declared-feed and structured-event discovery, and make crawl eligibility/outcome separate from registry presence. Persist each attempt's outcome in SQLite; drive refresh progress and source-index wording from those outcomes.

**Tech Stack:** Python 3.10+, FastAPI, SQLite, httpx, XML/HTML parsers, React + TypeScript + Vite.

## Global Constraints

- Respect robots.txt, published crawl delays, source terms, explicit host allowlists, and per-host throttling.
- Never bypass login, 403, CAPTCHA, anti-bot controls, or robots denial.
- Do not spider arbitrary site paths; fetch only configured URLs and declared feeds.
- Treat retrieved content and AI output as untrusted; store event facts only when grounded in captured source text.
- Keep the existing tech, future-date, Islamabad-relevance, and non-closed-registration filters.
- Keep third-party-network tests deterministic with mocked HTTP responses.
- Commit each independently verified task; push the final branch only after the complete suite passes.

---

### Task 1: Persist per-source crawl outcomes

**Files:**
- Modify: `backend/app/db.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_api.py`

**Interfaces:**
- Registry `crawl_policy` is one of `"eligible"`, `"review_required"`, or
  `"disallowed"`. Legacy `enabled` remains an API compatibility field equal to
  `crawl_policy == "eligible"`.
- Persisted `crawl_status` is one of `"pending"`, `"success"`, `"empty"`,
  `"robots_denied"`, `"forbidden"`, `"login_required"`, `"unsupported"`,
  `"parse_error"`, `"error"`, `"review_required"`, or `"disallowed"`.
- Produces `/api/sources` fields `crawl_status`, `last_checked`, `items_found`,
  `events_saved`, `last_attempted`, `last_error`, and `crawl_policy`.
- Produces additive refresh totals: `sources_attempted`, `sources_succeeded`,
  `sources_empty`, `sources_skipped`, `sources_failed`, plus existing event
  totals and errors.

- [ ] Add failing migration tests for an old `sources` table and newly initialized database.
- [ ] Add source status columns with safe `ALTER TABLE` checks; preserve prior
      `last_checked` and `last_error` values.
- [ ] Add API serialization tests for all source outcome fields.
- [ ] Run backend tests and Ruff; commit the schema/API change.

### Task 2: Add bounded public discovery connector

**Files:**
- Modify: `backend/app/sources.py`
- Test: `backend/tests/test_sources.py`

**Interfaces:**
- Add `DiscoveryConnector.fetch(source: Source) -> list[FeedItem]`.
- Keep `CONNECTORS` keyed by `"rss"`, `"event-directory"`, and `"discover"`.
- Parser extracts only declared RSS/Atom feeds and structured `Event` data or
  conservative event cards from the configured source page.

- [ ] Add mocked tests for HTML-declared RSS, Atom entries, schema.org Event,
      non-event JSON-LD, invalid feed links, and empty valid pages.
- [ ] Implement feed discovery and normalized event records with source URL
      provenance; include explicit start date/description in extracted text.
- [ ] Enforce same-host redirect and discovered-feed policy; reject unsafe
      destinations and oversized responses.
- [ ] Confirm robots-denied, timeout, 403, unsupported content, parser errors,
      and successful empty pages produce distinct outcomes.
- [ ] Run source tests and Ruff; commit connector and tests.

### Task 3: Attempt eligible registry sources and isolate failures

**Files:**
- Modify: `backend/sources.json`
- Modify: `backend/reference_sources.json`
- Modify: `backend/app/ingest.py`
- Test: `backend/tests/test_api.py`
- Test: `backend/tests/test_sources.py`

**Interfaces:**
- `refresh_sources(sources)` attempts every source whose policy is `eligible`,
  reports non-eligible sources as skipped with their configured reason, and
  continues after individual source failures.
- Persist exactly one latest result per source and accurate aggregate totals.

- [ ] Add a test registry with eligible, review-required, blocked, and
      failing sources; assert only eligible connectors fetch.
- [ ] Add integration assertions that every eligible source is attempted
      exactly once, statuses persist, and one failure does not stop the rest.
- [ ] Configure verified public-feed/page discovery sources as eligible;
      keep login-dependent, explicit policy-blocked, and unverified sources
      review-required until verified.
- [ ] Ensure event filtering and stale-record removal remain unchanged for
      fetched sources; count accepted events per source without duplicate
      inflation.
- [ ] Run full backend tests and Ruff; commit registry/ingestion changes.

### Task 4: Show truthful progress and source results

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/style.css`

**Interfaces:**
- `SourceItem` mirrors API crawl status and item/event counters.
- Refresh progress reports attempted/eligible totals and completed site count.
- Source index shows each site's latest outcome and reason; it never equates
  `listed`, `eligible`, and `success`.

- [ ] Add source-status presentation for success, empty, blocked, review
      required, skipped, and failed states.
- [ ] Derive progress/completion from source outcomes returned by API polling.
- [ ] Explain that “no matching events” means none qualified among successfully
      fetched sources and show how many sources were skipped or failed.
- [ ] Preserve accessible status announcements, keyboard focus, reduced motion,
      and mobile layout.
- [ ] Run frontend lint/build and focused accessibility checks; commit UI changes.

### Task 5: Document and verify all-source behavior

**Files:**
- Modify: `README.md`
- Test: `backend/tests/test_sources.py`
- Test: `backend/tests/test_api.py`

**Interfaces:**
- README documents per-source eligibility/status meanings, connector limits,
  refresh duration, and manual review needs.
- Tests assert source counts against the 60-entry index and validate policy
  completeness without hitting the network.

- [ ] Update source documentation to distinguish index size, eligible
      auto-check size, successful checks, and skipped/review-required entries.
- [ ] Add registry validation for unique IDs/URLs and explicit eligibility
      policy on every entry.
- [ ] Run backend tests, Ruff, frontend lint/build, dependency audit, and
      `git diff --check`.
- [ ] Run one live refresh, verify actual attempted/succeeded/skipped/failed
      counts, inspect per-source outcomes, and confirm API/UI agree.
- [ ] Commit docs and final verification changes; push `main`, then confirm
      clean status and matching remote commit.
