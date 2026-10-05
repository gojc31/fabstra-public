# Stack file: Next.js App Router

How the general traps in [../traps.md](../traps.md) are spelled on this stack. Read the framework's bundled docs (`node_modules/next/dist/docs/`) before asserting an API; versions move faster than training data.

- **Request-scoped memo:** React `cache()` dedups a function across the layout, page and nested server components of one request. Generic functions keep their signature with `cache(impl) as typeof impl`. Outside a render (a server action body) `cache()` memoises nothing, so an action's read cannot leak into the re-render that follows.
- **Early flush:** `loading.tsx` wraps its segment's page and every nested layout and page below it; its own segment's `layout.tsx` stays outside. After a fallback flushes, `notFound()` streams a soft 404, `redirect()` becomes a client-side redirect, and a throw renders the error boundary, all under 200.
- **Streaming a gated page:** keep the gate and any empty-state decision in the page, then `<Suspense fallback={<Skeleton />}>` around an async server component that receives already-authorised data. Move the existing data code into it verbatim.
- **Lazy loading:** `await import()` inside the handler; keep `import type` for types.
- **Routes file:** `find app -name page.tsx`, strip the parenthesised route groups and the trailing `/page.tsx`.
- **Per-request server time:** the dev server prints total and application-code milliseconds per request.

Provider notes met alongside this stack:

- Supabase: supabase-js talks HTTP to PostgREST, so connection pooling is the provider's side; the repo's job is one client per process. Migrations via `supabase migration new` and `supabase migration up`.
- Clerk: `currentUser()` is a network call, `auth()` reads the token; development instances whitelist specific local origins.
