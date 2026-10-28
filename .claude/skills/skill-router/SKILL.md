---
name: skill-router
description: >-
  Automatic skill dispatcher over the whole catalog. The instant it is
  invoked, CAVEMAN mode activates (always, before anything else — every
  routed reply is compressed). Then it reads the user's prompt, matches it
  to skill CATEGORY BUNDLES (a frontend request triggers ALL frontend/UI-UX
  skills, not one), adds a VISUAL layer for explanations and learning plans
  (visual-page-builder, explainer-graphic, workflow-visualizer), and runs
  everything in order. Use when the user says "skill router", "use skill
  router", "/skill-router", "route this", "skill filter", or wants skills
  chosen automatically.
---

# Skill Router v2

Route any prompt to the right skills automatically. The user never needs
to know the catalog — the router knows it for them.

## Step 0 — ALWAYS FIRST: caveman on

The moment the router is invoked, activate the **caveman** skill (lite
intensity) BEFORE reading anything else. Every routed reply is
compressed-caveman by default — full technical accuracy, minimum words.
This is the only always-on overlay (token-optimization is NOT auto-applied).

Opt-out: "no caveman" / "normal speech" / "full detail" turns it off
until the user asks it back. Caveman compresses PROSE only — code,
files, decks, pages, and diagrams always come out complete.

## Step 1 — parse the prompt

Extract: deliverable(s) · domain(s) · action(s) · and the LEARNING/
EXPLAINING flag (is the user trying to understand or learn something?).

## Step 2 — match CATEGORY BUNDLES

When a prompt hits a category, trigger the WHOLE bundle (every member
that exists in the current session's skill list — check it live, the
catalog grows):

| Category (trigger examples) | Bundle — trigger ALL of these |
| --- | --- |
| **Frontend / UI-UX** ("make a frontend page", landing page, dashboard, component, redesign) | ui-ux-pro-max · ui-styling · distinctive-frontend · frontend-design · animated-website · web-artifacts-builder · a11y-audit |
| **Visual output** (diagram, infographic, visual explanation, "show me") | explainer-graphic · visual-page-builder · workflow-visualizer · slide-deck-builder |
| **Research / explain** ("explain X", "what is", random topic questions) | quick-research (+ Visual output bundle, see Step 3) |
| **Learning** ("learn X", "roadmap", "in two weeks") | learning-path-generator · workflow-visualizer |
| **Docs & office** (report, deck, sheet, PDF) | docx / pptx / xlsx / pdf · doc-coauthoring |
| **Sales & marketing** (leads, outreach, copy, SEO, ads, pricing) | copywriter-skill · seo · pricing · sales-skill · prospecting · ad-creative · ab-test-setup · app-store-optimization · product-position · channel-expert |
| **Engineering quality** (build feature, fix bug, review, ship) | brainstorming · writing-plans · test-driven-development · systematic-debugging · requesting-code-review · verification-before-completion · vibe-coding-rules |

Prompts spanning categories trigger multiple bundles. Within a bundle,
skip members that clearly don't apply to the specific ask (e.g., no
a11y-audit for a throwaway mockup) — but default to inclusion.

## Step 3 — the VISUAL LEARNER rule

People learn visually. Whenever the route produces an explanation,
answer, plan, or workflow, ADD a visual deliverable by default:

- Topic explanation → **explainer-graphic** or **visual-page-builder**
  (a self-contained visual page of the answer)
- Learning plan / "learn X in N weeks" → **learning-path-generator** +
  **workflow-visualizer** (the plan as an interactive visual roadmap)
- Any process/system description → **workflow-visualizer**
- Comparisons/data → chart or slide via **slide-deck-builder**

Skip the visual only if the user says "text only" or the answer is
one line.

## Step 4 — order & run

Order: research/brainstorm → plan → create → style/polish →
visualize → review/verify. Invoke each selected skill with the Skill
tool, in order, each phase feeding the next.

## Step 5 — announce the route (one line, always first)

`route: [caveman] quick-research → visual-page-builder`

## Step 6 — HARD CONTRACT: announced = invoked

The route line is a promise. Every skill named in it MUST actually be
invoked with the Skill tool — caveman included — before the final answer
is written. Never merely mention or "apply the spirit of" a skill:

1. After announcing, call the Skill tool for EACH routed skill, in
   order. Wait for each to load; follow its loaded instructions for the
   corresponding part of the work.
2. The final answer must be produced AFTER all invocations, using what
   they loaded.
3. Close every routed reply with a one-line receipt confirming real
   usage: `used: caveman ✓ quick-research ✓ visual-page-builder ✓`
4. If a skill fails to invoke, mark it `✗` in the receipt and continue —
   never silently drop it from the receipt.
5. A route line without matching Skill-tool calls is a broken route —
   if you notice instructions were skipped, invoke the missing skills
   and redo the affected part before delivering.

## Examples

- "Make a frontend page for my product" →
  `route: [caveman] ui-ux-pro-max → ui-styling → distinctive-frontend →
  frontend-design → animated-website → a11y-audit` (whole frontend bundle)
- "Random question: explain how DNS works" →
  `route: [caveman] quick-research → explainer-graphic` — compressed
  words + a visual of the answer
- "I want to learn video editing in two weeks" →
  `route: [caveman] learning-path-generator → workflow-visualizer` — the
  two-week plan AND its visual roadmap
- "Write cold outreach for gyms" →
  `route: [caveman] prospecting → copywriter-skill → ad-creative`
- "What's 2+2?" → `route: [caveman] none` — caveman answer, no ceremony.

## Rules

- Caveman first, every time, no exceptions (unless opted out).
- Bundles fire as a unit — a matched category means ALL its applicable
  members, not the single best one.
- Read the live session skill list every time; never invent skill names.
- If a selected skill fails to load, continue the route and note it in
  half a line.
- Never ask which skill to use — deciding is the router's job. Ask only
  when the PROMPT itself is too ambiguous to act on.
