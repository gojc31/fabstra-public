# Traps that hold on any stack

Each of these cost a review round when first met. They are stated as principles; the project's framework decides the spelling.

## Request-scoped memoisation

- A memo that lives for one request is always safe to add. Anything that outlives the request is a caching policy and belongs to whoever owns the data policy.
- Key a memo on primitives (ids, slugs, dates). An object or array key compares by identity in most runtimes and misses every time, or worse, hits across callers that built equal-looking objects differently.
- Include every scoping dimension in the key: user, tenant, locale, role. A memo keyed on the resource alone serves one viewer's result to the next.
- A memo stored on an instance is request-scoped only when the instance is. Confirm what constructs the instance and how often; a module-level singleton turns a per-request memo into a process-wide cache.
- Evict a memo entry when its promise rejects, so a retry re-queries. Keep a resolved "not found".
- The one stale-read shape to grep for after adding any memo: a single handler that reads through the memoised function, writes the data it reads, then reads through it again.

## Streaming and early flush

- Once any byte of the body is sent, the status code and headers are final. Whatever the framework calls it - streaming, suspense, chunked rendering, early flush - a redirect, a not-found, or an unhandled error that happens after the first flush reaches the client under the status already sent, usually 200.
- So every authorisation check, existence check and redirect decision runs before the first flush. Stream only the data-dependent body, and hand it already-authorised inputs.
- A loading placeholder attached at a parent level becomes the placeholder for every child that has none of its own. Keep shared placeholders shape-neutral and free of page-specific text.
- List every status change the slice introduces in the pull request description. Monitoring keyed on 3xx or 5xx goes quiet for those routes.
- A placeholder visible under about 100 ms reads as a flicker; 300 ms and up reads as feedback. Measure before keeping one.

## Serial to parallel

- Parallelise only reads that are independent. Keep the gate first and serial: authorise, then fan out.
- Converting a serial loop to a parallel one changes which failure surfaces first and how many requests hit a downstream at once. Check the callee's failure mode (does it throw or return a sentinel?) and the downstream's rate limits, and keep any counters (attempts, failures) identical.
- A call that "cannot fail" because it catches internally is the safe one to move into a parallel group; one that throws changes the group's failure behaviour.

## Trimming work

- When a loop fetches a large payload to read one field, first ask whether the surface that shows the field is even on screen. Gating the work on the surface that needs it beats optimising the loop.
- When a bound is lowered or a limit added, find every consumer of the result: counts, "oldest" or "latest" derivations, pagination, and any validation of a user-supplied value against the list.
- A fallback that can never change the result is dead code that doubles the cost of the empty case. Prove it from the data model (nullability, derivation) before deleting, and put the proof in the comment.

## Client bundle

- A heavy library imported by a shared module reaches every client file that imports anything from that module. Move pure helpers into their own file and re-export them from the old path so importers keep working.
- Load parsers, exporters and editors inside the handler that needs them, within that handler's existing error handling, so a failed chunk load surfaces as the handler's own error message.
- A class check (`instanceof`) against a lazily loaded module works when the class comes from that same load.

## Environment

- A dev server left running across a branch checkout can die mid-run; restart it after every checkout before measuring or crawling.
- A service worker registered on a local origin by another project keeps serving that project's shell. A private window has no registrations.
- Auth providers often whitelist specific local origins; run the dev server on a whitelisted one.
- Where the package manager rewrites the lockfile wholesale, install from the lockfile (`npm ci`, `pnpm install --frozen-lockfile`, `pip install -r` with hashes) and keep lockfile churn out of the slice.
- Create schema migrations with the project's migration tool, apply locally, and prove a new index with the engine's query-plan command.
