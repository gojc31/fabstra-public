# Measuring a speed pass

## What to count

- **Queries per page or request.** Reset the engine's statement counter, render once, read the counter.
  - Postgres: `pg_stat_statements` (`select pg_stat_statements_reset();` then sum `calls`).
  - MySQL / MariaDB: `performance_schema.events_statements_summary_by_digest`, or the general log for one request.
  - SQLite, or any engine behind an ORM: turn on the ORM's query log (Prisma `log: ['query']`, SQLAlchemy `echo=True`, Django `connection.queries`, ActiveRecord log) and count lines for one request.
  - Document stores and HTTP-backed data layers: count outbound calls with a request log or a proxy.
  Render with a single direct request rather than a browser navigation: link prefetching and background refreshes fire extra renders into the same counter. Trust a delta only when it is large and repeats across two runs.
- **Bytes on first load.** From the production build: the largest bundles and which packages dominate each. In the browser: `performance.getEntriesByType('resource')` filtered to scripts, summed, with every script over 60 KB listed.
- **Server time per request.** The framework's or server's own request log. Take warm samples only; the first hit after a code change includes compilation or cold start.

## What local wall-clock cannot show

When the database runs on the same machine, a round trip costs almost nothing, so removing forty of them barely moves a local timer even though each costs tens of milliseconds between a hosted function and a hosted database. Dev-mode recompilation swings medians by hundreds of milliseconds between identical runs. Report the count as the result, give the production estimate as an estimate, and say that real timings need real-user monitoring or production tracing. Calls to external APIs are the exception: they cross the real network locally too, so local timing of those is meaningful.

## Routes file

One path per line, dynamic segments in brackets. Build it from the project's own router:

- File-based routers (Next, Nuxt, SvelteKit, Remix, Astro): list the page files and strip the filename and any grouping folders.
- Declarative routers: the framework's route listing (`rails routes`, Django `show_urls`, Laravel `route:list`, a printed Express/Fastify route table).
- Anything else: the sitemap, or the links harvested from the home page and navigation.

Take substitution values for dynamic segments from the local database and put them in `subs.json`.

## Route crawl

`scripts/crawl.py <routes-file> <out.json> --base <url> [--subs subs.json] [--header "Name: value"]... [--target <tabId>]`

- **Public app or API:** no extra flags.
- **Behind a login, header mode:** pass the session as `--header "Cookie: ..."` or `--header "Authorization: Bearer ..."`. The user supplies the value; the crawl never handles credentials beyond sending that header.
- **Behind a login, browser mode:** when a browser-automation helper that exposes `switch_tab` and `js` is installed (browser-harness), pass `--target` with the full tab id of a tab the user has signed into. Routes are fetched from inside that tab with its cookies.
- An unauthenticated crawl of a signed-in app returns the login redirect for every route and proves nothing.
- Crawl the branch, check out the base, restart the server, crawl again, check the branch back out, restart the server.
- Statuses: 200 rendered, 404 denied or unknown, 0 a redirect, EXC the request never reached the server. A route whose status differs between the two crawls is either a regression or a behaviour change that belongs in the pull request description.

## Live checks worth scripting

- **Deny still denies.** Fetch an unknown id on every gated route family and expect the project's deny status.
- **Placeholder duration.** A MutationObserver recording when the placeholder appears and disappears during a client-side navigation.
- **Lazy chunks stay lazy.** After first load, no script resource matches the heavy library's size; it appears only after the triggering interaction.
