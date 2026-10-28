---
name: build-for-maintenance
description: "Prevents post-deployment failures by fixing their root cause during the build, not after launch. Use whenever scaffolding, building, or reviewing an app, API, or backend that will be deployed and handed to a client or put into real use. Covers the 8 categories of post-deployment breakage and maps each to the build-time decision that causes it: infrastructure/hosting hygiene, database/schema drift (indexes, pagination, migrations), dependency rot, AI/LLM output and cost decay, scale and concurrency bugs (race conditions, N+1 queries, missing transactions), third-party integration breakage, usage/cost limits, and handoff documentation. Trigger this any time the user is building something meant to go to production or to a client, asks how to make an app 'not break after deployment', 'keep working', be 'maintainable', or mentions post-deployment issues, app maintenance, production failures, or client handoff."
---

# Build for Maintenance

Apps rarely fail in production because of bad luck. They fail because of a build-time decision that hadn't been tested under real conditions yet — a missing index, an unbounded loop, a hardcoded model alias, a webhook with no logging. This skill exists to catch those decisions **while the code is being written**, not after a client reports something broken.

It covers 8 categories of post-deployment failure, each traced back to its build-time root cause:

1. **Infrastructure & Hosting Decay** — log/disk growth, wrong hosting tier, no SSL renewal check.
2. **Data & Database Drift** — missing indexes, no pagination, unversioned migrations.
3. **Dependency & Security Rot** — unmaintained packages, no pinning, unversioned third-party APIs.
4. **AI/LLM-Specific Decay** — brittle output parsing, no model pinning, no token caps.
5. **Scale & Performance Issues** — race conditions, missing transactions, N+1 queries, no caching.
6. **Third-Party & Integration Breakage** — no retries, no webhook logging, no fallback paths.
7. **Business & Cost Issues** — no per-user limits, no usage logging, no billing ceilings.
8. **Process & Human Issues** — no README/runbook, alerts not wired up, no defined ownership.

Full detail for each — root cause, the exact build-time fix with a checklist, a drop-in prompt for `CLAUDE.md`/`.cursorrules`, and an honest note on what still requires ongoing monitoring even with a perfect build — lives in `references/full-guide.md`. **Read that file before doing a real build or audit** — this summary is for orientation, not for citing specifics.

## How to use this skill

**When building a new app, feature, or API meant for real use (not a throwaway demo):**
Apply the build-time fixes from all 8 categories proactively as you write the code — don't wait to be asked. In particular, categories 2, 5, and 7 (database drift, scale/performance, cost limits) are almost entirely preventable and should never ship without their fixes in place: pagination on every list endpoint, indexes added alongside the queries that need them, transactions around multi-step writes, atomic operations on shared resources, and per-user usage limits from day one.

**When reviewing or auditing an existing app for production-readiness:**
Open `references/full-guide.md` and check the codebase against each of the 8 categories. Report findings by category, and for each issue found, note both the immediate fix and whether it's something a build-time fix fully resolves or something that will still need ongoing monitoring (per the Residual Risk notes in the reference file). Don't let categories 1, 4, 6, and 8 get treated as "fully fixed" — be explicit that they retain a monitoring component even after the build is corrected.

**When asked "how do I keep this app from breaking after deployment" or similar:**
Don't just point to monitoring tools. Walk through the 8 categories, explain which are build-time fixable right now versus which need ongoing infrastructure (uptime monitoring, error tracking, dependency alerts), and apply the build-time fixes immediately in the code if there's an active build session.

**When generating a `CLAUDE.md`/`.cursorrules` file for a new project:**
Pull the drop-in prompt blocks from `references/full-guide.md` for the categories relevant to the project's stack and include them alongside any existing security/engineering rules already in that file.

## Quick Reference

| # | Category | Preventable at build time? | Residual risk |
|---|---|---|---|
| 1 | Infrastructure & Hosting | Mostly | Provider/hardware outages |
| 2 | Data & Database Drift | Almost fully | None significant |
| 3 | Dependency & Security Rot | Partially | Future provider/API changes |
| 4 | AI/LLM-Specific Decay | Mostly | Model updates/deprecations |
| 5 | Scale & Performance | Almost fully | None significant |
| 6 | Third-Party Integration Breakage | Partially | External API contract changes |
| 7 | Business & Cost Issues | Fully | None significant |
| 8 | Process & Human Issues | Partially | Ongoing human monitoring |

## Reference files

- `references/full-guide.md` — the complete guide. Each category includes the root cause, the build-time fix with a full checklist, a drop-in prompt, and the residual risk that monitoring still needs to cover.

Companion to the `vibe-coding-rules` skill (23-area security & engineering checklist) — this skill focuses specifically on the build-time decisions that prevent post-deployment maintenance failures.
