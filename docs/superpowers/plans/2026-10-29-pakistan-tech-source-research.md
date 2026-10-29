# Pakistan Tech-Event Source Research Implementation Plan

> **For agentic workers:** Execute inline task-by-task; keep each registry change and its test evidence reviewable.

**Goal:** Expand Pakistan-focused tech-event discovery using researched, publicly reachable, robots-permitted, crawler-compatible sources, then report and remove failed candidates.

**Architecture:** Research the user-provided leads plus a bounded set of additional Pakistan-focused sources. Add candidates to the existing registries, run the current crawler against all candidates, remove only sources with access, policy, or parser failures, and retain valid empty sources with a distinct status. Preserve evidence and exclusions in a research record.

**Tech Stack:** Python 3.10+, FastAPI crawler, JSON source registries, pytest, Ruff, Markdown research record.

## Global Constraints

- Never contact organizers or bypass access restrictions.
- Respect source terms, robots guidance, and rate limits.
- Enable only candidates with a public, robots-permitted path supported by the crawler.
- Do not equate an accessible but empty source with a failed source.
- Keep evidence-grounded event details and existing event eligibility rules.
- Do not add credentials, paid services, or unrelated frontend changes.

---

### Task 1: Research and preflight candidate sources

**Files:**
- Read: `backend/sources.json`
- Read: `backend/reference_sources.json`
- Read: `backend/app/sources.py`
- Read: `docs/superpowers/specs/2026-10-29-pakistan-tech-source-research-design.md`
- Create: `docs/source-research/pakistan-tech-event-sources.md`

**Interfaces:**
- Consumes: user-provided source leads and existing `Source` registry entries.
- Produces: candidate records with canonical URL, source focus, evidence URL, robots/access result, and proposed crawler-supported discovery URL.

- [x] **Step 1: Build candidate inventory**
  Research the user-provided organizations/platforms and additional Pakistan-focused tech-event publishers. Include Islamabad/ICT university, community, government, incubator, event directory, and tech-media sources; include global platforms only where they expose Pakistan-relevant public discovery.
- [x] **Step 2: Verify evidence and source URLs**
  For each candidate, visit its canonical site and identify a public event/feed page. Record supporting URLs and mark uncertain or unverified claims as such; do not treat search snippets as proof of crawler compatibility.
- [x] **Step 3: Preflight public access**
  Check candidate URLs and robots guidance using the project user-agent and non-invasive requests. Classify redirect, denied, unavailable, unsupported, or reachable without evading controls.
- [x] **Step 4: Add only preflight-eligible candidates**
  Add candidates with a supported public feed or discovery page to the existing JSON registries using current `Source` field conventions. Do not yet remove candidates solely because a live response contains zero events.
- [x] **Step 5: Validate registry structure**
  Run `cd backend && .venv/bin/python -m pytest -q tests/test_sources.py` and `cd backend && .venv/bin/ruff check app tests`. Resolve duplicate IDs, URLs, or malformed registry data before live crawling.
- [x] **Step 6: Commit research and candidate registry**
  ```bash
  git add docs/source-research/pakistan-tech-event-sources.md backend/sources.json backend/reference_sources.json backend/tests/test_sources.py
  git commit -m "research: add vetted Pakistan tech event sources"
  ```

### Task 2: Crawl all candidates and remove failed sources

**Files:**
- Modify: `backend/sources.json`
- Modify: `backend/reference_sources.json`
- Modify: `backend/tests/test_sources.py`
- Modify: `backend/tests/test_api.py` only if a behavior change needs an API regression test.
- Update: `docs/source-research/pakistan-tech-event-sources.md`

**Interfaces:**
- Consumes: eligible source registry and `POST /api/refresh`.
- Produces: per-source actual crawl outcomes and a final active registry containing no sources that failed access, robots, redirect, or supported-content checks.

- [x] **Step 1: Run every eligible source**
  Execute one full backend refresh with the candidate registry and retain the complete source-status response. Reconcile expected eligible source IDs against attempted/status IDs.
- [x] **Step 2: Classify each result**
  Keep sources with event results and sources that completed a valid empty crawl. Exclude robots-denied, unreachable, unsafe-redirect, unsupported, or parse-failing candidates; record exact outcome and timestamp. Do not label empty as a failure.
- [x] **Step 3: Add regression assertions**
  Update registry tests to assert unique IDs/URLs, all active entries eligible, and that removed failed candidates are absent. Update API tests only if registry behavior changes.
- [x] **Step 4: Rerun tests and lint**
  Run `cd backend && .venv/bin/python -m pytest -q && .venv/bin/ruff check app tests`.
- [x] **Step 5: Run the final registry**
  Refresh once more after exclusions. Verify every remaining source was attempted and no remaining source reports a failure or skip. Summarize event-bearing, valid-empty, and excluded sources separately.
- [x] **Step 6: Commit and publish branch**
  ```bash
  git diff --check
  git add backend/sources.json backend/reference_sources.json backend/tests/test_sources.py backend/tests/test_api.py docs/source-research/pakistan-tech-event-sources.md
  git commit -m "feat: verify Pakistan tech event source coverage"
  git push -u origin research-pakistan-tech-sources
  ```

## Self-review

- Research evidence and live crawl outcomes are kept distinct.
- Empty results remain enabled when the crawler completed successfully.
- Removed candidates retain exclusion reasons in the research record.
- No custom scraper, login flow, anti-bot workaround, or unrelated UI change is included.

### Follow-up: additional university source sweep

- [x] Tested six additional public pages with the existing compliant crawler.
- [x] Added QAU's reachable events archive; recorded 11 parsed raw items.
- [x] Kept the failed FAST, Bahria, Air University, IEEE vTools, and PROCOM URLs out of the registry.
- [x] Re-ran full 57-source refresh, backend tests/Ruff, and frontend lint/build.
