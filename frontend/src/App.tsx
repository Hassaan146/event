import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ArrowDownRight, ArrowUpRight, CalendarDays, Check, ChevronDown, Clock3, ExternalLink, MapPin, Radio, RefreshCw, Search, Sparkles, Users, Wifi } from "lucide-react";

type EventItem = {
  id: string;
  title: string;
  event_date: string | null;
  end_date: string | null;
  category: string | null;
  venue: string | null;
  format: string | null;
  eligibility: string | null;
  team_size: string | null;
  level: string | null;
  registration_status: "open" | "unknown";
  source_name: string;
  source_url: string;
  last_checked: string;
};

type SourceItem = {
  id: string;
  name: string;
  url: string;
  enabled: boolean;
  crawl_policy: "eligible" | "review_required" | "disallowed";
  crawl_status: "pending" | "success" | "empty" | "robots_denied" | "robots_unavailable" | "forbidden" | "login_required" | "unsupported" | "parse_error" | "error" | "review_required" | "disallowed";
  note: string | null;
  last_checked: string | null;
  last_attempted: string | null;
  items_found: number;
  events_saved: number;
  last_error: string | null;
};

type RefreshResult = {
  feeds_found: number;
  events_saved: number;
  sources_attempted: number;
  sources_succeeded: number;
  sources_empty: number;
  sources_skipped: number;
  sources_failed: number;
  errors: { source: string; error: string }[];
};

class ApiUnavailableError extends Error {}

async function requestApi(url: string, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(url, init);
  } catch {
    throw new ApiUnavailableError("The local API could not be reached.");
  }
}

const API_URL = import.meta.env.VITE_API_URL ?? "";
const categories = [
  { label: "All tech events", value: "" },
  { label: "Hackathons", value: "Hackathon" },
  { label: "Tech meetups", value: "Tech meetup" },
  { label: "Tech workshops", value: "Tech workshop" },
  { label: "Tech conferences", value: "Tech conference" },
  { label: "Startup events", value: "Startup event" },
];
const humanDate = (value: string | null) =>
  value
    ? new Intl.DateTimeFormat("en-PK", { day: "numeric", month: "short", year: "numeric" }).format(new Date(`${value}T00:00:00`))
    : "Date not confirmed";
const checkedAt = (value: string | null) =>
  value ? new Intl.DateTimeFormat("en-PK", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)) : "Not checked yet";

