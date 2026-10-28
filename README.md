# Islamabad Tech Events

A local-first event finder for hackathons, meetups, tech events, and workshops relevant to Islamabad/ICT. The app uses a React + TypeScript SPA, a FastAPI backend, and SQLite. It does not contact event organizers or crawl event-hosting sites for discovery.

## What it does

- Uses 11 Pakistani publisher/community RSS feeds plus 45 conservative public-page/feed discovery sources. Only event-like items with explicit date/location evidence are retained.
- Keeps source connectors modular so additional secondary publishers and community feeds can be added in `backend/sources.json`.
- Only displays events with a future event date. An unclear registration state is shown as **Unknown — verify on source**; closed registration is excluded.
- Requires explicit Islamabad/ICT evidence for in-person events, and Islamabad location or broad national/open-access evidence for online events.
- Shows only details supported by captured source text. Missing details stay marked as unknown.
- Optionally uses Groq for structured extraction. Each extracted value must include an exact supporting quote from the captured feed text or it is discarded.
- Stores events and refresh timestamps locally in SQLite. No paid services are required.
- Does not require sign-in; there is no user account or Google authentication flow in this version.

## Requirements

- Python 3.10+
- Node.js 20.19+ or 22.12+

## Run locally

1. Start the API:

   ```sh
   cd backend
   python -m venv .venv
   . .venv/bin/activate
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```

2. In another terminal, start the SPA:

   ```sh
   cd frontend
   npm install
   npm run dev
   ```

3. Open the Vite URL (normally `http://localhost:5173`). Use **Refresh sources** to run discovery. The API is at `http://localhost:8000`; interactive API docs are at `/docs`.

The SPA proxies `/api` requests to the local API. For a different API address, set `VITE_API_URL` before starting/building the frontend.

## Optional Groq extraction

Copy `backend/.env.example` to `backend/.env` and set `GROQ_API_KEY`. The key is read only by the backend and is never sent to the browser. `GROQ_MODEL` is optional and defaults to `llama-3.3-70b-versatile`. Without a key, conservative local extraction is used.

## Project skills

The skills from [Hassaan146/claude-skills](https://github.com/Hassaan146/claude-skills) are installed in `.claude/skills/` for this repository. This includes all 438 top-level skill folders and their supporting assets, copied from upstream revision `033736c5ab973f55b783cd1251571e176195f949`. To refresh them, copy the source repository's top-level skill directories into `.claude/skills/`; review upstream changes before replacing the checked-in copies.

## Sources, compliance, and data quality

The source index currently contains 56 unique websites: 11 RSS feeds and 45 conservative public-page/feed discovery candidates. The expanded index adds Pakistan-focused event communities, event directories, incubators, universities, and technology publishers. Sources retained after prior live checks remain distinct from newly researched additions; each source's actual live outcome is shown after refresh.

The retained index covers Pakistani publisher feeds and secondary sources such as Pakistan Hackathons, The Grind, Meetup, Eventbrite Islamabad, dev.events Pakistan, Pakistani Startup, Conference Alerts, Call4Paper, Sessionize, Ignite, Indus AI Week, PSEB / TechDestination, National CERT Pakistan, DigitalPakistan.io, GDG, IEEE, Microsoft Reactor, NUST, NUTECH, LUMS, COMSATS, GIKI, Air University, IT University Lahore, IBA Karachi, NED University, NIC Islamabad, NIC Karachi, ASPIRE Pakistan, Bano Qabil, Code for Pakistan, AI Tinkerers, lablab.ai, Invest2Innovate, PhoneWorld, TechMag Pakistan, Startup Grind, and TiE. Removed sources are no longer shown or retried automatically. Sources are not used to contact organizers or to crawl event-hosting pages as discovery sources.

See the [source research and full-crawl report](docs/source-research/pakistan-tech-event-sources.md) for per-source outcomes, retained empty results, and excluded candidates.

Each refresh attempts all 56 indexed sources that have an `eligible` crawl policy. Eligibility means the source is attempted; it does not mean the site is reachable or returns listings. The source index records a separate outcome for every source: listings found, a valid empty result, explicit robots denial, unavailable robots instructions, forbidden/login-required access, unsupported content, parse errors, network errors, or a policy skip. The refresh summary reports attempted, succeeded, empty, failed/blocked, and skipped totals; an empty event list is not presented as evidence that no events exist.

The crawler checks each source host's `robots.txt`, uses a descriptive user agent, limits concurrency to four sources, serializes requests per host, observes published crawl delays (with a two-second minimum per host), refuses redirects, validates and pins resolved public addresses for direct connections, rejects compressed responses, and caps streamed response bodies at 2 MB (robots files at 256 KB). Discovery follows only declared RSS/Atom feeds on the same origin, up to three feeds per page; it does not spider arbitrary paths. Sources denied by robots or whose destination cannot be validated are not fetched. Follow each publisher's terms and feed guidance before adding it. Captured feed/listing text is retained as provenance for each event.

The app now requires a clear technical topic (or an explicitly named hackathon) alongside an event type. Non-technical conference/workshop listings are discarded, and previously stored listings are removed when they fail this filter on refresh. The publisher feeds are search leads, not independently verified event facts. The app links to the source item. If a date or other detail is not in captured text, it remains unknown rather than guessed. Check the linked source before relying on an event listing.

Individual sites may block automated access, require sign-in, return unsupported pages, or have no compatible public event data. The crawler does not bypass those controls; each outcome appears separately in the source index. For example, a previously observed 403 from PkEvents is now displayed as a blocked result rather than silently omitted. Feed discovery is limited to declared same-origin feeds, and any event details missing from captured text remain unknown.

## Tests

```sh
cd backend
python -m pip install -r requirements.txt
pytest
ruff check app tests
```

```sh
cd frontend
npm install
npm run lint
npm run build
```
