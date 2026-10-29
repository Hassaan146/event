# Pakistan Tech-Event Sources: Research and Crawl Results

## Scope and method

This pass prioritized Pakistan-based event communities, technology publishers,
incubators, universities, and secondary event directories, with an Islamabad
focus. Public pages were checked using the existing bounded crawler, which
honors `robots.txt`, refuses redirects, pins validated public IPs, applies
per-host delays, and limits response size. No organizer contact, login, or
access-control bypass was used.

The source registry is a discovery index, not a claim that every publisher has
current events. A `success` result means the connector parsed listing/feed
items; an `empty` result means it fetched a page successfully but parsed no
items. Neither status alone establishes that a source contains or lacks a
qualifying event.

## Final full-registry run

The first final run completed at **2026-10-29 17:37:27 UTC**:

| Result | Count |
|---|---:|
| Configured and attempted | 57 |
| Parsed items from sources | 430 |
| Successful sources with parsed items | 29 |
| Successful empty sources | 28 |
| Failed or blocked sources | 0 |
| Skipped sources | 0 |
| Qualifying future event records saved or updated | 3 |

The three saved events were AWS Student Community Day Islamabad (Oct 31),
Open Source Hack Day — CloudCon Day 2 (Nov 1), and Open Source Hackathon NUST
(Nov 3). Their registration state remains **Unknown — verify on source**;
the listing does not establish team-size or eligibility details when those
facts were absent from captured text.

The added Quaid-i-Azam University events page returned 11 raw event items.
These are not necessarily technology-related or eligible for display; each
item still goes through the normal topic, future-date, and Islamabad/online
filters.

### Sources that yielded parsed items

Counts are raw feed/listing items, not accepted future Islamabad events.

| Source | Parsed items |
|---|---:|
| TechJuice | 15 |
| ProPakistani | 10 |
| Dawn | 26 |
| Express Tribune Technology | 27 |
| The News International Technology | 7 |
| Daily Times | 10 |
| Pakistan Observer | 10 |
| Startup Pakistan RSS | 10 |
| Islamabad Scene | 10 |
| Geo News | 20 |
| Daily Pakistan | 10 |
| PhoneWorld | 20 |
| Pakistan Hackathons | 8 |
| Meetup Islamabad technology events | 8 |
| Ignite events | 10 |
| Pakistani Startup | 18 |
| PSEB / TechDestination | 10 |
| NUST events | 13 |
| COMSATS | 4 |
| GIKI | 10 |
| Air University | 3 |
| IT University Lahore | 10 |
| TechMag Pakistan | 11 |
| ASPIRE Pakistan | 10 |
| dev.events Pakistan | 103 |
| NIC Karachi | 10 |
| Eventbrite Islamabad technology | 6 |
| Invest2Innovate | 10 |
| Quaid-i-Azam University events | 11 |

Eventbrite's broad browse results can be noisy; every event still goes through
the app's topic, date, and Islamabad/online eligibility filters.

### Reachable sources with valid empty crawl results

These remain indexed rather than being mislabeled as broken:

PkEvents Islamabad; PkEvnts; The Grind; GDG Pakistan; Conference Alerts;
Call4Paper; Sessionize; Indus AI Week Sindh; DigitalPakistan.io; GDG Community;
IEEE; Microsoft Reactor; Cisco Events; LUMS; IBA Karachi; NED University;
Startup Grind; TiE Global; Bano Qabil; Code for Pakistan; lablab.ai; Founder
Institute Islamabad; AI Tinkerers Lahore; AI Tinkerers Karachi; Friends of
Figma Lahore; NIC Islamabad; NUTECH; and The Nest I/O.

Several empty sources are JavaScript-rendered, archive-style, or community
landing pages. They were fetched successfully by the supported connector, but
the connector found no listing items during this run. This does not imply the
site has no events; it does mean this run did not extract any.

## Candidate exclusions

### Removed after a historical candidate crawl

| Source | Observed result | Decision |
|---|---|---|
| PKCERT events (`https://pkcert.gov.pk/events.asp`) | The crawler could not check `robots.txt` (`RobotsFetchError`, underlying `ConnectError`) during the historical 57-candidate run. | Removed from the active registry before the 56-source baseline run and remains absent from the current 57-source registry. This is a failed access-policy check, not evidence that the site has no events. |

### Not enabled after exact-URL preflight

