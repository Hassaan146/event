# Build for Maintenance — Preventing Post-Deployment Failures at Build Time

Most apps don't break because of bad luck after deployment. They break because of a decision made (or skipped) during the build that simply hadn't been tested by real-world conditions yet. This guide maps the eight categories of post-deployment failure back to their build-time root cause, gives the concrete fix to apply *while building*, and is honest about which part of each category can never be fully solved at build time — because it depends on something outside the code (a provider, infrastructure, or a human).

Each category includes:
- **Root cause** — what build-time decision actually causes this failure later.
- **Build-time fix** — the rule to follow while writing the code, with a checklist.
- **Drop-in prompt** — paste into `CLAUDE.md` / `.cursorrules` to enforce it automatically.
- **Residual risk** — what still requires ongoing monitoring even if the build is done right.

---

## 1. Infrastructure & Hosting Decay

**Root cause:** No log rotation or cleanup logic written in. No alerting configured before launch. Hosting tier chosen for a demo, not for real load.

> **Build-time fix: Build infrastructure hygiene in from day one**
> - Add log rotation / cleanup jobs for logs, temp files, and uploaded files at build time, not after the disk fills up.
> - Choose a hosting tier based on projected real load, not the cheapest demo tier.
> - Set database connection pool limits explicitly instead of relying on defaults.
> - Verify SSL certificate auto-renewal is actually configured — don't assume the platform handles it.
> - Avoid "sleeps on idle" free-tier hosting for anything client-facing.

**Drop-in prompt:**
```
When scaffolding deployment config, add log rotation and cleanup jobs for logs,
temp files, and uploads. Set explicit database connection pool limits instead of
relying on defaults. Flag if the chosen hosting tier or free-tier plan is
unsuitable for expected production load.
```

**Residual risk:** Hardware and provider outages remain genuinely external — uptime monitoring is still required even with a perfect build.

---

## 2. Data & Database Drift

**Root cause:** Missing indexes, no pagination written into list endpoints, migrations applied ad-hoc instead of version-controlled.

> **Build-time fix: Design the schema and queries for scale from the first migration**
> - Add an index on every field used in `WHERE`, `JOIN`, or `ORDER BY` in the same migration that introduces it.
> - Paginate every list endpoint by default, even when test data is small.
> - Use a versioned migration tool (Prisma Migrate, Alembic, Flyway) from the very first schema change.
> - Set storage quotas/alerts during initial setup, not as an afterthought.

**Drop-in prompt:**
```
Every database query that fetches a list must include pagination. Every field
used in a WHERE, JOIN, or ORDER BY clause must have an index added in the same
migration that introduces it. Use a versioned migration tool from the first
schema change — never apply schema changes by hand.
```

**Residual risk:** Essentially none. This category is almost entirely preventable at build time.

---

## 3. Dependency & Security Rot

**Root cause:** Unmaintained packages adopted without checking, no version pinning, no awareness that a provider's API can change.

> **Build-time fix: Choose dependencies defensively**
> - Check a package's last update date and maintenance activity before adopting it.
> - Pin exact versions in lockfiles; review changelogs before any upgrade.
> - Prefer providers/SDKs with explicit, versioned APIs over those that mutate response shapes without notice.

**Drop-in prompt:**
```
Before adding a new dependency, check it has been updated within the last 12
months and has no open critical CVEs. Pin exact versions in the lockfile. When
integrating a third-party API, use its versioned endpoint explicitly rather
than an unversioned or "latest" endpoint.
```

**Residual risk:** Future deprecations and provider policy changes are inherently ongoing. Dependabot/Renovate-style alerts are still needed — good build choices reduce the risk but can't eliminate it.

---

## 4. AI / LLM-Specific Decay

**Root cause:** Brittle output parsing that assumes one exact format, no token/cost caps, no model version pinned.

> **Build-time fix: Build AI integrations defensively, not optimistically**
> - Pin a specific model version in API calls where the provider supports it, instead of a "latest" alias.
> - Validate LLM output with a schema-based parser that has a fallback/retry path if the format doesn't match exactly.
> - Set `max_tokens` and per-user/session budgets at the integration layer from the start.
> - Log every LLM call's token usage and cost from day one.

**Drop-in prompt:**
```
Pin a specific model version in API calls rather than using a "latest" alias.
Validate and gracefully handle LLM output with a schema-based parser that has a
fallback path if the format doesn't match exactly. Set max_tokens and log token
usage per call from day one.
```

