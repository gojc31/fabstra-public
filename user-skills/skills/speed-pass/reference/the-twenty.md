# The twenty

The 20-point web-performance checklist (source: a Josh Hoeg reel, "your vibe-coded website is slow because you aren't telling it to do these 20 things"). Each row says what to look for and what evidence earns a verdict. The rows are stack-neutral: apply each to whatever this project uses for rendering, data and hosting. On a platform-hosted app expect a third to come back `platform's job`; on an API-only service or a static site mark the rows that cannot apply `not applicable`.

| # | Item | Look for | Evidence for the verdict |
|---|---|---|---|
| 1 | Compress images | every `<img>` and image import; files in the public folder over 200 KB | list of image sites with source type and size |
| 2 | Lazy loading | below-the-fold images; heavy modules loaded on first paint | which heavy modules load before the user asks for them |
| 3 | Code splitting | large libraries (spreadsheet, PDF, chart, editor, SDK) statically imported by client code, directly or through a shared module | the import chain from a client file to the library |
| 4 | Cache API responses | the same read issued more than once per request; identical external calls on every render | each duplicate pair, file:line both sides |
| 5 | CDN | static assets and pages served from the origin | hosting config; usually `platform's job` |
| 6 | Minify JS and CSS | unminified output in the production build | built size against source size |
| 7 | Index the database | filter and order columns with no supporting index on tables that grow; foreign keys (several engines, Postgres among them, leave these unindexed) | a table of query shape against index, from the migrations |
| 8 | Reduce rerenders | state lifted too high, effects refetching every render, unmemoised expensive derivations in the largest client components | file:line in the biggest client files |
| 9 | Debounce inputs | text inputs whose change handler navigates, fetches, or calls the server | each handler, or "zero violations found" |
| 10 | Paginate large lists | queries with no limit on unbounded tables; components mapping a whole array | the unbounded query and its callers |
| 11 | Remove unused dependencies | declared packages with zero imports | grep result per dependency, plus a dependency checker's output |
| 12 | Defer non-critical scripts | third-party scripts loading before interaction | script tags and their strategy |
| 13 | Loading skeleton | routes that block on all data with no loading state; pages with no streaming or placeholder mechanism | count of placeholder or streaming sites against count of data-heavy routes |
| 14 | Load balancer | single-instance serving | hosting config; usually `platform's job` |
| 15 | Compress API payloads | raw row arrays shipped to client components and recomputed in the browser | the prop, its size driver, and the compute it feeds |
| 16 | Connection pooling | a client or pool constructed per request | how the database client is created; a data layer reached over HTTP pools on the provider's side |
| 17 | Cache computed results | expensive derivations recomputed per request from unchanged inputs | the computation and how often its inputs change |
| 18 | Fix N+1 queries | an awaited read or write inside a loop over rows or periods | the loop, its cardinality, and whether iterations are independent |
| 19 | Server-side caching | cross-request caching of slow reads | what exists today and what the project's data policy allows |
| 20 | Lighthouse audit | measured field performance | whether real-user monitoring exists; an app behind a login needs real-user monitoring, since a lab audit cannot sign in |

Where to look first depends on the rendering model. Server-rendered apps: 4, 13 and 18 (duplicate reads per request, no streaming, loops that await). Single-page apps: 3, 8 and 15 (bundle weight, rerenders, oversized payloads). API services: 7, 10 and 18 (indexes, unbounded queries, N+1). Static and content sites: 1, 2 and 12 (images, lazy loading, third-party scripts).