| Candidate URL | Observed result | Reason not enabled |
|---|---|---|
| `https://devpost.com/hackathons` | HTTP 403 | Access denied |
| `https://mlh.io/seasons/2026/events` | Robots check redirected | Crawler refuses redirects; permission could not be established |
| `https://dorahacks.io/hackathon` | `robots.txt` returned HTTP 405 | Permission could not be established |
| `https://genglobal.org/events` | `robots.txt` returned HTTP 403 | Permission could not be established |
| `https://itcnasia.com/events/` | `robots.txt` returned HTTP 406 | Permission could not be established |
| `https://digiskills.pk/` | TLS certificate verification failure while checking robots | Public connection could not be verified |
| `https://procom.com.pk/` | HTTP 404 | Candidate page unavailable |
| `https://plan9.pitb.gov.pk/` | Robots check timed out | No usable permission response |
| `https://10pearls.com/events/` | HTTP 404 | Candidate event page unavailable |
| `https://devopsdays.org/events/2026-islamabad/welcome/` | Response exceeded the crawler's 2 MB limit | Direct page unsupported under current bounded-fetch policy; dev.events Pakistan remains enabled as an alternate listing source |
| `https://pasha.org.pk/events/` | Redirected | Crawler refuses redirects |
| `https://cust.edu.pk/events/` | Malformed HTML (`ParseError: mismatched tag`) | Current parser could not safely parse the response |
| `https://islamabad.wordcamp.org/2026/` | 16 items parsed, but 2026 event dates were Oct 24–25 | Historical event page; no future edition was confirmed |
| `https://lu.ma/pakistan` | Robots check redirected | Crawler refuses redirects; permission could not be established |
| `https://nu.edu.pk/Events` | HTTP 404 | Exact candidate route unavailable; generic homepage is not an event feed |
| `https://www.bahria.edu.pk/events/` | HTTP 500 | Exact candidate route returned server error |
| `https://www.au.edu.pk/Pages/Events/Events.aspx` | HTTP 404 | Exact candidate route unavailable |
| `https://events.vtools.ieee.org/m/events` | HTTP 404 | Exact candidate route unavailable |

These results are time-sensitive. A blocked or unavailable candidate may be
reconsidered after its public access or event page changes, without bypassing
the restriction. The earlier 56-source run was a baseline; the current final
57-source run below includes QAU and excludes PKCERT.

## Registry additions and URL improvements

The final index has **57 unique sources**: 11 RSS feeds and 46 public-page
discovery sources. Added sources include Bano Qabil, Code for Pakistan, ASPIRE
Pakistan, lablab.ai, dev.events Pakistan, Founder Institute Islamabad, AI
Tinkerers Lahore and Karachi, Friends of Figma Lahore, NIC Karachi, Eventbrite
Islamabad technology, NIC Islamabad, NUTECH, Invest2Innovate, The Nest I/O,
PhoneWorld, and Quaid-i-Azam University. Existing entries were updated to use
the verified Indus AI Week Sindh events site, NUST events page, and Meetup's
Islamabad technology browse page.

## Additional live preflight sweep

The follow-up checked public pages from Pakistan's university, IEEE, event
platform, and hackathon ecosystem using the same compliant discovery connector.
Exact outcomes and decisions are recorded in the exclusion table above. The
one crawler-compatible additional publisher was:

| Candidate URL | Result | Decision |
|---|---|---|
| `https://qau.edu.pk/events/` | Reachable; 11 parsed items | Added as `qau-events`; valid even if later crawls return empty |

These are URL-level outcomes, not claims that the organizations themselves
never publish events. The final 57-source refresh was then run with QAU
included; all configured sources were attempted, with no failures or skips.

## Limitations

The current connector supports RSS/Atom, public event cards, and Event
JSON-LD; it does not execute page JavaScript or spider arbitrary links. Some
sites visibly discuss events but do not expose data in these supported forms.
No custom per-site integration was added in this pass. The app preserves
source provenance and leaves unavailable facts unknown rather than inventing
them.

## Follow-up: focused tech-training and community sources

The later focused check added two Pakistan-relevant sources after testing their
exact public URLs with the same discovery connector:

| Source | Live preflight | Decision |
|---|---|---|
| [Tech Valley Pakistan training programs](https://techvalley.pk/trainings/) | Reachable; six public cards parsed, including technology literacy and AI bootcamp program announcements | Added as `techvalley-training`. This is a training/program publisher, not a calendar; cards are still subject to the app's date, topic, and Islamabad relevance filters. |
| [GDG Islamabad](https://gdg.community.dev/gdg-islamabad/) | Reachable; zero parser-compatible event items | Added as `gdg-islamabad-events` as a relevant local developer-community source. A valid empty result is not evidence that the chapter has no events. |

Two candidates were deliberately not added: Eventbrite's Islamabad-wide
workshops browse page parsed unrelated voice-over, clothing, business, and
other non-technical listings; the tech topic filter would not make that page a
focused tech-workshop source. Guessed GDG-on-campus NUST and QAU URLs returned
404, and Tech Valley's guessed `/events/` route returned 404. The Luma
Islamabad candidate could not pass the crawler's robots/redirect check.

The current registry is **59 unique sources**: 11 RSS feeds and 48 public-page
discovery sources. The focused candidates are checked alongside the prior
registry; each source's actual crawl outcome is stored separately from whether
it produced a future, eligible Islamabad event.

## Latest live verification

The latest full refresh attempted all **59 configured sources** through the
compliant connectors: 30 returned items, 28 fetched successfully with no
parser-compatible items, one failed with a network disconnect, and none were
skipped. Across the run, 438 feed/page items were parsed and three future
Islamabad-relevant events passed the app's filters. The failed source was
PakEvents Islamabad (`RemoteProtocolError: Server disconnected without
sending a response`); it was not bypassed or counted as a valid empty result.
The API source index exposed all 59 configured entries after the run.

The new Tech Valley page was reachable and returned six cards but no event
survived the future-date and Islamabad relevance filters. GDG Islamabad was
reachable with a valid empty result. These are useful distinctions: page
availability does not guarantee that the current page contains a qualifying
event.
