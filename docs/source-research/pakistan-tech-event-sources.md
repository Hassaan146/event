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

The final run completed at **2026-10-28 19:22:58 UTC**:

| Result | Count |
|---|---:|
| Configured and attempted | 56 |
| Parsed items from sources | 425 |
| Successful sources with parsed items | 28 |
| Successful empty sources | 28 |
| Failed or blocked sources | 0 |
| Skipped sources | 0 |
| Qualifying future event records saved or updated | 3 |

The three saved events were AWS Student Community Day Islamabad (Oct 31),
Open Source Hack Day — CloudCon Day 2 (Nov 1), and Open Source Hackathon NUST
(Nov 3). Their registration state remains **Unknown — verify on source**;
the listing does not establish team-size or eligibility details when those
facts were absent from captured text.

### Sources that yielded parsed items

Counts are raw feed/listing items, not accepted future Islamabad events.

| Source | Parsed items |
|---|---:|
| TechJuice | 15 |
| ProPakistani | 10 |
| Dawn | 28 |
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
| Meetup Islamabad technology events | 12 |
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

### Removed after the full crawler run

| Source | Observed result | Decision |
|---|---|---|
| PKCERT events (`pkcert.gov.pk/events.asp`) | The crawler could not check `robots.txt` (`RobotsFetchError`, underlying `ConnectError`) during the initial 57-source run. | Removed from the active registry. It was not included in the final 56-source run. This is a failed access-policy check, not evidence that the site has no events. |

### Not enabled after live preflight

| Candidate | Observed result | Reason not enabled |
|---|---|---|
| Devpost | HTTP 403 | Access denied |
| MLH | Redirected away from the candidate URL | The crawler refuses redirects |
| DoraHacks | `robots.txt` returned HTTP 405 | Could not establish permission |
| GEN Global | `robots.txt` returned HTTP 403 | Could not establish permission |
| ITCN Asia | `robots.txt` returned HTTP 406 | Could not establish permission |
| DigiSkills | TLS certificate failure | Public connection could not be verified |
| Procom | DNS resolution failure | Unreachable during check |
| Plan9 | Request timed out | No usable response during check |
| 10Pearls events page | HTTP 404 | Candidate event page unavailable |
| DevOpsDays Islamabad direct page | Response exceeded the crawler's 2 MB limit | Direct page unsupported under current bounded-fetch policy; dev.events Pakistan remains enabled as an alternate listing source |
| P@SHA events page | Parsed placeholder text (“Hello world!”) | Not a usable event listing |
| CUST events page | Page reported “Nothing Found” | No usable listing surfaced |
| WordCamp Islamabad 2026 | Event dates were Oct 24–25, 2026 | Historical event page; no future edition was confirmed |
| Luma Pakistan | Surfaced a 2020 event | Stale listing, not a current event source |
| FAST-NUCES | Tested public homepage was not an event listing; no crawler-compatible events page was verified | Do not treat a generic homepage as an event feed |

These results are time-sensitive. A blocked or unavailable candidate may be
reconsidered after its public access or event page changes, without bypassing
the restriction.

## Registry additions and URL improvements

The final index has **56 unique sources**: 11 RSS feeds and 45 public-page
discovery sources. Added sources include Bano Qabil, Code for Pakistan, ASPIRE
Pakistan, lablab.ai, dev.events Pakistan, Founder Institute Islamabad, AI
Tinkerers Lahore and Karachi, Friends of Figma Lahore, NIC Karachi, Eventbrite
Islamabad technology, NIC Islamabad, NUTECH, Invest2Innovate, The Nest I/O,
and PhoneWorld. Existing entries were updated to use the verified Indus AI
Week Sindh events site, NUST events page, and Meetup's Islamabad technology
browse page.

## Limitations

The current connector supports RSS/Atom, public event cards, and Event
JSON-LD; it does not execute page JavaScript or spider arbitrary links. Some
sites visibly discuss events but do not expose data in these supported forms.
No custom per-site integration was added in this pass. The app preserves
source provenance and leaves unavailable facts unknown rather than inventing
them.