**Residual risk:** Provider-side model updates and deprecations remain an ongoing risk that needs monitoring even with disciplined build practices.

---

## 5. Scale & Performance Issues

**Root cause:** Race conditions, missing transactions, N+1 queries, and no caching — all written into the code from the start, just untested under real concurrency.

> **Build-time fix: Write for concurrent, large-scale usage on day one**
> - Wrap multi-step writes in database transactions from the first implementation.
> - Use atomic operations or row-level locking on any shared, frequently-updated resource (balances, inventory, counters).
> - Batch or join queries instead of looping — never write a loop that hits the database once per item.
> - Add caching for expensive or repeated computations at the point the function is written, not after a complaint.

**Drop-in prompt:**
```
Any multi-step database write must be wrapped in a transaction from the first
implementation. Any loop that would call the database once per iteration must
instead be rewritten as a batched query or join. Any shared, frequently-updated
resource (counters, balances, inventory) must use atomic operations or
row-level locking.
```

**Residual risk:** Almost none — this category is close to fully preventable at build time if these rules are actually followed.

---

## 6. Third-Party & Integration Breakage

**Root cause:** No retry/fallback logic on external calls, no logging on webhook delivery, assuming every external call succeeds.

> **Build-time fix: Build integrations assuming they will eventually fail**
> - Add retry logic with exponential backoff for any external API call that can transiently fail.
> - Log every webhook received and its processing result — success or failure — so problems are visible immediately, not reported by a client.
> - Build an explicit fallback/error path for every external dependency.

**Drop-in prompt:**
```
Every external API call must have retry logic with exponential backoff for
transient failures. Every webhook handler must log receipt and processing
result, success or failure. Never assume a third-party call succeeds — always
handle the failure path explicitly.
```

**Residual risk:** A provider unilaterally changing their API contract is genuinely outside build-time control — integration health monitoring is still needed.

---

## 7. Business & Cost Issues

**Root cause:** No per-user/per-plan limits built into the data model or middleware, no usage logging from day one.

> **Build-time fix: Treat usage limits as a feature, not an afterthought**
> - Add per-user and per-plan usage limits as middleware applied to every metered endpoint from the start.
> - Log usage (API calls, tokens, storage) per user/account from the first version.
> - Build a hard enforced ceiling — not just a logged warning — for any resource tied to billing.

**Drop-in prompt:**
```
Add per-user and per-plan usage limits as middleware applied to every metered
endpoint, not as a later patch. Log usage per user/account from the first
version. Any resource tied to billing must have a hard enforced ceiling, not
just a logged warning.
```

**Residual risk:** None of significance — this is a pure code/architecture decision and is fully preventable at build time.

---

## 8. Process & Human Issues

**Root cause:** No README, no runbook, no alerting wired up, no defined ownership for what happens after handoff.

> **Build-time fix: Build the handoff, not just the app**
> - Write a README and a short runbook ("what to do when X breaks") before considering the build done.
> - Wire error and uptime alerts to a real notification channel (email/Slack/SMS) as part of the build, not a follow-up task.
> - Document who owns monitoring post-handoff, even if the answer is "you, weekly."

**Drop-in prompt:**
```
Before marking a build complete, generate a README and a short runbook
covering common failure scenarios and how to resolve them. Wire error and
uptime alerts to an actual notification channel as part of the build, not as a
follow-up task.
```

**Residual risk:** The actual ongoing act of a human checking those alerts is a commitment, not a code problem. Building the alerting in is necessary but not sufficient — someone still has to watch it.

---

## Summary Table

| # | Category | Preventable at build time? | Residual risk after a good build |
|---|---|---|---|
| 1 | Infrastructure & Hosting | Mostly | Provider/hardware outages |
| 2 | Data & Database Drift | Almost fully | None significant |
| 3 | Dependency & Security Rot | Partially | Future provider/API changes |
| 4 | AI/LLM-Specific Decay | Mostly | Model updates/deprecations |
| 5 | Scale & Performance | Almost fully | None significant |
| 6 | Third-Party Integration Breakage | Partially | External API contract changes |
| 7 | Business & Cost Issues | Fully | None significant |
| 8 | Process & Human Issues | Partially | Ongoing human monitoring |

**The pattern:** categories 2, 5, and 7 are almost entirely build-time mistakes wearing a "deployment problem" costume. Categories 1, 4, 6, and 8 are partially preventable at build time but always keep a genuine ongoing-maintenance component, because they depend on something outside the code. Category 3 is the most "you did nothing wrong, the world changed" of the eight.