function App() {
  const [events, setEvents] = useState<EventItem[]>([]);
  const [sources, setSources] = useState<SourceItem[]>([]);
  const [category, setCategory] = useState("");
  const [query, setQuery] = useState("");
  const [registration, setRegistration] = useState("all");
  const [lastRefresh, setLastRefresh] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [checkedSources, setCheckedSources] = useState(0);
  const [error, setError] = useState("");
  const [apiUnavailable, setApiUnavailable] = useState(false);
  const [notice, setNotice] = useState("");
  const refreshStartedAt = useRef(0);
  const sourceCheckBaseline = useRef(new Map<string, string | null>());

  const sourceCounts = useMemo(() => {
    const eligible = sources.filter((source) => source.crawl_policy === "eligible").length;
    return {
      total: sources.length,
      eligible,
      checked: sources.filter((source) => source.last_attempted).length,
      failed: sources.filter((source) => ["robots_denied", "robots_unavailable", "forbidden", "login_required", "unsupported", "parse_error", "error"].includes(source.crawl_status)).length,
      skipped: sources.filter((source) => ["review_required", "disallowed"].includes(source.crawl_status)).length,
    };
  }, [sources]);

  const loadEvents = useCallback(async () => {
    const params = new URLSearchParams();
    if (query.trim()) params.set("q", query.trim());
    if (category) params.set("category", category);
    if (registration !== "all") params.set("registration", registration);
    const response = await requestApi(`${API_URL}/api/events?${params}`);
    if (!response.ok) throw new Error("Could not load events from the local API.");
    const data = await response.json();
    setEvents(data.events);
    setLastRefresh(data.last_refresh);
  }, [category, query, registration]);

  const loadSources = useCallback(async (): Promise<SourceItem[]> => {
    const response = await requestApi(`${API_URL}/api/sources`);
    if (!response.ok) throw new Error("Could not load configured sources.");
    const latestSources: SourceItem[] = await response.json();
    setSources(latestSources);
    return latestSources;
  }, []);

  useEffect(() => {
    let active = true;
    const run = async () => {
      try {
        setError("");
        await Promise.all([loadEvents(), loadSources()]);
      } catch (reason) {
        if (active) {
          setError(reason instanceof Error ? reason.message : "The API could not be reached.");
          setApiUnavailable(reason instanceof ApiUnavailableError);
        }
      }
    };
    void run();
    return () => {
      active = false;
    };
  }, [loadEvents, loadSources]);

  useEffect(() => {
    if (!busy) return;
    const timer = window.setInterval(() => {
      setElapsedSeconds(Math.floor((Date.now() - refreshStartedAt.current) / 1000));
    }, 1000);
    const progressTimer = window.setInterval(() => {
      void fetch(`${API_URL}/api/sources`)
        .then((response) => {
          if (!response.ok) throw new Error("Could not update source progress.");
          return response.json();
        })
        .then((latestSources: SourceItem[]) => {
          setSources(latestSources);
          const completed = latestSources.filter(
            (source) =>
              source.crawl_policy === "eligible" &&
              source.last_attempted &&
              source.last_attempted !== sourceCheckBaseline.current.get(source.id),
          ).length;
          setCheckedSources(Math.min(completed, latestSources.filter((source) => source.crawl_policy === "eligible").length));
        })
        .catch(() => {
          // The refresh request remains authoritative if a progress poll fails.
        });
    }, 2000);
    return () => {
      window.clearInterval(timer);
      window.clearInterval(progressTimer);
    };
  }, [busy]);

  const refresh = async () => {
    setError("");
    setApiUnavailable(false);
    setNotice("");
    setCheckedSources(0);
    sourceCheckBaseline.current = new Map(sources.map((source) => [source.id, source.last_attempted]));
    refreshStartedAt.current = Date.now();
    setElapsedSeconds(0);
    setBusy(true);
    try {
      const baselineSources = await loadSources();
      sourceCheckBaseline.current = new Map(baselineSources.map((source) => [source.id, source.last_attempted]));
      const response = await requestApi(`${API_URL}/api/refresh`, { method: "POST" });
      if (!response.ok) throw new Error("Source refresh failed.");
      const result: RefreshResult = await response.json();
      const [, latestSources] = await Promise.all([loadEvents(), loadSources()]);
      setCheckedSources(result.sources_attempted);
      setNotice(`Refresh finished: attempted ${result.sources_attempted} of ${latestSources.length} sources; ${result.sources_succeeded} sources returned items (${result.feeds_found} parsed), ${result.sources_empty} had no event items, ${result.sources_failed} were blocked or failed, and ${result.sources_skipped} were skipped by policy. Saved ${result.events_saved} qualifying future tech event listing${result.events_saved === 1 ? "" : "s"}.`);
      if (result.errors.length) setError("Some sources could not be checked. Their status is shown below.");
      window.requestAnimationFrame(() => {
        document.getElementById("event-results")?.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The refresh could not be completed.");
      setApiUnavailable(reason instanceof ApiUnavailableError);
    } finally {
      setBusy(false);
    }
  };

  const stats = useMemo(() => ({
    total: events.length,
    open: events.filter((event) => event.registration_status === "open").length,
    unknown: events.filter((event) => event.registration_status === "unknown").length,
  }), [events]);

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">Skip to main content</a>
      <header className="topbar">
        <a className="brand" href="/" aria-label="Fieldnotes home">
          <span className="brand-mark"><span /></span>
          <span>fieldnotes<span className="brand-dot">.</span></span>
        </a>
        <div className="topbar-right">
          <span className="location-pill"><span className="pulse" /> ISLAMABAD / ICT</span>
          <button className="refresh-button" onClick={refresh} disabled={busy}>
            <RefreshCw size={15} className={busy ? "spin" : ""} />
            {busy ? "Checking sources" : "Refresh sources"}
          </button>
        </div>
      </header>

      <main id="main">
        <section className="hero">
          <div className="hero-copy">
            <div className="eyebrow"><span className="eyebrow-line" /> A FIELD GUIDE FOR THE CURIOUS</div>
            <h1>Make room<br />for <em>what’s next.</em></h1>
            <p className="hero-description">The moments worth showing up for, gathered from around Islamabad’s tech community.</p>
            <div className="hero-meta"><span><Radio size={14} /> COMMUNITY-SOURCED</span><span className="meta-divider" /><span>NO NOISE, JUST SIGNAL</span></div>
          </div>
          <div className="hero-art" aria-hidden="true">
            <div className="orbit orbit-one" /><div className="orbit orbit-two" />
            <div className="sun"><span /></div>
            <div className="art-label label-top">33.6844° N</div>
            <div className="art-label label-bottom">73.0479° E <span>·</span> ISLAMABAD</div>
            <div className="spark spark-one">✳</div><div className="spark spark-two">✳</div>
          </div>
          <div className="hero-index">01 <span>/</span> 04</div>
        </section>

        <section className="events-section">
          <div className="section-heading">
            <div><div className="eyebrow section-eyebrow"><span className="eyebrow-line" /> THE UPCOMING</div><h2>Find your next thing<span>.</span></h2></div>
            <div className="stats">
              <div><strong>{String(stats.total).padStart(2, "0")}</strong><span>LISTED</span></div>
              <div><strong>{String(stats.open).padStart(2, "0")}</strong><span>REGISTRATION OPEN</span></div>
              <div><strong>{String(stats.unknown).padStart(2, "0")}</strong><span>VERIFY FIRST</span></div>
            </div>
          </div>

          <div className="toolbar">
              <div className="category-tabs" role="group" aria-label="Filter by technology event type">
                {categories.map((item) => <button key={item.label} type="button" aria-pressed={category === item.value} className={category === item.value ? "tab active" : "tab"} onClick={() => setCategory(item.value)}>{item.label}</button>)}
            </div>
            <div className="filters">
              <label className="searchbox" htmlFor="event-search"><Search size={16} /><span className="sr-only">Search events</span><input id="event-search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search events" aria-label="Search events" /></label>
              <label className="selectbox" htmlFor="registration-filter"><span className="sr-only">Filter registration status</span><select id="registration-filter" value={registration} onChange={(event) => setRegistration(event.target.value)} aria-label="Filter registration status"><option value="all">Any status</option><option value="open">Registration open</option><option value="unknown">Verify on source</option></select><ChevronDown size={14} /></label>
            </div>
          </div>

          {busy && (
            <div className="refresh-progress">
              <div className="progress-doodle" aria-hidden="true">
                <span className="doodle-orbit doodle-orbit-outer" />
                <span className="doodle-orbit doodle-orbit-inner" />
                <span className="doodle-center"><Radio size={18} /></span>
                <Sparkles className="doodle-spark" size={16} />
              </div>
              <div className="progress-copy">
                <strong>Checking tech sources<span className="loading-ellipsis"><i>.</i><i>.</i><i>.</i></span></strong>
                <span role="status" aria-live="polite" aria-atomic="true">
                  {sourceCounts.total
                    ? `${checkedSources} of ${sourceCounts.eligible} eligible sources attempted · ${sourceCounts.total} sites indexed`
                    : "Loading the source list"}
                </span>
                <span className="progress-timer" aria-hidden="true">
                  {Math.floor(elapsedSeconds / 60)}:{String(elapsedSeconds % 60).padStart(2, "0")} elapsed
                </span>
                <span className="progress-hint">
                  {sourceCounts.failed || sourceCounts.skipped
                    ? `${sourceCounts.failed} blocked or failed and ${sourceCounts.skipped} skipped on the last refresh. Each site's reason appears below.`
                    : "Each source is checked only when public access and its crawl policy allow it."}
                </span>
              </div>
              <div className="progress-track" aria-hidden="true"><span /></div>
            </div>
          )}
          {error && <div className="message error-message" role="alert" aria-live="assertive">{error}</div>}
          {notice && (
            <div className="message success-message" role="status" aria-live="polite">
              <Check size={15} />
              <span>{notice}</span>
              <button onClick={() => document.getElementById("event-results")?.scrollIntoView({ behavior: "smooth", block: "start" })}>View results <ArrowDownRight size={13} /></button>
            </div>
          )}
          {events.length ? (
            <div className="event-grid" id="event-results">
              {events.map((event, index) => <EventCard key={event.id} event={event} index={index} />)}
            </div>
          ) : (
            <div className="empty-state" id="event-results">
              <div className="empty-symbol">∅</div>
              <h3>{apiUnavailable ? "Can’t reach the event desk." : "A little quiet, for now."}</h3>
              <p>{apiUnavailable ? "Start the FastAPI server and try again." : `No qualifying future listings. ${sourceCounts.checked} sources have a recorded refresh result; ${sourceCounts.failed} were blocked or failed and ${sourceCounts.skipped} were skipped.`}</p>
              <button onClick={refresh} disabled={busy} className="text-button">Check the sources <ArrowUpRight size={15} /></button>
            </div>
          )}
        </section>

        <section className="source-strip">
          <div className="source-copy"><span className="eyebrow"><span className="eyebrow-line" /> A NOTE ON SOURCES</span><p>Only technology-related listings belong here. We check event details against their sources and remove listings that do not meet that bar.</p></div>
          <div className="source-check"><Clock3 size={15} /><span>LAST CHECKED</span><strong>{checkedAt(lastRefresh)}</strong></div>
          <nav aria-label="Page sections">
            <a className="source-link" href="#sources">OUR SOURCES <ArrowDownRight size={14} /></a>
          </nav>
        </section>
        <section className="source-list" id="sources">
          <div className="source-list-heading"><span className="eyebrow"><span className="eyebrow-line" /> TECH EVENT SOURCE INDEX</span><span>{sourceCounts.total} INDEXED · {sourceCounts.eligible} ELIGIBLE · {sourceCounts.checked} CHECKED · {sourceCounts.failed} FAILED</span></div>
          <div className="source-list-items">
            {sources.map((source) => (
              <a className="source-item" key={source.id} href={source.url} target="_blank" rel="noreferrer">
                <span className={`source-state ${source.crawl_status === "success" ? "success" : source.crawl_status === "empty" ? "empty" : ["robots_denied", "robots_unavailable", "forbidden", "login_required", "unsupported", "parse_error", "error"].includes(source.crawl_status) ? "failed" : "pending"}`} />
                <span className="source-item-name">{source.name}</span>
                <span className="source-item-meta" title={source.last_error ?? source.note ?? ""}>{source.crawl_status === "pending" ? "Not checked yet" : source.crawl_status === "success" ? `${source.items_found} items · ${source.events_saved} saved · ${checkedAt(source.last_attempted)}` : source.crawl_status === "empty" ? `No event items · ${checkedAt(source.last_attempted)}` : `${source.crawl_status.replace(/_/g, " ")} · ${checkedAt(source.last_attempted)}`}</span>
                <ExternalLink size={12} />
              </a>
            ))}
          </div>
        </section>
      </main>
      <footer><span>FIELDNOTES <span className="brand-dot">·</span> ISLAMABAD</span><span>GOOD THINGS HAPPEN WHEN YOU SHOW UP.</span><span>© 2026</span></footer>
    </div>
  );
}

function EventCard({ event, index }: { event: EventItem; index: number }) {
  const date = new Date(`${event.event_date}T00:00:00`);
  const month = new Intl.DateTimeFormat("en", { month: "short" }).format(date).toUpperCase();
  const day = new Intl.DateTimeFormat("en", { day: "2-digit" }).format(date);
  return (
    <article className={`event-card ${index === 0 ? "featured" : ""}`}>
      <div className="card-topline"><span className="category-label">{event.category ?? "Tech gathering"}</span><span className={`registration ${event.registration_status}`}>{event.registration_status === "open" ? <><span className="status-dot" /> REGISTRATION OPEN</> : <>VERIFY ON SOURCE <ArrowUpRight size={11} /></>}</span></div>
      <div className="card-main">
        <div className="date-block"><strong>{day}</strong><span>{month}</span></div>
        <div className="event-content">
          <h3>{event.title}</h3>
          <div className="event-details">
            <span><CalendarDays size={13} />{humanDate(event.event_date)}</span>
            <span>{event.format === "Online" ? <Wifi size={13} /> : <MapPin size={13} />}{event.format ?? event.venue ?? "Format / venue unknown"}</span>
            {event.venue && event.format && <span><MapPin size={13} />{event.venue}</span>}
          </div>
        </div>
      </div>
      <div className="card-facts">
        <div><span className="fact-label">WHO CAN JOIN</span><strong>{event.eligibility ?? "Eligibility not stated"}</strong></div>
        <div><span className="fact-label">TEAM SIZE</span><strong><Users size={13} />{event.team_size ?? "Not stated"}</strong></div>
        <div><span className="fact-label">SCOPE</span><strong>{event.level ?? "Not stated"}</strong></div>
      </div>
      <div className="card-footer"><span className="source-name">VIA <strong>{event.source_name}</strong></span><a href={event.source_url} target="_blank" rel="noreferrer">VIEW SOURCE <ExternalLink size={12} /></a></div>
    </article>
  );
}

export default App;
