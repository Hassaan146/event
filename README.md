# Islamabad Tech Events

A local-first event finder for hackathons, meetups, tech events, and workshops relevant to Islamabad/ICT. The app uses a React + TypeScript SPA, a FastAPI backend, and SQLite. It does not contact event organizers or crawl event-hosting sites for discovery.

## What it does

- Reads ten curated Pakistani publisher/community RSS feeds plus AllEvents' Islamabad listings. Only event-like items with explicit date/location evidence are retained.
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

The enabled registry contains TechJuice, ProPakistani, Dawn, Express Tribune, The News International, Daily Times, Pakistan Observer, Startup Pakistan, Islamabad Scene, Geo News, Daily Pakistan, and the AllEvents Islamabad directory. RSS publishers are queried through their feeds; AllEvents uses its public Islamabad listing page. The RSS publishers are broad news/community sources, so event coverage can be sparse; the title/summary filter only keeps event-like entries with an extractable future date and Islamabad/online scope.

Each refresh checks the source host's `robots.txt`, uses a descriptive user agent, fetches sources sequentially, observes published crawl delays (with a two-second minimum per host), and applies a response-size limit. A source whose robots rules disallow access is skipped. Follow each publisher's terms and feed guidance before adding it. Captured feed/listing text is retained as provenance for each event.

The publisher feeds are search leads, not independently verified event facts. The app links to the secondary-source item. It does not follow result links or contact organizers. If a date or other detail is not in the captured text, it remains unknown rather than being guessed. Check the linked source before relying on an event listing.

PkEvents' Islamabad page was reviewed but is paused in the registry because the app's fetch environment receives HTTP 403; the app does not bypass this. The supplied Hack Scout name did not resolve to a verifiable public event directory URL, and The Grind site currently describes a coworking business rather than an events listing source, so neither is crawled.

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
